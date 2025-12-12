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
from dotenv import load_dotenv
load_dotenv()

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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

    state["messages"].append(HumanMessage(content=user_text))

    await message.answer("⏳ Думаю...")

    try:
        result = city_agent.invoke(state)
        answer_message = result["messages"][-1]
        if (answer_message.content == user_text):
            answer_message.content = "Вы слышком грубы! Общайтесь вежливее, мы же говорим о культурной столице!"
            state["messages"].append(answer_message)

        answer_text = answer_message.content
        answer_text = clean_html(answer_text)
        answer_text = answer_text.replace("#", "")
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"Время ответа агента - {duration:4f} секунд")
        await message.answer(answer_text+f"\n\nДумал {duration:4f} секунд")

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
