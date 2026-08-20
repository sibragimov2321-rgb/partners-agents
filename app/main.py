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
from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from .storage import init_storage
from .webapi import (
    AccountStartIn,
    ApplicationDraftIn,
    ApplicationIn,
    ContactCheckIn,
    ManagerActionIn,
    TicketIn,
    check_contact,
    check_manager,
    current_user,
    load_document,
    manager_application_action,
    manager_applications,
    mark_deposit,
    profile_payload,
    remove_document,
    save_application_draft,
    save_document,
    start_account,
    submit_application,
    submit_profile,
    submit_ticket,
)

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


@api.post("/api/agent-onboarding/account")
async def onboarding_account(payload: AccountStartIn, user: dict = Depends(current_user)):
    return start_account(user, payload)


@api.patch("/api/agent-onboarding/draft")
async def onboarding_draft(payload: ApplicationDraftIn, user: dict = Depends(current_user)):
    return save_application_draft(user, payload)


@api.post("/api/agent-onboarding/deposit")
async def onboarding_deposit(user: dict = Depends(current_user)):
    return mark_deposit(user)


@api.post("/api/agent-onboarding/submit")
async def onboarding_submit(user: dict = Depends(current_user)):
    return submit_profile(user)


@api.post("/api/agent-documents/{kind}")
async def upload_agent_document(kind: str, document: UploadFile = File(...), user: dict = Depends(current_user)):
    data = await document.read(8 * 1024 * 1024 + 1)
    return save_document(user, kind, document.filename or "document.jpg", document.content_type or "", data)


@api.get("/api/agent-documents/{kind}")
async def get_agent_document(kind: str, user: dict = Depends(current_user)):
    data, mime_type, filename = load_document(user, kind)
    return Response(data, media_type=mime_type, headers={
        "Cache-Control": "no-store, private",
        "Content-Disposition": f'inline; filename="{filename.replace(chr(34), "")}"',
    })


@api.delete("/api/agent-documents/{kind}")
async def delete_agent_document(kind: str, user: dict = Depends(current_user)):
    return remove_document(user, kind)


@api.get("/api/manager/applications")
async def get_manager_applications(user: dict = Depends(current_user)):
    return manager_applications(user)


@api.post("/api/manager/applications/{application_id}/action")
async def act_on_application(application_id: int, payload: ManagerActionIn, user: dict = Depends(current_user)):
    return manager_application_action(user, application_id, payload)


@api.get("/api/manager/applications/{application_id}/documents/{kind}")
async def get_manager_document(application_id: int, kind: str, user: dict = Depends(current_user)):
    data, mime_type, filename = load_document(user, kind, application_id)
    return Response(data, media_type=mime_type, headers={
        "Cache-Control": "no-store, private",
        "Content-Disposition": f'inline; filename="{filename.replace(chr(34), "")}"',
    })


@api.post("/api/support-tickets")
async def support_ticket(payload: TicketIn, user: dict = Depends(current_user)):
    return submit_ticket(user, payload)


@api.post("/api/check-contact")
async def contact_check(payload: ContactCheckIn, user: dict = Depends(current_user)):
    return check_contact(payload)


@api.post("/api/check-blocked")
async def blocked_check(payload: ContactCheckIn, user: dict = Depends(current_user)):
    return check_contact(payload, blocked_only=True)


@api.post("/api/check-manager")
async def manager_check(payload: ContactCheckIn, user: dict = Depends(current_user)):
    return check_manager(payload)


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
        "Внутри доступны: стать агентом, кабинет агента, проверка агента, проверка менеджера и поддержка.",
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
