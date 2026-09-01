import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from .storage import init_storage, save_telegram_user
from .cashier_api import close_cashier_client
from .webapi import (
    AccountStartIn,
    ApplicationDraftIn,
    ApplicationIn,
    ContactCheckIn,
    DeleteApplicationIn,
    ManagerActionIn,
    ManagerAgentCreateIn,
    ManagerAgentUpdateIn,
    ManagerAccessIn,
    GeoSettingIn,
    GiveawayBroadcastIn,
    GiveawayCreateIn,
    GiveawayJoinIn,
    GiveawayLifecycleIn,
    GiveawayParticipantActionIn,
    GiveawayUpdateIn,
    SubmitProfileIn,
    TicketIn,
    check_contact,
    check_manager,
    active_giveaway,
    complete_giveaway_broadcast,
    create_giveaway,
    create_giveaway_broadcast,
    current_user,
    draw_giveaway,
    giveaway_action,
    giveaway_history,
    giveaway_participation,
    load_document,
    load_giveaway_banner,
    list_manager_access,
    list_geo_settings,
    grant_manager_access,
    delete_manager_application,
    manager_application_action,
    manager_applications,
    manager_giveaway,
    manager_giveaways,
    mark_deposit,
    profile_payload,
    public_winners,
    remove_document,
    revoke_manager_access,
    restore_participant,
    save_application_draft,
    save_document,
    save_giveaway_banner,
    start_account,
    submit_application,
    submit_profile,
    submit_ticket,
    set_participant_excluded,
    update_geo_setting,
    update_giveaway,
    join_giveaway,
    create_manager_agent,
    update_manager_agent,
    list_giveaway_participants,
    replace_giveaway_winner,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOKEN = os.environ["BOT_TOKEN"]
# Older Railway deployments used WEBAPP_URL.  Accept it as a safe fallback so
# the already-configured bot button and webhook never fall back to localhost.
PUBLIC_APP_URL = (os.getenv("PUBLIC_APP_URL") or os.getenv("WEBAPP_URL") or "http://localhost:8000").strip().rstrip("/")
if not PUBLIC_APP_URL.startswith(("http://", "https://")):
    PUBLIC_APP_URL = "https://" + PUBLIC_APP_URL
# Telegram Desktop and mobile clients can cache a Mini App by its exact URL.
# Bump this non-secret build marker when frontend navigation changes so the
# menu button always opens the current deployment instead of a cached shell.
WEBAPP_BUILD = os.getenv("WEBAPP_BUILD", "20260901-01").strip()

BASE = Path(__file__).resolve().parent.parent
WEBHOOK_PATH = "/telegram/webhook"

api = FastAPI(title="Partners Agent Mini App")
api.mount("/static", StaticFiles(directory=BASE / "web"), name="static")
dp = Dispatcher()


def webapp_url(giveaway_id: int | None = None) -> str:
    """Return a versioned Mini App URL and preserve a future custom query."""
    separator = "&" if "?" in PUBLIC_APP_URL else "?"
    url = f"{PUBLIC_APP_URL}{separator}v={WEBAPP_BUILD}"
    return f"{url}&giveaway={giveaway_id}" if giveaway_id is not None else url


@api.get("/")
async def index():
    return FileResponse(BASE / "web" / "index.html", headers={
        "Cache-Control": "no-store, max-age=0",
    })


@api.get("/health")
async def health():
    return {"status": "ok"}


@api.on_event("startup")
async def startup() -> None:
    init_storage()


@api.on_event("shutdown")
async def shutdown() -> None:
    await close_cashier_client()


@api.get("/api/me")
def me(user: dict = Depends(current_user)):
    return profile_payload(user)


@api.post("/api/agent-applications")
def agent_application(payload: ApplicationIn, user: dict = Depends(current_user)):
    return submit_application(user, payload)


@api.post("/api/agent-onboarding/account")
def onboarding_account(payload: AccountStartIn, user: dict = Depends(current_user)):
    return start_account(user, payload)


@api.patch("/api/agent-onboarding/draft")
def onboarding_draft(payload: ApplicationDraftIn, user: dict = Depends(current_user)):
    return save_application_draft(user, payload)


@api.post("/api/agent-onboarding/deposit")
def onboarding_deposit(user: dict = Depends(current_user)):
    return mark_deposit(user)


@api.post("/api/agent-onboarding/submit")
def onboarding_submit(payload: SubmitProfileIn, user: dict = Depends(current_user)):
    return submit_profile(user, payload.confirmed_truth)


@api.get("/api/geo-settings")
def geo_settings(user: dict = Depends(current_user)):
    return list_geo_settings(user)


@api.get("/api/manager/geo-settings")
def manager_geo_settings(user: dict = Depends(current_user)):
    return list_geo_settings(user, include_inactive=True)


@api.put("/api/superadmin/geo-settings/{geo_code}")
def put_geo_setting(geo_code: str, payload: GeoSettingIn, user: dict = Depends(current_user)):
    return update_geo_setting(user, geo_code, payload)


@api.put("/api/manager/geo-settings/{geo_code}")
def put_manager_geo_setting(geo_code: str, payload: GeoSettingIn, user: dict = Depends(current_user)):
    return update_geo_setting(user, geo_code, payload)


@api.post("/api/agent-documents/{kind}")
async def upload_agent_document(kind: str, document: UploadFile = File(...), user: dict = Depends(current_user)):
    data = await document.read(8 * 1024 * 1024 + 1)
    return await asyncio.to_thread(save_document, user, kind, document.filename or "document.jpg", document.content_type or "", data)


@api.get("/api/agent-documents/{kind}")
def get_agent_document(kind: str, user: dict = Depends(current_user)):
    data, mime_type, filename = load_document(user, kind)
    return Response(data, media_type=mime_type, headers={
        "Cache-Control": "no-store, private",
        "Content-Disposition": f'inline; filename="{filename.replace(chr(34), "")}"',
    })


@api.delete("/api/agent-documents/{kind}")
def delete_agent_document(kind: str, user: dict = Depends(current_user)):
    return remove_document(user, kind)


@api.get("/api/manager/applications")
def get_manager_applications(user: dict = Depends(current_user)):
    return manager_applications(user)


@api.post("/api/manager/applications/{application_id}/action")
def act_on_application(application_id: int, payload: ManagerActionIn, user: dict = Depends(current_user)):
    return manager_application_action(user, application_id, payload)


@api.post("/api/manager/agents")
def add_manager_agent(payload: ManagerAgentCreateIn, user: dict = Depends(current_user)):
    return create_manager_agent(user, payload)


@api.put("/api/manager/agents/{application_id}")
def edit_manager_agent(application_id: int, payload: ManagerAgentUpdateIn, user: dict = Depends(current_user)):
    return update_manager_agent(user, application_id, payload)


@api.delete("/api/manager/applications/{application_id}")
def delete_application(application_id: int, payload: DeleteApplicationIn, user: dict = Depends(current_user)):
    return delete_manager_application(user, application_id, payload)


@api.get("/api/manager/applications/{application_id}/documents/{kind}")
def get_manager_document(application_id: int, kind: str, user: dict = Depends(current_user)):
    data, mime_type, filename = load_document(user, kind, application_id)
    return Response(data, media_type=mime_type, headers={
        "Cache-Control": "no-store, private",
        "Content-Disposition": f'inline; filename="{filename.replace(chr(34), "")}"',
    })


@api.get("/api/giveaways/active")
def get_active_giveaway(user: dict = Depends(current_user)):
    return active_giveaway(user)


@api.get("/api/giveaways/{giveaway_id}/participation")
def get_giveaway_participation(giveaway_id: int, user: dict = Depends(current_user)):
    return giveaway_participation(user, giveaway_id)


@api.post("/api/giveaways/{giveaway_id}/participation")
async def create_giveaway_participation(giveaway_id: int, payload: GiveawayJoinIn, user: dict = Depends(current_user)):
    return await asyncio.to_thread(join_giveaway, user, giveaway_id, payload)


@api.get("/api/giveaways/{giveaway_id}/winners")
def get_giveaway_winners(giveaway_id: int, user: dict = Depends(current_user)):
    return public_winners(user, giveaway_id)


@api.get("/api/giveaways/{giveaway_id}/banner")
def get_giveaway_banner(giveaway_id: int):
    data, mime_type, filename = load_giveaway_banner(giveaway_id)
    return Response(data, media_type=mime_type, headers={
        "Cache-Control": "public, max-age=3600",
        "Content-Disposition": f'inline; filename="{filename.replace(chr(34), "")}"',
    })


@api.get("/api/manager/giveaways")
def get_manager_giveaways(user: dict = Depends(current_user)):
    return manager_giveaways(user)


@api.post("/api/manager/giveaways")
def create_manager_giveaway(payload: GiveawayCreateIn, user: dict = Depends(current_user)):
    return create_giveaway(user, payload)


@api.get("/api/manager/giveaways/{giveaway_id}")
def get_manager_giveaway(giveaway_id: int, user: dict = Depends(current_user)):
    return manager_giveaway(user, giveaway_id)


@api.patch("/api/manager/giveaways/{giveaway_id}")
def patch_manager_giveaway(giveaway_id: int, payload: GiveawayUpdateIn, user: dict = Depends(current_user)):
    return update_giveaway(user, giveaway_id, payload)


@api.post("/api/manager/giveaways/{giveaway_id}/action")
def manager_giveaway_action(giveaway_id: int, payload: GiveawayLifecycleIn, user: dict = Depends(current_user)):
    return giveaway_action(user, giveaway_id, payload.action)


@api.post("/api/manager/giveaways/{giveaway_id}/banner")
async def upload_giveaway_banner(giveaway_id: int, banner: UploadFile = File(...), user: dict = Depends(current_user)):
    data = await banner.read(8 * 1024 * 1024 + 1)
    return await asyncio.to_thread(save_giveaway_banner, user, giveaway_id, banner.filename or "giveaway.jpg", banner.content_type or "", data)


@api.get("/api/manager/giveaways/{giveaway_id}/participants")
def get_giveaway_participants(
    giveaway_id: int,
    status: str | None = Query(default=None, max_length=24),
    geo_code: str | None = Query(default=None, max_length=16),
    query: str | None = Query(default=None, max_length=100),
    user: dict = Depends(current_user),
):
    return list_giveaway_participants(user, giveaway_id, status=status, geo_code=geo_code, query=query)


@api.post("/api/manager/giveaways/{giveaway_id}/participants/{participant_id}/exclude")
def exclude_giveaway_participant(giveaway_id: int, participant_id: int, payload: GiveawayParticipantActionIn, user: dict = Depends(current_user)):
    return set_participant_excluded(user, giveaway_id, participant_id, payload)


@api.post("/api/manager/giveaways/{giveaway_id}/participants/{participant_id}/restore")
def restore_giveaway_participant(giveaway_id: int, participant_id: int, user: dict = Depends(current_user)):
    return restore_participant(user, giveaway_id, participant_id)


@api.post("/api/manager/giveaways/{giveaway_id}/draw")
def run_giveaway_draw(giveaway_id: int, user: dict = Depends(current_user)):
    return draw_giveaway(user, giveaway_id)


@api.post("/api/manager/giveaways/{giveaway_id}/winners/{winner_id}/replace")
def replace_winner(giveaway_id: int, winner_id: int, payload: GiveawayParticipantActionIn, user: dict = Depends(current_user)):
    return replace_giveaway_winner(user, giveaway_id, winner_id, payload)


@api.get("/api/manager/giveaways/{giveaway_id}/history")
def get_giveaway_history(giveaway_id: int, user: dict = Depends(current_user)):
    return giveaway_history(user, giveaway_id)


async def send_giveaway_broadcast(broadcast: dict, giveaway_id: int) -> dict:
    """Respect Telegram limits: each user gets at most one attempted delivery."""
    bot = Bot(TOKEN)
    sent = failed = 0
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=broadcast["button_text"],
            web_app=WebAppInfo(url=webapp_url(giveaway_id)),
        )
    ]]) if broadcast.get("button_text") else None
    try:
        for recipient in broadcast["recipients"]:
            delivered = False
            for attempt in range(2):
                try:
                    await bot.send_message(recipient, broadcast["message"], reply_markup=markup)
                    delivered = True
                    break
                except TelegramRetryAfter as error:
                    if attempt == 0:
                        await asyncio.sleep(float(error.retry_after))
                        continue
                except (TelegramForbiddenError, TelegramBadRequest, TelegramNetworkError):
                    break
            if delivered:
                sent += 1
                await asyncio.sleep(0.05)
            else:
                failed += 1
    finally:
        await bot.session.close()
    await asyncio.to_thread(complete_giveaway_broadcast, broadcast["broadcast_id"], sent, failed)
    return {"sent": sent, "failed": failed}


@api.post("/api/manager/giveaways/{giveaway_id}/broadcast")
async def broadcast_giveaway(
    giveaway_id: int,
    payload: GiveawayBroadcastIn,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user),
):
    # Sending can take minutes for a large audience. Queue it after the HTTP
    # response so it cannot freeze the manager UI or other API requests.
    broadcast = await asyncio.to_thread(create_giveaway_broadcast, user, giveaway_id, payload)
    background_tasks.add_task(send_giveaway_broadcast, broadcast, giveaway_id)
    return {"recipients": len(broadcast["recipients"]), "sent": 0, "failed": 0, "status": "queued"}


@api.get("/api/superadmin/managers")
def get_managers(user: dict = Depends(current_user)):
    return list_manager_access(user)


@api.post("/api/superadmin/managers")
def add_manager(payload: ManagerAccessIn, user: dict = Depends(current_user)):
    return grant_manager_access(user, payload)


@api.delete("/api/superadmin/managers/{telegram_id}")
def delete_manager(telegram_id: int, user: dict = Depends(current_user)):
    return revoke_manager_access(user, telegram_id)


@api.post("/api/support-tickets")
def support_ticket(payload: TicketIn, user: dict = Depends(current_user)):
    return submit_ticket(user, payload)


@api.post("/api/check-contact")
def contact_check(payload: ContactCheckIn, user: dict = Depends(current_user)):
    return check_contact(payload)


@api.post("/api/check-blocked")
def blocked_check(payload: ContactCheckIn, user: dict = Depends(current_user)):
    return check_contact(payload, blocked_only=True)


@api.post("/api/check-manager")
def manager_check(payload: ContactCheckIn, user: dict = Depends(current_user)):
    return check_manager(payload)


def open_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Открыть",
                web_app=WebAppInfo(url=webapp_url()),
            )
        ]]
    )


async def configure_menu(bot: Bot, chat_id: int | None = None) -> None:
    """Set the Mini App button globally and for the current private chat."""
    menu_button = MenuButtonWebApp(text="Открыть", web_app=WebAppInfo(url=webapp_url()))
    await bot.set_chat_menu_button(menu_button=menu_button)
    if chat_id is not None:
        await bot.set_chat_menu_button(chat_id=chat_id, menu_button=menu_button)


async def send_portal(message: Message) -> None:
    if message.from_user:
        save_telegram_user(telegram_message_user(message))
    # The persistent menu button is configured during application startup.
    # Do not call Telegram's setChatMenuButton for every /start: a transient
    # Telegram API timeout must never prevent the user from receiving the
    # Mini App button and produce a failed webhook response.
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


@dp.message()
async def start_fallback(message: Message):
    """Handle a plain /start that arrives without a Telegram command entity.

    Some Telegram clients resend the visible command as plain text after a
    deployment or a restored chat. ``CommandStart`` intentionally ignores
    that shape, so keep this narrow fallback after all regular command
    handlers. It never reacts to ordinary user messages.
    """
    command = (message.text or "").strip().split(maxsplit=1)[0].lower()
    if command == "/start" or command.startswith("/start@"):
        await send_portal(message)


@api.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    bot = Bot(TOKEN)
    try:
        await dp.feed_raw_update(bot, await request.json())
    finally:
        await bot.session.close()
    return {"ok": True}


async def bot_setup():
    """Keep the Telegram webhook registered without blocking FastAPI.

    Railway may start serving HTTP before Telegram becomes reachable.  The
    previous one-shot setup made this failure hard to diagnose and discarded
    queued /start updates on every deployment.  Retry setup safely and retain
    updates so users can always receive the portal message after a restart.
    """
    webhook_url = f"{PUBLIC_APP_URL}{WEBHOOK_PATH}"
    bot = Bot(TOKEN)
    try:
        while True:
            try:
                await bot.set_my_commands([
                    BotCommand(command="start", description="Открыть Partners Agent"),
                    BotCommand(command="menu", description="Open app menu"),
                    BotCommand(command="help", description="How to use the app"),
                ])
                await configure_menu(bot)
                await bot.set_webhook(
                    webhook_url,
                    allowed_updates=dp.resolve_used_update_types(),
                    drop_pending_updates=False,
                )
                info = await bot.get_webhook_info()
                logger.info(
                    "Telegram webhook configured: url=%s pending=%s last_error=%s",
                    info.url,
                    info.pending_update_count,
                    info.last_error_message or "none",
                )
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Telegram webhook setup failed; retrying in 15 seconds")
                await asyncio.sleep(15)
    finally:
        await bot.session.close()


async def serve():
    server = uvicorn.Server(
        uvicorn.Config(api, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
    )
    await asyncio.gather(server.serve(), bot_setup())


if __name__ == "__main__":
    asyncio.run(serve())
