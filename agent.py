import zipfile
import os
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_gigachat import GigaChat, GigaChatEmbeddings
from langchain_core.tools import tool
from operator import add as add_messages
from langgraph.graph import StateGraph, END
from langchain_chroma import Chroma
from toxicity_test import check_toxicity
from dotenv import load_dotenv
load_dotenv()

GIGACHAT_KEY = os.getenv("GIGACHAT_API_KEY")
GIGACHAT_EMBEDD_KEY = os.getenv("GIGACHAT_EMBEDDINGS_KEY")

model = GigaChat(
    credentials=GIGACHAT_KEY,
    verify_ssl_certs=False,
    temperature=0
)
model.model = "GigaChat-2"

embeddings = GigaChatEmbeddings(
    credentials=GIGACHAT_EMBEDD_KEY,
    verify_ssl_certs=False
)

file_list = ["all_parsed_data.txt", "afisha_events.txt", "beautiful_places.txt", "mfc_info.txt"] 
combined_content = ""

for file_name in file_list:
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            combined_content += f.read() + "\n" 
    except Exception as e:
        print(f"Ошибка при чтении файла {file_name} - {e}")
        raise

raw_entries = re.split(r"\s*Запись\s*\d+\s*", combined_content)
entries = [e.strip() for e in raw_entries if e.strip()]

docs = []

for idx, entry in enumerate(entries, start=1):
    docs.append(
        Document(
            page_content=entry,
            metadata={"entry_id": idx}
        )
    )

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=250
)

final_docs = []

for doc in docs:
    text = doc.page_content
    chunks = splitter.split_text(text)
    for i, chunk in enumerate(chunks):
        final_docs.append(
            Document(
                page_content=chunk,
                metadata={
                    "entry_id": doc.metadata["entry_id"],
                    "chunk": i
                }
            )
        )

 
PERSIST_DIR = "data/chroma_db"



if os.path.exists(PERSIST_DIR):
    print("Найдена существующая база Chroma")
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings
    )
    print("База загружена")
else:
    print("База не найдена — создание...")
    vectorstore = Chroma.from_documents(
        documents=final_docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    print("База создана")

retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 8, "fetch_k": 20, "lambda_mult": 0.8}
)

@tool
def retriever_tool(query: str) -> str:
    """
    Этот инструмент ищет и возвращает релевантную информацию в базе данных 
    """

    docs = retriever.invoke(query)

    if not docs:
        return "Релевантной информации в документе не найдено"
    
    results = []
    for i, doc in enumerate(docs):
        results.append(f"Фрагмент {i+1}:\n{doc.page_content}")

    return "\n\n".join(results)

tools = [retriever_tool]

model = model.bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def start_node(state: AgentState):
    return state

def should_continue(state: AgentState):
    """Проверяет, содержит ли последнее сообщение вызов инструмента"""
    result = state["messages"][-1]
    return hasattr(result, "tool_calls") and len(result.tool_calls) > 0


def check_toxic(state: AgentState):
    """Использует функцию check_toxicity для определения токсичности сообщения"""
    message = state["messages"][-1].content
    if (float(check_toxicity(message)["toxic"]) < 0.6):
        return True
    else:
        print("Вы слишком грубы! К сожалению, я не смогу Вам помочь.")
        return False

system_prompt = """
Ты интеллектуальный агент, который отвечает на вопросы о государственных сервисах и услугах Санкт-Петербурга в 2025 году, базируясь на доступной тебе векторной базе данных.
Отвечай только на вопросы, связанные с Санкт-Петерубургом и его государственными сервисами и услугами. Если тема вопроса другая, сообщи, что ты агент-помощнник в сфере государственных услуг и жизни в Санкт-Петербурге и не отвечай на вопрос.
Если вопрос о красивых местах в Санкт-Петербурге, то старайся отвечать не только про места, расположенные в Карелии, но и про другие.
Если вопрос о каких-либо мероприятиях в городе, обязательно добавляй в ответ название этого события.
Используй инструмент retriever_tool для ответа на вопросы о государственных услугах, документах, жизненных ситуациях.
Если тебе нужно найти какую-то информацию, прежде чем задать уточняющий вопрос, ты можешь это сделать, но не более 3 уточнений по одному вопросу, это очень важно. Если после 3 вызовов retriever_tool по одному вопросу ты считаешь ответ недостаточным, то отвечай, что ты не можешь ответить на вопрос.
При ответе на вопрос всегда анализируй все фрагменты, которые предоставляет тебе retriever_tool. Формируй ответ из всех них, чтобы он получился более полным.
Если найденный фрагмент содержит возрастные, социальные или иные ограничения,но в запросе пользователя таких ограничений нет — ищи дальше. Не возвращай такие документы как основной ответ.
Если посчитаешь нужным, вставляй полный текст из базы знаний в ответ. Чем ответ подробнее, тем лучше.
Также обязательно вставляй ссылки на дополнительные источники, если находишь их в предложенных тебе отрезках подходящего текста. При этом, указывать из какого фрагмента взят текст ответа не нужно. Если источника нет, не пиши о том, что его нет, просто предоставь информацию без источника.
"""
tool_dict = {our_tool.name: our_tool for our_tool in tools}

def call_llm(state: AgentState):
    messages = list(state["messages"])
    print(messages)
    messages = [SystemMessage(content=system_prompt)] + messages
    message = model.invoke(messages)
    return {"messages": [message]}

def take_action(state: AgentState) -> AgentState:
    """Выполняет вызовы инструментов по запросу llm (model)"""
    tool_calls = state["messages"][-1].tool_calls
    results = []
    for t in tool_calls:
        print(f"Вызываемый инструмент: {t['name']} с запросом: {t['args'].get('query', 'No query provided')}")

        if not t['name'] in tool_dict:
            print(f"\nTool: {t['name']} не сушествует")
            result = "Некорректное имя инструмента"
        
        else:
            result = tool_dict[t['name']].invoke(t['args'].get('query', ''))
            print(f"Итоговая длина: {len(str(result))}")

        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Выполнение инструментов завершено")
    return {'messages': results}


graph = StateGraph(AgentState)


graph.add_node("start_node", start_node)
graph.add_conditional_edges(
    "start_node", 
    check_toxic,
    {True: "llm", False: END}
)
graph.add_node("llm", call_llm)
graph.add_node("retriever_agent", take_action)

graph.add_conditional_edges(
    "llm",
    should_continue,
    {True: "retriever_agent", False: END}
)

graph.add_edge("retriever_agent", "llm")
graph.set_entry_point("start_node")

city_agent = graph.compile()

# def running_agent():
#     print("\n=== Городской помощник ===")

#     while True:
#         user_input = input("\nКакой у Вас вопрос: ")
#         if user_input.lower() in ['exit', 'quit', 'выход', 'выйти', 'конец']:
#             break

#         messages = [HumanMessage(content=user_input)]

#         result = city_agent.invoke({"messages": messages})

#         print("\n=== ОТВЕТ ===")
#         print(result['messages'][-1].content)

# running_agent()