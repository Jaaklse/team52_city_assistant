import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.filters import Command
import re
from agent import city_agent
from langchain_core.messages import HumanMessage
# from dotenv import load_dotenv
# load_dotenv()

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


@dp.message()
async def handle_message(message: Message):
    user_text = message.text
    user_id = message.from_user.id

    if user_state.get(user_id, False):
        user_state[user_id] = False

    await message.answer("⏳ Думаю...")

    try:
        result = city_agent.invoke(
            {"messages": [HumanMessage(content=user_text)]}
            # ,
            # config={"thread_id": str(user_id)}
        )
        answer = result["messages"][-1].content
        answer = clean_html(answer)
        answer = answer.replace("#", "")

        await message.answer(answer)

    except Exception as e:
        print(f"Ошибка LLM/агента: {e}")

        await message.answer(
            "❗ Произошла ошибка при обработке запроса.\n"
            "Попробуйте ещё раз, возможно, немного уточнив формулировку"
        )

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
