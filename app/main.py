import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, WebAppInfo, Message
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "http://localhost:8000")
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
BASE = Path(__file__).resolve().parent.parent

api = FastAPI(title="Partners & Agents Mini App")
api.mount("/static", StaticFiles(directory=BASE / "web"), name="static")
dp = Dispatcher()

@api.get("/")
async def index():
    return FileResponse(BASE / "web" / "index.html")

def open_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="Открыть", web_app=WebAppInfo(url=PUBLIC_APP_URL)
    )]])

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "⚡ Начните работу\n\n"
        "Чтобы продолжить, нажмите кнопку «Открыть» ниже 👇\n\n"
        "В приложении доступны регистрация, материалы, статистика и поддержка.",
        reply_markup=open_keyboard(),
    )

async def bot_loop():
    bot = Bot(TOKEN)
    await bot.set_my_commands([BotCommand(command="start", description="Открыть приложение")])
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_chat_menu_button(
                chat_id=admin_id,
                menu_button=MenuButtonWebApp(text="Открыть", web_app=WebAppInfo(url=PUBLIC_APP_URL)),
            )
        except TelegramAPIError:
            logging.warning("Не удалось установить меню для ADMIN_IDS=%s", admin_id)
    await dp.start_polling(bot)

async def serve():
    config = uvicorn.Config(api, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), bot_loop())

if __name__ == "__main__":
    asyncio.run(serve())
