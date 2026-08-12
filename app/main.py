import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, WebAppInfo, Message
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "http://localhost:8000").strip().rstrip("/")
if not PUBLIC_APP_URL.startswith(("http://", "https://")):
    PUBLIC_APP_URL = "https://" + PUBLIC_APP_URL
BASE = Path(__file__).resolve().parent.parent
WEBHOOK_PATH = "/telegram/webhook"

api = FastAPI(title="Melbet Partners Mini App")
api.mount("/static", StaticFiles(directory=BASE / "web"), name="static")
dp = Dispatcher()

@api.get("/")
async def index():
    return FileResponse(BASE / "web" / "index.html")

def open_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть", web_app=WebAppInfo(url=PUBLIC_APP_URL))]])

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "⚡ Начните работу\n\nЧтобы продолжить, нажмите кнопку «Открыть» ниже 👇\n\n"
        "В приложении доступны регистрация, материалы, статистика и поддержка.",
        reply_markup=open_keyboard(),
    )

@api.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    bot = Bot(TOKEN)
    try:
        await dp.feed_raw_update(bot, await request.json())
    finally:
        await bot.session.close()
    return {"ok": True}

async def bot_setup():
    bot = Bot(TOKEN)
    await bot.set_my_commands([BotCommand(command="start", description="Открыть приложение")])
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Открыть", web_app=WebAppInfo(url=PUBLIC_APP_URL)))
    await bot.set_webhook(f"{PUBLIC_APP_URL}{WEBHOOK_PATH}", drop_pending_updates=True)
    await asyncio.Event().wait()

async def serve():
    server = uvicorn.Server(uvicorn.Config(api, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info"))
    await asyncio.gather(server.serve(), bot_setup())

if __name__ == "__main__":
    asyncio.run(serve())
