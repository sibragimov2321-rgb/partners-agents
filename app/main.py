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
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from .storage import init_storage, save_telegram_user
from .webapi import (
    AccountStartIn,
    ApplicationDraftIn,
    ApplicationIn,
    ContactCheckIn,
    ManagerActionIn,
    ManagerAccessIn,
    GeoSettingIn,
    SubmitProfileIn,
    TicketIn,
    check_contact,
    check_manager,
    current_user,
    load_document,
    list_manager_access,
    list_geo_settings,
    grant_manager_access,
    manager_application_action,
    manager_applications,
    mark_deposit,
    profile_payload,
    remove_document,
    revoke_manager_access,
    save_application_draft,
    save_document,
    start_account,
    submit_application,
    submit_profile,
    submit_ticket,
    update_geo_setting,
)

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "http://localhost:8000").strip().rstrip("/")
if not PUBLIC_APP_URL.startswith(("http://", "https://")):
    PUBLIC_APP_URL = "https://" + PUBLIC_APP_URL

BASE = Path(__file__).resolve().parent.parent
WEBHOOK_PATH = "/telegram/webhook"

api = FastAPI(title="Partners Agent Mini App")
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
async def onboarding_submit(payload: SubmitProfileIn, user: dict = Depends(current_user)):
    return submit_profile(user, payload.confirmed_truth)


@api.get("/api/geo-settings")
async def geo_settings(user: dict = Depends(current_user)):
    return list_geo_settings(user)


@api.get("/api/manager/geo-settings")
async def manager_geo_settings(user: dict = Depends(current_user)):
    return list_geo_settings(user, include_inactive=True)


@api.put("/api/superadmin/geo-settings/{geo_code}")
async def put_geo_setting(geo_code: str, payload: GeoSettingIn, user: dict = Depends(current_user)):
    return update_geo_setting(user, geo_code, payload)


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


@api.get("/api/superadmin/managers")
async def get_managers(user: dict = Depends(current_user)):
    return list_manager_access(user)


@api.post("/api/superadmin/managers")
async def add_manager(payload: ManagerAccessIn, user: dict = Depends(current_user)):
    return grant_manager_access(user, payload)


@api.delete("/api/superadmin/managers/{telegram_id}")
async def delete_manager(telegram_id: int, user: dict = Depends(current_user)):
    return revoke_manager_access(user, telegram_id)


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
    if message.from_user:
        save_telegram_user(telegram_message_user(message))
    await configure_menu(message.bot, message.chat.id)
    await message.answer(
        "\U0001F680 Добро пожаловать в Partners Agent!\n\n"
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


def telegram_message_user(message: Message) -> dict:
    sender = message.from_user
    return {
        "id": sender.id if sender else 0,
        "username": sender.username if sender else None,
        "first_name": sender.first_name if sender else None,
        "last_name": sender.last_name if sender else None,
        "language_code": sender.language_code if sender else None,
    }


def command_telegram_id(message: Message) -> int | None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].strip().isdigit():
        return None
    return int(parts[1].strip())


@dp.message(Command("add_manager"))
async def add_manager_command(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    identifier = parts[1].strip() if len(parts) == 2 else ""
    if not identifier:
        await message.answer("Используйте: /add_manager @username или /add_manager TELEGRAM_ID")
        return
    try:
        payload = ManagerAccessIn(telegram_id=int(identifier)) if identifier.isdigit() else ManagerAccessIn(username=identifier)
        result = grant_manager_access(telegram_message_user(message), payload)
        label = f"@{result['username']}" if result.get("username") else str(result["telegram_id"])
        await message.answer(f"✅ Менеджер {label} добавлен.")
    except HTTPException as error:
        await message.answer(f"⛔ {error.detail}")
    except ValueError:
        await message.answer("⛔ Проверьте username или Telegram ID.")


@dp.message(Command("remove_manager"))
async def remove_manager_command(message: Message):
    telegram_id = command_telegram_id(message)
    if telegram_id is None:
        await message.answer("Используйте команду: /remove_manager TELEGRAM_ID")
        return
    try:
        revoke_manager_access(telegram_message_user(message), telegram_id)
        await message.answer(f"✅ Доступ менеджера {telegram_id} удалён.")
    except HTTPException as error:
        await message.answer(f"⛔ {error.detail}")


@dp.message(Command("managers"))
async def managers_command(message: Message):
    try:
        managers = list_manager_access(telegram_message_user(message))
        active = [item for item in managers if item["active"]]
        rows = [
            f"• {item['first_name'] or item['username'] or 'Менеджер'} — {item['telegram_id']}"
            + (" (владелец)" if item["is_superadmin"] else "")
            for item in active
        ]
        await message.answer("Менеджеры:\n" + ("\n".join(rows) if rows else "список пуст"))
    except HTTPException as error:
        await message.answer(f"⛔ {error.detail}")


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Нижняя кнопка «Открыть» запускает Partners Agent.\n"
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
        BotCommand(command="start", description="Открыть Partners Agent"),
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
