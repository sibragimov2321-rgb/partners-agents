import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .storage import init_storage
from .webapi import ApplicationIn, TicketIn, current_user, profile_payload, submit_application, submit_ticket

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "http://localhost:8000").strip().rstrip("/")
if not PUBLIC_APP_URL.startswith(("http://", "https://")):
    PUBLIC_APP_URL = "https://" + PUBLIC_APP_URL

BASE = Path(__file__).resolve().parent.parent
WEBHOOK_PATH = "/telegram/webhook"

api = FastAPI(title="Partners Portal Mini App")
api.mount("/static", StaticFiles(directory=BASE / "web"), name="static")
dp = Dispatcher()


@api.get("/")
async def index():
    return FileResponse(BASE / "web" / "index.html")


@api.get("/health")
async def health():
    return {"status": "ok"}


@api.on_event("startup")
async def startup() -> None:
    init_storage()


@api.get("/api/me")
async def me(user: dict = Depends(current_user)):
    return profile_payload(user)


@api.post("/api/agent-applications")
async def agent_application(payload: ApplicationIn, user: dict = Depends(current_user)):
    return submit_application(user, payload)


@api.post("/api/support-tickets")
async def support_ticket(payload: TicketIn, user: dict = Depends(current_user)):
    return submit_ticket(user, payload)


def open_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Menu",
                web_app=WebAppInfo(url=PUBLIC_APP_URL),
            )
        ]]
    )


async def configure_menu(bot: Bot, chat_id: int | None = None) -> None:
    """Set the Mini App button globally and for the current private chat."""
    menu_button = MenuButtonWebApp(text="Menu", web_app=WebAppInfo(url=PUBLIC_APP_URL))
    await bot.set_chat_menu_button(menu_button=menu_button)
    if chat_id is not None:
        await bot.set_chat_menu_button(chat_id=chat_id, menu_button=menu_button)


async def send_portal(message: Message) -> None:
    await configure_menu(message.bot, message.chat.id)
    await message.answer(
        "\U0001F680 \u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 Partners Portal!\n\n"
        "\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u043a\u043d\u043e\u043f\u043a\u0443 \u00ab\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435\u00bb \u043d\u0438\u0436\u0435.\n\n"
        "\u0412\u043d\u0443\u0442\u0440\u0438 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b: \u0430\u0433\u0435\u043d\u0442\u044b, \u043f\u0430\u0440\u0442\u043d\u0451\u0440\u044b, \u0431\u0430\u043d\u043d\u0435\u0440\u044b, \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438, FAQ, \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430 \u0438 \u043b\u0438\u0447\u043d\u044b\u0439 \u043a\u0430\u0431\u0438\u043d\u0435\u0442.",
        reply_markup=open_keyboard(),
    )


@dp.message(CommandStart())
async def start(message: Message):
    await send_portal(message)


@dp.message(Command("menu"))
async def menu(message: Message):
    await send_portal(message)


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "\u041d\u0438\u0436\u043d\u044f\u044f \u043a\u043d\u043e\u043f\u043a\u0430 Menu \u043e\u0442\u043a\u0440\u043e\u0435\u0442 Partners Portal.\n"
        "\u0418\u043b\u0438 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 /menu \u0434\u043b\u044f \u043a\u043d\u043e\u043f\u043a\u0438 \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u044f \u0432 \u0447\u0430\u0442\u0435.",
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
    await bot.set_my_commands([
        BotCommand(command="start", description="Open Partners Portal"),
        BotCommand(command="menu", description="Open app menu"),
        BotCommand(command="help", description="How to use the app"),
    ])
    await configure_menu(bot)
    await bot.set_webhook(f"{PUBLIC_APP_URL}{WEBHOOK_PATH}", drop_pending_updates=True)
    await asyncio.Event().wait()


async def serve():
    server = uvicorn.Server(
        uvicorn.Config(api, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
    )
    await asyncio.gather(server.serve(), bot_setup())


if __name__ == "__main__":
    asyncio.run(serve())
