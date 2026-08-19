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
from .webapi import ApplicationIn, ContactCheckIn, TicketIn, check_contact, current_user, profile_payload, submit_application, submit_ticket

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "http://localhost:8000").strip().rstrip("/")
if not PUBLIC_APP_URL.startswith(("http://", "https://")):
    PUBLIC_APP_URL = "https://" + PUBLIC_APP_URL

BASE = Path(__file__).resolve().parent.parent
WEBHOOK_PATH = "/telegram/webhook"

api = FastAPI(title="MELBET Partners Mini App")
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


@api.post("/api/check-contact")
async def contact_check(payload: ContactCheckIn, user: dict = Depends(current_user)):
    return check_contact(payload)


@api.post("/api/check-blocked")
async def blocked_check(payload: ContactCheckIn, user: dict = Depends(current_user)):
    return check_contact(payload, blocked_only=True)


def open_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Открыть",
                web_app=WebAppInfo(url=PUBLIC_APP_URL),
            )
        ]]
    )


async def configure_menu(bot: Bot, chat_id: int | None = None) -> None:
    """Set the Mini App button globally and for the current private chat."""
    menu_button = MenuButtonWebApp(text="Открыть", web_app=WebAppInfo(url=PUBLIC_APP_URL))
    await bot.set_chat_menu_button(menu_button=menu_button)
    if chat_id is not None:
        await bot.set_chat_menu_button(chat_id=chat_id, menu_button=menu_button)


async def send_portal(message: Message) -> None:
    await configure_menu(message.bot, message.chat.id)
    await message.answer(
        "\U0001F680 Добро пожаловать в MELBET PARTNERS!\n\n"
        "\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u043a\u043d\u043e\u043f\u043a\u0443 \u00ab\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435\u00bb \u043d\u0438\u0436\u0435.\n\n"
        "Внутри доступны: агенты, партнёры, баннеры, проверки, FAQ, поддержка и личный кабинет.",
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
        "Нижняя кнопка «Открыть» запускает MELBET PARTNERS.\n"
        "Также можно использовать команду /menu.",
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
        BotCommand(command="start", description="Открыть MELBET PARTNERS"),
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
