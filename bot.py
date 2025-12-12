import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.filters import Command
import re
import time
from agent import city_agent
from langchain_core.messages import HumanMessage
from langchain_gigachat import GigaChatEmbeddings
import numpy as np
from dotenv import load_dotenv
load_dotenv()

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

GIGACHAT_EMBEDD_KEY = os.getenv("GIGACHAT_EMBEDDINGS_KEY")

emb = GigaChatEmbeddings(
    credentials=GIGACHAT_EMBEDD_KEY,
    verify_ssl_certs=False
)

def embed_text(text: str) -> np.ndarray:
    """Преобразование текста в эмбеддинг"""
    return np.array(emb.embed_query(text))

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def is_topic_changed(prev_text: str, curr_text: str, threshold: float = 0.8) -> bool:
    try:
        v1 = embed_text(prev_text)
        v2 = embed_text(curr_text)
        sim = cosine_similarity(v1, v2)
        print(f"[topic similarity] {sim:.3f}")

        return sim < threshold

    except Exception as e:
        print("Ошибка эмбеддинга:", e)
        return False

ALLOWED_TAGS = ["b", "i", "strong", "em", "u", "s", "code", "pre", "a"]

def clean_html(text: str) -> str:
    """Очищаем запрещённые HTML-теги"""
    def replace_tag(match):
        tag = match.group(1)
        if tag.lower() in ALLOWED_TAGS:
            return match.group(0)
        return "" 
    cleaned = re.sub(r"</?([a-zA-Z0-9]+)[^>]*>", replace_tag, text)
    return cleaned

user_state = {} 

TOKEN = TG_TOKEN

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user_state[user_id] = True

    await message.answer(
        "Привет! 👋\n"
        "Я — умный помощник по вопросам государственных услуг и сервисов Санкт-Петербурга.\n"
        "Напиши мне любой вопрос — я помогу!"
    )


user_states = {}  # user_id -> AgentState

@dp.message()
async def handle_message(message: Message):
    start_time = time.perf_counter()
    user_id = message.from_user.id
    user_text = message.text

    if user_id not in user_states:
        user_states[user_id] = {"messages": []}

    state = user_states[user_id]

    if state["messages"]:
        last_user_msg = None

        for msg in reversed(state["messages"]):
            if msg.type == "human":
                last_user_msg = msg.content
                print(f"СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ АХАХАХАХ {last_user_msg}")
                break

        if last_user_msg:
            try:
                if is_topic_changed(last_user_msg, user_text):
                    state["messages"] = []
            except Exception as err:
                print("Ошибка сравнения тем:", err)

    state["messages"].append(HumanMessage(content=user_text))

    await message.answer("⏳ Думаю...")

    try:
        result = city_agent.invoke(state)

        answer_message = result["messages"][-1]

        if answer_message.content == user_text:
            answer_message.content = (
                "Вы слишком грубы! Общайтесь вежливее, мы же говорим о культурной столице!"
            )
            state["messages"].append(answer_message)

        answer_text = clean_html(answer_message.content)
        answer_text = answer_text.replace("#", "")
        final_answer = re.sub(r'\[Фрагмент \d\]', '', answer_text)

        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"Время ответа агента - {duration:.4f} секунд")

        await message.answer(final_answer + f"\n\nДумал {duration:.4f} секунд")

    except Exception as e:
        print(f"Ошибка LLM/агента: {e}")
        await message.answer(
            "❗ Произошла ошибка при обработке запроса.\nПопробуйте ещё раз"
        )


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
