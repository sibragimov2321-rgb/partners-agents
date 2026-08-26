import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
import time
from typing import Literal
from urllib.parse import parse_qsl
from zoneinfo import ZoneInfo

from fastapi import Header, HTTPException
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.orm import Session

from .storage import (
    AgentApplication,
    AgentApplicationHistory,
    AgentDocument,
    ApplicationAuditLog,
    DeletedApplicationAudit,
    GeoAgentSetting,
    Giveaway,
    GiveawayAuditLog,
    GiveawayBroadcast,
    GiveawayParticipant,
    GiveawayWinner,
    ManagerAccess,
    ManagerAccessAudit,
    SupportTicket,
    TelegramUser,
    engine,
    save_telegram_user,
)

TOKEN = os.environ["BOT_TOKEN"]
MANAGER_ID_LIST = [item.strip() for item in os.getenv("ADMIN_IDS", "").split(",") if item.strip()]
MANAGER_IDS = set(MANAGER_ID_LIST)
OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID", "").strip()
if not OWNER_TELEGRAM_ID:
    # Backward-compatible fallback: accept only the first legacy superadmin ID.
    legacy_superadmins = [item.strip() for item in os.getenv("SUPERADMIN_IDS", "").split(",") if item.strip()]
    OWNER_TELEGRAM_ID = legacy_superadmins[0] if legacy_superadmins else (MANAGER_ID_LIST[0] if MANAGER_ID_LIST else "")
SUPERADMIN_IDS = {OWNER_TELEGRAM_ID} if OWNER_TELEGRAM_ID else set()
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lower().lstrip("@")
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
DOCUMENT_KINDS = {"deposit", "passport", "selfie"}
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
PHONE_RE = re.compile(r"^\+?[0-9][0-9 ()-]{5,23}$")

try:
    PROJECT_TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Moscow"))
except Exception:
    PROJECT_TIMEZONE = timezone.utc


def _utc_naive(value: datetime) -> datetime:
    """Persist timestamps in the same UTC-naive format as existing tables."""
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def _giveaway_utc_naive(value: datetime) -> datetime:
    """Treat a datetime-local giveaway value as project local time, then store UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=PROJECT_TIMEZONE)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _giveaway_deadline_is_future(value: datetime, now: datetime | None = None) -> bool:
    """The registration deadline must be after the current instant, not tomorrow."""
    return value > (now if now is not None else datetime.utcnow())


def _valid_image(data: bytes, mime_type: str) -> bool:
    signatures = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": len(data) > 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    return signatures.get(mime_type, False)


def telegram_user(init_data: str | None) -> dict:
    if not init_data:
        raise HTTPException(401, "Откройте приложение из Telegram.")
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", "")
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash) or "user" not in data:
        raise HTTPException(401, "Не удалось проверить авторизацию Telegram.")
    try:
        auth_date = int(data.get("auth_date", "0"))
        user = json.loads(data["user"])
    except (TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(401, "Некорректные данные Telegram.")
    if auth_date and abs(time.time() - auth_date) > 86400:
        raise HTTPException(401, "Сессия Telegram устарела. Откройте приложение заново.")
    if "id" not in user:
        raise HTTPException(401, "Telegram ID не найден.")
    return user


def current_user(x_telegram_init_data: str | None = Header(default=None)) -> dict:
    user = telegram_user(x_telegram_init_data)
    save_telegram_user(user)
    return user


def is_manager_id(telegram_id: int | str) -> bool:
    value = str(telegram_id)
    if value in MANAGER_IDS or value in SUPERADMIN_IDS:
        return True
    with Session(engine) as session:
        return bool(session.scalar(select(ManagerAccess.id).where(
            ManagerAccess.telegram_id == int(value),
            ManagerAccess.active.is_(True),
        )))


def is_superadmin_id(telegram_id: int | str) -> bool:
    return str(telegram_id) in SUPERADMIN_IDS


def manager_user(user: dict) -> dict:
    if not is_manager_id(user.get("id")):
        raise HTTPException(403, "Недостаточно прав.")
    return user


def superadmin_user(user: dict) -> dict:
    if not is_superadmin_id(user.get("id")):
        raise HTTPException(403, "Только владелец может управлять менеджерами.")
    return user


def _audit(session: Session, application_id: int, actor_id: int, action: str, details: str | None = None) -> None:
    session.add(ApplicationAuditLog(
        application_id=application_id,
        actor_telegram_id=actor_id,
        action=action,
        details=details[:2000] if details else None,
    ))


def _set_status(
    session: Session,
    application: AgentApplication,
    new_status: str,
    actor_id: int,
    comment: str | None = None,
) -> None:
    previous = application.status
    if previous == new_status:
        return
    application.status = new_status
    session.add(AgentApplicationHistory(
        application_id=application.id,
        actor_telegram_id=actor_id,
        previous_status=previous,
        new_status=new_status,
        comment=(comment or "").strip()[:2000] or None,
    ))


def _document_flags(session: Session, application_id: int) -> dict[str, bool]:
    kinds = session.scalars(select(AgentDocument.kind).where(AgentDocument.application_id == application_id)).all()
    return {kind: kind in kinds for kind in DOCUMENT_KINDS}


def application_payload(application: AgentApplication, session: Session) -> dict:
    setting = None
    if application.geo_code:
        setting = session.scalar(select(GeoAgentSetting).where(GeoAgentSetting.geo_code == application.geo_code))
    if setting is None and application.country:
        setting = session.scalar(select(GeoAgentSetting).where(GeoAgentSetting.country.ilike(application.country)))
    history = session.scalars(select(AgentApplicationHistory).where(
        AgentApplicationHistory.application_id == application.id,
    ).order_by(AgentApplicationHistory.created_at.asc(), AgentApplicationHistory.id.asc())).all()
    return {
        "id": application.id,
        "application_number": f"PA-{application.id:06d}",
        "agent_id": application.agent_id,
        "telegram_id": application.telegram_id,
        "telegram_username": application.telegram_username,
        "status": application.status,
        "account_identifier": application.account_identifier,
        "manager_comment": application.manager_comment,
        "resume_state": application.resume_state,
        "name": application.name,
        "first_name": application.first_name,
        "last_name": application.last_name,
        "email": application.email,
        "phone": application.phone,
        "country": application.country,
        "geo_code": application.geo_code,
        "city": application.city,
        "cashdesk_name": application.cashdesk_name,
        "location": application.location,
        "experience": application.experience,
        "has_experience": application.has_experience,
        "planned_players": application.planned_players,
        "physical_point": application.physical_point,
        "referral_agent": application.referral_agent,
        "assigned_manager_id": application.assigned_manager_id,
        "source": application.source,
        "source_other": application.source_other,
        "documents": _document_flags(session, application.id),
        "created_at": application.created_at.isoformat() if application.created_at else None,
        "updated_at": application.updated_at.isoformat() if application.updated_at else None,
        "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
        "approved_at": application.approved_at.isoformat() if application.approved_at else None,
        "activated_at": application.activated_at.isoformat() if application.activated_at else None,
        "deposit_submitted_at": application.deposit_submitted_at.isoformat() if application.deposit_submitted_at else None,
        "documents_submitted_at": application.documents_submitted_at.isoformat() if application.documents_submitted_at else None,
        "documents_verified_at": application.documents_verified_at.isoformat() if application.documents_verified_at else None,
        "geo_setting": ({
            "geo_code": setting.geo_code,
            "country": setting.country,
            "currency": setting.currency,
            "minimum_deposit": setting.minimum_deposit,
        } if setting else None),
        "history": [{
            "previous_status": item.previous_status,
            "new_status": item.new_status,
            "actor_telegram_id": item.actor_telegram_id,
            "comment": item.comment,
            "created_at": item.created_at.isoformat(),
        } for item in history],
    }


def profile_payload(user: dict) -> dict:
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        # The project uses boolean capability flags, not string role names.
        # ADMIN_IDS and database managers are managers; the owner is also a
        # superadmin. Keep a dedicated capability for the Giveaway UI so both
        # frontend and backend use the same effective permission.
        is_manager = is_manager_id(user["id"])
        is_superadmin = is_superadmin_id(user["id"])
        is_agent = bool(application and application.status == "approved" and application.agent_id)
        display_role = (
            "superadmin" if is_superadmin else
            "manager" if is_manager else
            "agent" if is_agent else
            "user"
        )
        return {
            "telegram": user,
            "is_manager": is_manager or is_superadmin,
            "is_superadmin": is_superadmin,
            "is_agent": is_agent,
            "display_role": display_role,
            "can_manage_giveaways": is_manager or is_superadmin,
            "application": application_payload(application, session) if application else None,
        }


class AccountStartIn(BaseModel):
    account_identifier: str = Field(min_length=3, max_length=160)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None

    @model_validator(mode="after")
    def contact_required(self):
        self.phone = self.phone.strip() if self.phone else None
        if not self.phone and not self.email:
            raise ValueError("Укажите телефон или email.")
        if self.phone and not PHONE_RE.fullmatch(self.phone):
            raise ValueError("Проверьте формат телефона.")
        return self


class ApplicationDraftIn(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=160)
    telegram_username: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=120)
    cashdesk_name: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=300)
    experience: str | None = Field(default=None, max_length=3000)
    has_experience: bool | None = None
    planned_players: str | None = Field(default=None, max_length=32)
    physical_point: bool | None = None
    referral_agent: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, max_length=80)
    source_other: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_phone(self):
        if self.phone:
            self.phone = self.phone.strip()
            if not PHONE_RE.fullmatch(self.phone):
                raise ValueError("Проверьте формат телефона.")
        if self.telegram_username:
            self.telegram_username = self.telegram_username.strip().lstrip("@")
            if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", self.telegram_username):
                raise ValueError("Проверьте Telegram username.")
        return self


class ApplicationIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    country: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=5, max_length=64)
    experience: str | None = Field(default=None, max_length=3000)


class ManagerActionIn(BaseModel):
    action: Literal[
        "start_review", "pre_approve", "open_deposit", "confirm_deposit",
        "confirm_documents", "request_information", "activate", "reject",
        "comment", "approve", "changes",
    ]
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def reason_required(self):
        if self.action in {"changes", "request_information", "reject"} and not (self.comment or "").strip():
            raise ValueError("Для этого действия нужен комментарий.")
        return self


class DeleteApplicationIn(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class SubmitProfileIn(BaseModel):
    confirmed_truth: bool = False


class GeoSettingIn(BaseModel):
    country: str = Field(min_length=2, max_length=100)
    currency: str = Field(min_length=3, max_length=8)
    minimum_deposit: int = Field(ge=0, le=1_000_000)
    active: bool = True


class TicketIn(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    body: str = Field(min_length=2, max_length=5000)


class ContactCheckIn(BaseModel):
    query: str = Field(min_length=2, max_length=254)


class ManagerAccessIn(BaseModel):
    telegram_id: int | None = Field(default=None, gt=0)
    username: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def manager_identifier_required(self):
        if self.username:
            self.username = self.username.strip().lstrip("@").lower()
            if not re.fullmatch(r"[a-z0-9_]{5,32}", self.username):
                raise ValueError("Проверьте Telegram username.")
        if not self.telegram_id and not self.username:
            raise ValueError("Укажите Telegram ID или username.")
        return self


class GiveawayCreateIn(BaseModel):
    title: str = Field(default="", max_length=180)
    description: str = Field(default="", max_length=5000)
    prize: str = Field(min_length=1, max_length=300)
    winner_count: int = Field(ge=1, le=100)
    start_at: datetime
    end_at: datetime
    geo_codes: list[str] = Field(min_length=1, max_length=50)
    rules: str = Field(default="", max_length=8000)

    @model_validator(mode="after")
    def validate_dates_and_geos(self):
        self.start_at = _giveaway_utc_naive(self.start_at)
        self.end_at = _giveaway_utc_naive(self.end_at)
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.prize = self.prize.strip()
        self.geo_codes = sorted({code.strip().upper() for code in self.geo_codes if code.strip()})
        if not self.geo_codes:
            raise ValueError("Выберите хотя бы один GEO.")
        if self.end_at <= self.start_at:
            raise ValueError("Окончание розыгрыша должно быть позже начала.")
        return self


class GiveawayUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    prize: str | None = Field(default=None, min_length=1, max_length=300)
    winner_count: int | None = Field(default=None, ge=1, le=100)
    start_at: datetime | None = None
    end_at: datetime | None = None
    geo_codes: list[str] | None = Field(default=None, max_length=50)
    rules: str | None = Field(default=None, max_length=8000)

    @model_validator(mode="after")
    def normalize_dates(self):
        if self.start_at:
            self.start_at = _giveaway_utc_naive(self.start_at)
        if self.end_at:
            self.end_at = _giveaway_utc_naive(self.end_at)
        return self


class GiveawayJoinIn(BaseModel):
    geo_code: str = Field(min_length=2, max_length=16)
    player_id: str = Field(min_length=3, max_length=80)

    @model_validator(mode="after")
    def clean_player_id(self):
        self.geo_code = self.geo_code.strip().upper()
        self.player_id = self.player_id.strip().replace(" ", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", self.player_id):
            raise ValueError("Player ID может содержать только буквы, цифры, дефис и подчёркивание.")
        return self


class GiveawayParticipantActionIn(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class GiveawayLifecycleIn(BaseModel):
    action: Literal["launch", "close", "cancel"]


class GiveawayBroadcastIn(BaseModel):
    audience: Literal["all_participants", "geo", "winners"]
    message: str = Field(min_length=2, max_length=4000)
    geo_codes: list[str] = Field(default_factory=list, max_length=50)
    button_text: str | None = Field(default=None, max_length=80)


def list_geo_settings(user: dict, include_inactive: bool = False) -> list[dict]:
    if include_inactive:
        manager_user(user)
    with Session(engine) as session:
        query = select(GeoAgentSetting).order_by(GeoAgentSetting.country.asc())
        if not include_inactive:
            query = query.where(GeoAgentSetting.active.is_(True))
        settings = session.scalars(query).all()
        return [{
            "geo_code": item.geo_code,
            "country": item.country,
            "currency": item.currency,
            "minimum_deposit": item.minimum_deposit,
            "active": item.active,
        } for item in settings]


def update_geo_setting(user: dict, geo_code: str, payload: GeoSettingIn) -> dict:
    superadmin_user(user)
    code = geo_code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_-]{2,16}", code):
        raise HTTPException(422, "Некорректный GEO-код.")
    with Session(engine) as session:
        setting = session.scalar(select(GeoAgentSetting).where(GeoAgentSetting.geo_code == code))
        if setting is None:
            setting = GeoAgentSetting(geo_code=code)
            session.add(setting)
        setting.country = payload.country.strip()
        setting.currency = payload.currency.strip().upper()
        setting.minimum_deposit = payload.minimum_deposit
        setting.active = payload.active
        setting.updated_at = datetime.utcnow()
        session.commit()
        return {
            "geo_code": setting.geo_code,
            "country": setting.country,
            "currency": setting.currency,
            "minimum_deposit": setting.minimum_deposit,
            "active": setting.active,
        }


# Giveaway module -----------------------------------------------------------
# Kept isolated from applications: a player can participate without being an
# agent, and all mutations remain protected by the existing manager role.
def _giveaway_uses_schedule(giveaway: Giveaway) -> bool:
    return giveaway.start_at is not None and giveaway.end_at is not None


def _giveaway_start(giveaway: Giveaway) -> datetime:
    return giveaway.start_at or giveaway.created_at


def _giveaway_end(giveaway: Giveaway) -> datetime:
    return giveaway.end_at or giveaway.entry_deadline


def _utc_iso(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat()


def _sync_giveaway_schedule(giveaway: Giveaway, now: datetime | None = None) -> bool:
    """Advance a new giveaway from draft → active → closed by its schedule."""
    if not _giveaway_uses_schedule(giveaway) or giveaway.status in {"cancelled", "drawn"}:
        return False
    moment = now or datetime.utcnow()
    previous = giveaway.status
    if moment >= _giveaway_end(giveaway) and giveaway.status in {"draft", "active"}:
        giveaway.status = "closed"
    elif moment >= _giveaway_start(giveaway) and giveaway.status == "draft":
        giveaway.status = "active"
    if giveaway.status != previous:
        giveaway.updated_at = moment
        return True
    return False


def _sync_scheduled_giveaways(session: Session, now: datetime | None = None) -> None:
    moment = now or datetime.utcnow()
    giveaways = session.scalars(select(Giveaway).where(
        Giveaway.start_at.is_not(None),
        Giveaway.end_at.is_not(None),
        Giveaway.status.in_(["draft", "active"]),
    )).all()
    if any(_sync_giveaway_schedule(giveaway, moment) for giveaway in giveaways):
        session.commit()


def _giveaway_geos(giveaway: Giveaway) -> list[str]:
    try:
        value = json.loads(giveaway.geo_codes or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        value = []
    return [str(code).upper() for code in value if str(code).strip()]


def _giveaway_audit(
    session: Session,
    giveaway_id: int,
    actor_id: int,
    action: str,
    participant_id: int | None = None,
    details: dict | None = None,
) -> None:
    session.add(GiveawayAuditLog(
        giveaway_id=giveaway_id,
        actor_telegram_id=actor_id,
        action=action,
        participant_id=participant_id,
        details=json.dumps(details, ensure_ascii=False)[:5000] if details else None,
    ))


def _participant_payload(
    participant: GiveawayParticipant,
    manager: bool = False,
    owner: bool = False,
) -> dict:
    player_id = participant.player_id
    masked = ("*" * max(0, len(player_id) - 4)) + player_id[-4:]
    return {
        "id": participant.id,
        "participant_number": participant.participant_number,
        "telegram_id": participant.telegram_id if manager else None,
        "telegram_username": participant.telegram_username if manager else None,
        # A participant can see their own Player ID, but public lists always
        # keep it masked and managers receive it only through protected APIs.
        "player_id": player_id if manager or owner else masked,
        "geo_code": participant.geo_code,
        "status": participant.status,
        "exclusion_reason": participant.exclusion_reason if manager else None,
        "excluded_at": participant.excluded_at.isoformat() if participant.excluded_at else None,
        "joined_at": participant.joined_at.isoformat() if participant.joined_at else None,
    }


def _giveaway_payload(giveaway: Giveaway, session: Session, manager: bool = False) -> dict:
    participant_totals = session.execute(select(
        func.count(GiveawayParticipant.id),
        func.coalesce(func.sum(case((GiveawayParticipant.status == "active", 1), else_=0)), 0),
        func.coalesce(func.sum(case((GiveawayParticipant.status == "excluded", 1), else_=0)), 0),
    ).where(GiveawayParticipant.giveaway_id == giveaway.id)).one()
    winners = session.scalars(select(GiveawayWinner).where(
        GiveawayWinner.giveaway_id == giveaway.id,
        GiveawayWinner.status == "active",
    ).order_by(GiveawayWinner.rank.asc(), GiveawayWinner.id.asc())).all()
    winner_participant_ids = [winner.participant_id for winner in winners]
    winner_participants = session.scalars(select(GiveawayParticipant).where(
        GiveawayParticipant.id.in_(winner_participant_ids),
    )).all() if winner_participant_ids else []
    participant_by_id = {item.id: item for item in winner_participants}
    winner_rows = []
    for winner in winners:
        participant = participant_by_id.get(winner.participant_id)
        if participant:
            row = {
                "rank": winner.rank,
                "selected_at": winner.selected_at.isoformat(),
                "participant": _participant_payload(participant, manager=manager),
            }
            if manager:
                row["winner_id"] = winner.id
            winner_rows.append(row)
    return {
        "id": giveaway.id,
        "number": f"GW-{giveaway.id:04d}",
        "title": giveaway.title or "🎁 Розыгрыш",
        "description": giveaway.description or "",
        "prize": giveaway.prize,
        "winner_count": giveaway.winner_count,
        "start_at": _utc_iso(_giveaway_start(giveaway)),
        "end_at": _utc_iso(_giveaway_end(giveaway)),
        # Kept for legacy read-only clients during the Mini App transition.
        "entry_deadline": _utc_iso(_giveaway_end(giveaway)),
        "draw_date": _utc_iso(_giveaway_end(giveaway)),
        "geo_codes": _giveaway_geos(giveaway),
        "rules": giveaway.rules,
        "status": giveaway.status,
        "banner_url": f"/api/giveaways/{giveaway.id}/banner" if giveaway.banner_data else None,
        "created_at": giveaway.created_at.isoformat(),
        "updated_at": giveaway.updated_at.isoformat(),
        "participants_count": int(participant_totals[0] or 0),
        "active_participants_count": int(participant_totals[1] or 0),
        "excluded_participants_count": int(participant_totals[2] or 0),
        "winners": winner_rows,
        **({"created_by": giveaway.created_by} if manager else {}),
    }


def _get_giveaway(session: Session, giveaway_id: int) -> Giveaway:
    giveaway = session.get(Giveaway, giveaway_id)
    if not giveaway:
        raise HTTPException(404, "Розыгрыш не найден.")
    return giveaway


def active_giveaway(user: dict) -> dict | None:
    with Session(engine) as session:
        _sync_scheduled_giveaways(session)
        giveaway = session.scalar(select(Giveaway).where(
            Giveaway.status == "active",
        ).order_by(Giveaway.created_at.desc(), Giveaway.id.desc()))
        return _giveaway_payload(giveaway, session) if giveaway else None


def giveaway_participation(user: dict, giveaway_id: int) -> dict | None:
    with Session(engine) as session:
        participant = session.scalar(select(GiveawayParticipant).where(
            GiveawayParticipant.giveaway_id == giveaway_id,
            GiveawayParticipant.telegram_id == int(user["id"]),
        ))
        return _participant_payload(participant, owner=True) if participant else None


def join_giveaway(user: dict, giveaway_id: int, payload: GiveawayJoinIn) -> dict:
    now = datetime.utcnow()
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        _sync_giveaway_schedule(giveaway, now)
        if _giveaway_uses_schedule(giveaway) and now < _giveaway_start(giveaway):
            raise HTTPException(409, "Розыгрыш ещё не начался.")
        if giveaway.status != "active" or _giveaway_end(giveaway) <= now:
            raise HTTPException(409, "Регистрация в этом розыгрыше уже закрыта.")
        if payload.geo_code not in _giveaway_geos(giveaway):
            raise HTTPException(422, "Выбранный GEO не участвует в этом розыгрыше.")
        existing = session.scalar(select(GiveawayParticipant).where(
            GiveawayParticipant.giveaway_id == giveaway.id,
            GiveawayParticipant.telegram_id == int(user["id"]),
        ))
        if existing:
            raise HTTPException(409, "Вы уже участвуете в текущем розыгрыше.")
        duplicate = session.scalar(select(GiveawayParticipant).where(
            GiveawayParticipant.giveaway_id == giveaway.id,
            GiveawayParticipant.player_id == payload.player_id,
        ))
        if duplicate:
            raise HTTPException(409, "Этот Player ID уже участвует в текущем розыгрыше.")
        participant = GiveawayParticipant(
            giveaway_id=giveaway.id,
            telegram_id=int(user["id"]),
            telegram_username=(user.get("username") or "").strip().lstrip("@") or None,
            player_id=payload.player_id,
            geo_code=payload.geo_code,
            participant_number="pending",
        )
        session.add(participant)
        session.flush()
        participant.participant_number = f"#{participant.id:06d}"
        giveaway.updated_at = now
        _giveaway_audit(session, giveaway.id, int(user["id"]), "participant_joined", participant.id, {
            "geo_code": participant.geo_code,
        })
        session.commit()
        session.refresh(participant)
        return _participant_payload(participant, owner=True)


def public_winners(user: dict, giveaway_id: int) -> list[dict]:
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        return _giveaway_payload(giveaway, session)["winners"]


def create_giveaway(user: dict, payload: GiveawayCreateIn) -> dict:
    manager_user(user)
    if not _giveaway_deadline_is_future(payload.end_at):
        raise HTTPException(422, "Дата и время окончания розыгрыша должны быть позже текущего времени.")
    with Session(engine) as session:
        giveaway = Giveaway(
            title=payload.title.strip(),
            description=payload.description.strip(),
            prize=payload.prize.strip(),
            winner_count=payload.winner_count,
            entry_deadline=payload.end_at,
            draw_date=payload.end_at,
            start_at=payload.start_at,
            end_at=payload.end_at,
            geo_codes=json.dumps(payload.geo_codes),
            rules=payload.rules.strip(),
            created_by=int(user["id"]),
            # New giveaways are activated by their configured start time.
            # SQLAlchemy column defaults are applied on INSERT, therefore set
            # this explicitly before the first schedule sync.
            status="active" if payload.start_at <= datetime.utcnow() else "draft",
        )
        _sync_giveaway_schedule(giveaway)
        session.add(giveaway)
        session.flush()
        _giveaway_audit(session, giveaway.id, int(user["id"]), "created", details={
            "winner_count": giveaway.winner_count,
            "geo_codes": payload.geo_codes,
        })
        session.commit()
        session.refresh(giveaway)
        return _giveaway_payload(giveaway, session, manager=True)


def update_giveaway(user: dict, giveaway_id: int, payload: GiveawayUpdateIn) -> dict:
    manager_user(user)
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        if giveaway.status in {"drawn", "cancelled"}:
            raise HTTPException(409, "Завершённый розыгрыш редактировать нельзя.")
        values = payload.model_dump(exclude_unset=True)
        if "geo_codes" in values and values["geo_codes"] is not None:
            codes = sorted({code.strip().upper() for code in values["geo_codes"] if code.strip()})
            if not codes:
                raise HTTPException(422, "Выберите хотя бы один GEO.")
            values["geo_codes"] = json.dumps(codes)
        if "end_at" in values:
            values["entry_deadline"] = values["end_at"]
            values["draw_date"] = values["end_at"]
        for field, value in values.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(giveaway, field, value)
        if _giveaway_uses_schedule(giveaway):
            if _giveaway_end(giveaway) <= _giveaway_start(giveaway):
                raise HTTPException(422, "Окончание розыгрыша должно быть позже начала.")
            if "end_at" in values and not _giveaway_deadline_is_future(_giveaway_end(giveaway)):
                raise HTTPException(422, "Дата и время окончания розыгрыша должны быть позже текущего времени.")
        elif giveaway.draw_date < giveaway.entry_deadline:
            raise HTTPException(422, "Дата проведения не может быть раньше окончания регистрации.")
        _sync_giveaway_schedule(giveaway)
        giveaway.updated_at = datetime.utcnow()
        _giveaway_audit(session, giveaway.id, int(user["id"]), "updated", details={"fields": sorted(values)})
        session.commit()
        session.refresh(giveaway)
        return _giveaway_payload(giveaway, session, manager=True)


def manager_giveaways(user: dict) -> list[dict]:
    manager_user(user)
    with Session(engine) as session:
        _sync_scheduled_giveaways(session)
        giveaways = session.scalars(select(Giveaway).order_by(Giveaway.updated_at.desc(), Giveaway.id.desc())).all()
        return [_giveaway_payload(item, session, manager=True) for item in giveaways]


def manager_giveaway(user: dict, giveaway_id: int) -> dict:
    manager_user(user)
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        if _sync_giveaway_schedule(giveaway):
            session.commit()
        return _giveaway_payload(giveaway, session, manager=True)


def giveaway_action(user: dict, giveaway_id: int, action: Literal["launch", "close", "cancel"]) -> dict:
    manager_user(user)
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        _sync_giveaway_schedule(giveaway)
        if _giveaway_uses_schedule(giveaway) and action in {"launch", "close"}:
            raise HTTPException(409, "Статус этого розыгрыша меняется автоматически по времени.")
        old_status = giveaway.status
        allowed = {
            "launch": {"draft"},
            "close": {"active"},
            "cancel": {"draft", "active", "closed"},
        }
        if giveaway.status not in allowed[action]:
            raise HTTPException(409, "Это действие сейчас недоступно.")
        if action == "launch":
            another_active = session.scalar(select(Giveaway.id).where(
                Giveaway.status == "active",
                Giveaway.id != giveaway.id,
            ))
            if another_active:
                raise HTTPException(409, "Сначала закройте или отмените текущий активный розыгрыш.")
        giveaway.status = {"launch": "active", "close": "closed", "cancel": "cancelled"}[action]
        giveaway.updated_at = datetime.utcnow()
        _giveaway_audit(session, giveaway.id, int(user["id"]), action, details={"from": old_status, "to": giveaway.status})
        session.commit()
        session.refresh(giveaway)
        return _giveaway_payload(giveaway, session, manager=True)


def list_giveaway_participants(
    user: dict,
    giveaway_id: int,
    status: str | None = None,
    geo_code: str | None = None,
    query: str | None = None,
) -> dict:
    manager_user(user)
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        statement = select(GiveawayParticipant).where(GiveawayParticipant.giveaway_id == giveaway.id)
        if status:
            statement = statement.where(GiveawayParticipant.status == status)
        if geo_code:
            statement = statement.where(GiveawayParticipant.geo_code == geo_code.strip().upper())
        if query:
            cleaned = query.strip().lstrip("#")
            statement = statement.where(or_(
                GiveawayParticipant.player_id.ilike(f"%{cleaned}%"),
                GiveawayParticipant.participant_number.ilike(f"%{cleaned}%"),
                GiveawayParticipant.telegram_username.ilike(f"%{cleaned.lstrip('@')}%"),
            ))
        participants = session.scalars(statement.order_by(
            GiveawayParticipant.joined_at.desc(), GiveawayParticipant.id.desc(),
        ).limit(250)).all()
        all_participants = session.scalars(select(GiveawayParticipant).where(
            GiveawayParticipant.giveaway_id == giveaway.id,
        )).all()
        by_geo: dict[str, int] = {}
        for item in all_participants:
            by_geo[item.geo_code] = by_geo.get(item.geo_code, 0) + 1
        return {
            "total": len(all_participants),
            "by_geo": by_geo,
            "participants": [_participant_payload(item, manager=True) for item in participants],
        }


def set_participant_excluded(user: dict, giveaway_id: int, participant_id: int, payload: GiveawayParticipantActionIn) -> dict:
    manager_user(user)
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        participant = session.get(GiveawayParticipant, participant_id)
        if not participant or participant.giveaway_id != giveaway.id:
            raise HTTPException(404, "Участник не найден.")
        if participant.status == "winner":
            raise HTTPException(409, "Победителя нельзя исключить. Используйте перевыбор.")
        if participant.status == "excluded":
            raise HTTPException(409, "Участник уже исключён.")
        participant.status = "excluded"
        participant.exclusion_reason = payload.reason.strip()
        participant.excluded_by = int(user["id"])
        participant.excluded_at = datetime.utcnow()
        participant.updated_at = datetime.utcnow()
        _giveaway_audit(session, giveaway.id, int(user["id"]), "participant_excluded", participant.id, {"reason": participant.exclusion_reason})
        session.commit()
        return _participant_payload(participant, manager=True)


def restore_participant(user: dict, giveaway_id: int, participant_id: int) -> dict:
    manager_user(user)
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        participant = session.get(GiveawayParticipant, participant_id)
        if not participant or participant.giveaway_id != giveaway.id:
            raise HTTPException(404, "Участник не найден.")
        if participant.status != "excluded":
            raise HTTPException(409, "Вернуть можно только исключённого участника.")
        participant.status = "active"
        participant.exclusion_reason = None
        participant.excluded_by = None
        participant.excluded_at = None
        participant.updated_at = datetime.utcnow()
        _giveaway_audit(session, giveaway.id, int(user["id"]), "participant_restored", participant.id)
        session.commit()
        return _participant_payload(participant, manager=True)


def draw_giveaway(user: dict, giveaway_id: int) -> dict:
    """Atomically choose unique winners only from active participants."""
    manager_user(user)
    actor_id = int(user["id"])
    with Session(engine) as session:
        statement = select(Giveaway).where(Giveaway.id == giveaway_id)
        if engine.dialect.name == "postgresql":
            statement = statement.with_for_update()
        giveaway = session.scalar(statement)
        if not giveaway:
            raise HTTPException(404, "Розыгрыш не найден.")
        now = datetime.utcnow()
        _sync_giveaway_schedule(giveaway, now)
        if _giveaway_uses_schedule(giveaway) and now < _giveaway_end(giveaway):
            raise HTTPException(409, "Провести розыгрыш можно после его окончания.")
        if giveaway.status not in {"active", "closed"}:
            raise HTTPException(409, "Провести розыгрыш можно только для активного или закрытого события.")
        existing = session.scalar(select(GiveawayWinner.id).where(
            GiveawayWinner.giveaway_id == giveaway.id,
            GiveawayWinner.status == "active",
        ))
        if existing:
            raise HTTPException(409, "Победители уже выбраны.")
        candidates = session.scalars(select(GiveawayParticipant).where(
            GiveawayParticipant.giveaway_id == giveaway.id,
            GiveawayParticipant.status == "active",
        )).all()
        if len(candidates) < giveaway.winner_count:
            raise HTTPException(422, "Недостаточно валидных участников для выбора победителей.")
        selected = secrets.SystemRandom().sample(candidates, giveaway.winner_count)
        for rank, participant in enumerate(selected, start=1):
            participant.status = "winner"
            participant.updated_at = datetime.utcnow()
            session.add(GiveawayWinner(
                giveaway_id=giveaway.id,
                participant_id=participant.id,
                rank=rank,
                selected_by=actor_id,
            ))
        giveaway.status = "drawn"
        giveaway.updated_at = datetime.utcnow()
        _giveaway_audit(session, giveaway.id, actor_id, "draw_completed", details={
            "winner_count": len(selected),
            "participant_ids": [item.id for item in selected],
        })
        session.commit()
        session.refresh(giveaway)
        return _giveaway_payload(giveaway, session, manager=True)


def replace_giveaway_winner(user: dict, giveaway_id: int, winner_id: int, payload: GiveawayParticipantActionIn) -> dict:
    manager_user(user)
    actor_id = int(user["id"])
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        if giveaway.status != "drawn":
            raise HTTPException(409, "Перевыбор доступен после проведения розыгрыша.")
        old = session.get(GiveawayWinner, winner_id)
        if not old or old.giveaway_id != giveaway.id or old.status != "active":
            raise HTTPException(404, "Победитель не найден.")
        candidates = session.scalars(select(GiveawayParticipant).where(
            GiveawayParticipant.giveaway_id == giveaway.id,
            GiveawayParticipant.status == "active",
        )).all()
        if not candidates:
            raise HTTPException(422, "Нет участника для перевыбора.")
        new_participant = secrets.choice(candidates)
        old_participant = session.get(GiveawayParticipant, old.participant_id)
        old.status = "replaced"
        old.replacement_reason = payload.reason.strip()
        if old_participant:
            old_participant.status = "excluded"
            old_participant.exclusion_reason = "Заменён при перевыборе победителя"
            old_participant.excluded_by = actor_id
            old_participant.excluded_at = datetime.utcnow()
        new_participant.status = "winner"
        session.add(GiveawayWinner(
            giveaway_id=giveaway.id,
            participant_id=new_participant.id,
            rank=old.rank,
            selected_by=actor_id,
            replacement_reason=payload.reason.strip(),
        ))
        _giveaway_audit(session, giveaway.id, actor_id, "winner_replaced", new_participant.id, {
            "old_winner_id": old.id,
            "reason": payload.reason.strip(),
        })
        session.commit()
        session.refresh(giveaway)
        return _giveaway_payload(giveaway, session, manager=True)


def create_giveaway_broadcast(user: dict, giveaway_id: int, payload: GiveawayBroadcastIn) -> dict:
    manager_user(user)
    actor_id = int(user["id"])
    geo_codes = sorted({code.strip().upper() for code in payload.geo_codes if code.strip()})
    if payload.audience == "geo" and not geo_codes:
        raise HTTPException(422, "Для рассылки по GEO выберите страны.")
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        statement = select(GiveawayParticipant.telegram_id).where(GiveawayParticipant.giveaway_id == giveaway.id)
        if payload.audience == "winners":
            statement = statement.join(GiveawayWinner, GiveawayWinner.participant_id == GiveawayParticipant.id).where(
                GiveawayWinner.status == "active",
            )
        else:
            statement = statement.where(GiveawayParticipant.status.in_(["active", "winner"]))
            if payload.audience == "geo":
                statement = statement.where(GiveawayParticipant.geo_code.in_(geo_codes))
        recipients = list(dict.fromkeys(session.scalars(statement).all()))
        broadcast = GiveawayBroadcast(
            giveaway_id=giveaway.id,
            actor_telegram_id=actor_id,
            audience=payload.audience,
            geo_codes=json.dumps(geo_codes),
            message=payload.message.strip(),
            button_text=(payload.button_text or "").strip() or None,
            status="sending",
        )
        session.add(broadcast)
        session.flush()
        _giveaway_audit(session, giveaway.id, actor_id, "broadcast_started", details={
            "broadcast_id": broadcast.id,
            "audience": payload.audience,
            "recipient_count": len(recipients),
        })
        session.commit()
        return {
            "broadcast_id": broadcast.id,
            "recipients": recipients,
            "message": broadcast.message,
            "button_text": broadcast.button_text,
        }


def complete_giveaway_broadcast(broadcast_id: int, sent_count: int, failed_count: int) -> None:
    with Session(engine) as session:
        broadcast = session.get(GiveawayBroadcast, broadcast_id)
        if not broadcast:
            return
        broadcast.sent_count = sent_count
        broadcast.failed_count = failed_count
        broadcast.status = "sent" if not failed_count else "completed_with_errors"
        broadcast.completed_at = datetime.utcnow()
        _giveaway_audit(session, broadcast.giveaway_id or 0, broadcast.actor_telegram_id, "broadcast_completed", details={
            "broadcast_id": broadcast.id,
            "sent": sent_count,
            "failed": failed_count,
        })
        session.commit()


def giveaway_history(user: dict, giveaway_id: int) -> list[dict]:
    manager_user(user)
    with Session(engine) as session:
        _get_giveaway(session, giveaway_id)
        rows = session.scalars(select(GiveawayAuditLog).where(
            GiveawayAuditLog.giveaway_id == giveaway_id,
        ).order_by(GiveawayAuditLog.created_at.desc(), GiveawayAuditLog.id.desc())).all()
        return [{
            "action": item.action,
            "actor_telegram_id": item.actor_telegram_id,
            "participant_id": item.participant_id,
            "details": item.details,
            "created_at": item.created_at.isoformat(),
        } for item in rows]


def save_giveaway_banner(user: dict, giveaway_id: int, filename: str, mime_type: str, data: bytes) -> dict:
    manager_user(user)
    if mime_type not in IMAGE_TYPES or not data or len(data) > MAX_DOCUMENT_BYTES or not _valid_image(data, mime_type):
        raise HTTPException(415, "Загрузите корректное изображение JPG, PNG или WEBP до 8 МБ.")
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        if giveaway.status in {"drawn", "cancelled"}:
            raise HTTPException(409, "Для завершённого розыгрыша баннер менять нельзя.")
        giveaway.banner_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename or "giveaway.jpg")[:255]
        giveaway.banner_mime_type = mime_type
        giveaway.banner_data = data
        giveaway.updated_at = datetime.utcnow()
        _giveaway_audit(session, giveaway.id, int(user["id"]), "banner_uploaded")
        session.commit()
        return {"uploaded": True, "banner_url": f"/api/giveaways/{giveaway.id}/banner"}


def load_giveaway_banner(giveaway_id: int) -> tuple[bytes, str, str]:
    with Session(engine) as session:
        giveaway = _get_giveaway(session, giveaway_id)
        if not giveaway.banner_data or not giveaway.banner_mime_type:
            raise HTTPException(404, "Баннер не добавлен.")
        return giveaway.banner_data, giveaway.banner_mime_type, giveaway.banner_filename or "giveaway.jpg"


def list_manager_access(user: dict) -> list[dict]:
    superadmin_user(user)
    configured = {int(value) for value in MANAGER_IDS | SUPERADMIN_IDS if value.isdigit()}
    with Session(engine) as session:
        stored = session.scalars(select(ManagerAccess).order_by(ManagerAccess.created_at.desc())).all()
        stored_by_id = {item.telegram_id: item for item in stored}
        telegram_ids = configured | set(stored_by_id)
        users = session.scalars(select(TelegramUser).where(TelegramUser.telegram_id.in_(telegram_ids))).all() if telegram_ids else []
        users_by_id = {item.telegram_id: item for item in users}
        result = []
        for telegram_id in sorted(telegram_ids, key=lambda value: (value not in configured, value)):
            profile = users_by_id.get(telegram_id)
            access = stored_by_id.get(telegram_id)
            result.append({
                "telegram_id": telegram_id,
                "username": profile.username if profile else None,
                "first_name": profile.first_name if profile else None,
                "active": True if telegram_id in configured else bool(access and access.active),
                "source": "environment" if telegram_id in configured else "database",
                "is_superadmin": str(telegram_id) in SUPERADMIN_IDS,
                "created_at": access.created_at.isoformat() if access else None,
            })
        return result


def grant_manager_access(user: dict, payload: ManagerAccessIn) -> dict:
    superadmin_user(user)
    with Session(engine) as session:
        profile = None
        if payload.telegram_id:
            target = int(payload.telegram_id)
            profile = session.scalar(select(TelegramUser).where(TelegramUser.telegram_id == target))
        else:
            profile = session.scalar(select(TelegramUser).where(TelegramUser.username.ilike(payload.username)))
            if profile is None:
                raise HTTPException(
                    404,
                    f"Пользователь @{payload.username} не найден. Попросите его сначала отправить /start этому боту.",
                )
            target = int(profile.telegram_id)
        resolved_username = profile.username if profile else payload.username
        if str(target) in SUPERADMIN_IDS:
            raise HTTPException(409, "Этот пользователь уже является владельцем.")
        access = session.scalar(select(ManagerAccess).where(ManagerAccess.telegram_id == target))
        if access is None:
            access = ManagerAccess(telegram_id=target, granted_by=int(user["id"]), active=True)
            session.add(access)
        else:
            access.active = True
            access.granted_by = int(user["id"])
            access.updated_at = datetime.utcnow()
        session.add(ManagerAccessAudit(actor_telegram_id=int(user["id"]), target_telegram_id=target, action="granted"))
        session.commit()
    return {"telegram_id": target, "username": resolved_username, "active": True}


def revoke_manager_access(user: dict, telegram_id: int) -> dict:
    superadmin_user(user)
    target = int(telegram_id)
    if str(target) in SUPERADMIN_IDS or str(target) in MANAGER_IDS:
        raise HTTPException(409, "Доступ из Railway нельзя удалить внутри приложения.")
    with Session(engine) as session:
        access = session.scalar(select(ManagerAccess).where(ManagerAccess.telegram_id == target))
        if not access:
            raise HTTPException(404, "Менеджер не найден.")
        access.active = False
        access.updated_at = datetime.utcnow()
        session.add(ManagerAccessAudit(actor_telegram_id=int(user["id"]), target_telegram_id=target, action="revoked"))
        session.commit()
    return {"telegram_id": target, "active": False}


def start_account(user: dict, payload: AccountStartIn) -> dict:
    """Compatibility entry point for older clients; new clients create a draft."""
    telegram_id = int(user["id"])
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == telegram_id))
        can_correct_account = application and application.status == "need_information"
        if application and application.status not in {"rejected", "draft"} and not can_correct_account:
            raise HTTPException(409, "Регистрация уже начата.")
        full_name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")])).strip() or "Telegram user"
        if application is None:
            application = AgentApplication(
                telegram_id=telegram_id,
                telegram_username=user.get("username"),
                name=full_name,
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email=str(payload.email or ""),
                phone=payload.phone or "",
                country="",
                account_identifier=payload.account_identifier.strip(),
                status="draft",
            )
            session.add(application)
            session.flush()
            session.add(AgentApplicationHistory(
                application_id=application.id,
                actor_telegram_id=telegram_id,
                previous_status=None,
                new_status="draft",
            ))
        else:
            application.telegram_username = user.get("username")
            application.account_identifier = payload.account_identifier.strip()
            application.phone = payload.phone or application.phone
            application.email = str(payload.email or application.email)
            _set_status(session, application, "under_review", telegram_id)
            application.manager_comment = None
            application.updated_at = datetime.utcnow()
        if application.status == "draft":
            _set_status(session, application, "under_review", telegram_id)
        _audit(session, application.id, telegram_id, "account_submitted")
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def save_application_draft(user: dict, payload: ApplicationDraftIn) -> dict:
    telegram_id = int(user["id"])
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == telegram_id))
        if application is None:
            application = AgentApplication(
                telegram_id=telegram_id,
                telegram_username=user.get("username"),
                name=" ".join(filter(None, [user.get("first_name"), user.get("last_name")])).strip() or "Telegram user",
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email="",
                phone="",
                country="",
                status="draft",
            )
            session.add(application)
            session.flush()
            session.add(AgentApplicationHistory(
                application_id=application.id,
                actor_telegram_id=telegram_id,
                previous_status=None,
                new_status="draft",
            ))
        if application.status not in {"draft", "need_information"}:
            raise HTTPException(409, "Сейчас анкету изменить нельзя.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(application, field, value.strip() if isinstance(value, str) else value)
        if payload.first_name is not None or payload.last_name is not None:
            application.name = " ".join(filter(None, [application.first_name, application.last_name])).strip()
        if not application.telegram_username:
            application.telegram_username = user.get("username")
        if application.email and not application.account_identifier:
            application.account_identifier = application.email
        if application.country:
            setting = session.scalar(select(GeoAgentSetting).where(GeoAgentSetting.country.ilike(application.country)))
            application.geo_code = setting.geo_code if setting else None
        application.updated_at = datetime.utcnow()
        _audit(session, application.id, telegram_id, "draft_saved")
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def mark_deposit(user: dict) -> dict:
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        can_correct = application and application.status == "need_information" and application.resume_state == "waiting_deposit"
        if not application or (application.status != "waiting_deposit" and not can_correct):
            raise HTTPException(409, "Этот этап пока недоступен.")
        flags = _document_flags(session, application.id)
        if not flags["deposit"]:
            raise HTTPException(422, "Сначала загрузите подтверждение депозита.")
        application.deposit_submitted_at = datetime.utcnow()
        if can_correct:
            _set_status(session, application, "waiting_deposit", int(user["id"]), "Подтверждение депозита обновлено")
            application.resume_state = None
        application.updated_at = datetime.utcnow()
        _audit(session, application.id, int(user["id"]), "deposit_submitted")
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def submit_profile(user: dict, confirmed_truth: bool = False) -> dict:
    required = ["first_name", "last_name", "phone", "email", "country", "city", "telegram_username", "location", "source"]
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        if not application or application.status not in {"draft", "need_information", "waiting_documents"}:
            raise HTTPException(409, "Анкета пока недоступна.")
        identity_stage = application.status == "waiting_documents" or (
            application.status == "need_information" and application.resume_state in {"waiting_documents", "final_review"}
        )
        if identity_stage:
            flags = _document_flags(session, application.id)
            if not flags["passport"] or not flags["selfie"]:
                raise HTTPException(422, "Загрузите фото документа и селфи с документом.")
            application.documents_submitted_at = datetime.utcnow()
            _set_status(session, application, "final_review", int(user["id"]), "Документы отправлены")
        else:
            missing = [field for field in required if not str(getattr(application, field, "") or "").strip()]
            if application.source == "other" and not (application.source_other or "").strip():
                missing.append("source_other")
            if application.source == "agent" and not (application.referral_agent or "").strip():
                missing.append("referral_agent")
            if missing:
                raise HTTPException(422, "Заполните обязательные поля.")
            if not confirmed_truth:
                raise HTTPException(422, "Подтвердите достоверность данных.")
            target_status = "under_review" if application.status == "need_information" else "submitted"
            _set_status(session, application, target_status, int(user["id"]), "Заявка отправлена")
            application.submitted_at = datetime.utcnow()
        application.manager_comment = None
        application.resume_state = None
        application.updated_at = datetime.utcnow()
        _audit(session, application.id, int(user["id"]), "application_submitted")
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def save_document(user: dict, kind: str, filename: str, mime_type: str, data: bytes) -> dict:
    if kind not in DOCUMENT_KINDS:
        raise HTTPException(404, "Неизвестный тип документа.")
    if mime_type not in IMAGE_TYPES:
        raise HTTPException(415, "Загрузите JPG, PNG или WEBP.")
    if not data or len(data) > MAX_DOCUMENT_BYTES:
        raise HTTPException(413, "Файл должен быть не больше 8 МБ.")
    if not _valid_image(data, mime_type):
        raise HTTPException(415, "Файл повреждён или имеет неверный формат.")
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        if not application:
            raise HTTPException(404, "Регистрация не найдена.")
        deposit_correction = kind == "deposit" and application.status == "need_information" and application.resume_state == "waiting_deposit"
        identity_correction = kind != "deposit" and application.status == "need_information" and application.resume_state in {"waiting_documents", "final_review"}
        allowed = {"waiting_deposit"} if kind == "deposit" else {"waiting_documents"}
        if application.status not in allowed and not deposit_correction and not identity_correction:
            raise HTTPException(409, "На этом этапе загрузка недоступна.")
        document = session.scalar(select(AgentDocument).where(AgentDocument.application_id == application.id, AgentDocument.kind == kind))
        if document is None:
            document = AgentDocument(application_id=application.id, kind=kind)
            session.add(document)
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", (filename or f"{kind}.jpg").split("/")[-1].split("\\")[-1])
        document.filename = safe_name[:255]
        document.mime_type = mime_type
        document.size = len(data)
        document.data = data
        document.uploaded_at = datetime.utcnow()
        document.expires_at = datetime.utcnow() + timedelta(days=int(os.getenv("DOCUMENT_RETENTION_DAYS", "365")))
        application.updated_at = datetime.utcnow()
        _audit(session, application.id, int(user["id"]), f"{kind}_uploaded")
        session.commit()
        return {"kind": kind, "uploaded": True, "size": len(data)}


def load_document(user: dict, kind: str, application_id: int | None = None) -> tuple[bytes, str, str]:
    if kind not in DOCUMENT_KINDS:
        raise HTTPException(404, "Документ не найден.")
    with Session(engine) as session:
        if application_id is None:
            application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        else:
            manager_user(user)
            application = session.get(AgentApplication, application_id)
        if not application:
            raise HTTPException(404, "Документ не найден.")
        document = session.scalar(select(AgentDocument).where(AgentDocument.application_id == application.id, AgentDocument.kind == kind))
        if not document:
            raise HTTPException(404, "Документ не найден.")
        if application_id is not None:
            _audit(session, application.id, int(user["id"]), f"{kind}_viewed")
            session.commit()
        return document.data, document.mime_type, document.filename


def remove_document(user: dict, kind: str) -> dict:
    if kind not in DOCUMENT_KINDS:
        raise HTTPException(404, "Документ не найден.")
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        correction = application and application.status == "need_information" and application.resume_state in {"waiting_deposit", "waiting_documents", "final_review"}
        if not application or (application.status not in {"waiting_deposit", "waiting_documents"} and not correction):
            raise HTTPException(409, "Документ сейчас нельзя удалить.")
        session.execute(delete(AgentDocument).where(AgentDocument.application_id == application.id, AgentDocument.kind == kind))
        _audit(session, application.id, int(user["id"]), f"{kind}_deleted")
        session.commit()
        return {"kind": kind, "uploaded": False}


def manager_applications(user: dict) -> list[dict]:
    manager_user(user)
    with Session(engine) as session:
        applications = session.scalars(select(AgentApplication).order_by(AgentApplication.updated_at.desc(), AgentApplication.id.desc())).all()
        return [application_payload(application, session) for application in applications]


def delete_manager_application(user: dict, application_id: int, payload: DeleteApplicationIn) -> dict:
    """Remove an unneeded application while retaining a non-sensitive audit record."""
    manager_user(user)
    actor_id = int(user["id"])
    with Session(engine) as session:
        application = session.get(AgentApplication, application_id)
        if not application:
            raise HTTPException(404, "Заявка не найдена.")
        if application.status == "approved":
            raise HTTPException(409, "Подтверждённого агента удалить нельзя.")
        application_number = f"PA-{application.id:06d}"
        reason = payload.reason.strip()
        snapshot = json.dumps({
            "name": application.name,
            "telegram_username": application.telegram_username,
            "country": application.country,
            "city": application.city,
            "created_at": application.created_at.isoformat() if application.created_at else None,
            "updated_at": application.updated_at.isoformat() if application.updated_at else None,
        }, ensure_ascii=False)
        session.add(DeletedApplicationAudit(
            application_id=application.id,
            application_number=application_number,
            applicant_telegram_id=application.telegram_id,
            actor_telegram_id=actor_id,
            status=application.status,
            reason=reason,
            details=snapshot,
        ))
        session.execute(delete(AgentDocument).where(AgentDocument.application_id == application.id))
        session.execute(delete(AgentApplicationHistory).where(AgentApplicationHistory.application_id == application.id))
        session.execute(delete(ApplicationAuditLog).where(ApplicationAuditLog.application_id == application.id))
        session.delete(application)
        session.commit()
        return {
            "deleted": True,
            "application_id": application_id,
            "application_number": application_number,
        }


def manager_application_action(user: dict, application_id: int, payload: ManagerActionIn) -> dict:
    manager_user(user)
    actor_id = int(user["id"])
    with Session(engine) as session:
        application = session.get(AgentApplication, application_id)
        if not application:
            raise HTTPException(404, "Заявка не найдена.")
        previous = application.status
        action = payload.action
        comment = (payload.comment or "").strip() or None
        if action == "approve":
            compatibility = {
                "submitted": "under_review",
                "under_review": "pre_approved",
                "pre_approved": "waiting_deposit",
                "final_review": "approved",
            }
            if previous not in compatibility:
                raise HTTPException(409, "Для этого этапа выберите специальное действие.")
            target = compatibility[previous]
            if target == "approved" and not application.documents_verified_at:
                raise HTTPException(409, "Сначала подтвердите документы.")
            _set_status(session, application, target, actor_id, comment)
        elif action == "start_review":
            if previous != "submitted":
                raise HTTPException(409, "Заявка уже находится на другом этапе.")
            _set_status(session, application, "under_review", actor_id, comment)
        elif action == "pre_approve":
            if previous not in {"submitted", "under_review"}:
                raise HTTPException(409, "Сначала начните проверку заявки.")
            _set_status(session, application, "pre_approved", actor_id, comment)
        elif action == "open_deposit":
            if previous != "pre_approved":
                raise HTTPException(409, "Сначала предварительно одобрите заявку.")
            _set_status(session, application, "waiting_deposit", actor_id, comment)
        elif action == "confirm_deposit":
            if previous != "waiting_deposit" or not application.deposit_submitted_at:
                raise HTTPException(409, "Пользователь ещё не отправил подтверждение депозита.")
            _set_status(session, application, "waiting_documents", actor_id, comment)
        elif action == "confirm_documents":
            if previous != "final_review" or not application.documents_submitted_at:
                raise HTTPException(409, "Пользователь ещё не отправил документы.")
            application.documents_verified_at = datetime.utcnow()
        elif action == "activate":
            if previous != "final_review" or not application.documents_verified_at:
                raise HTTPException(409, "Сначала подтвердите документы.")
            _set_status(session, application, "approved", actor_id, comment)
            application.agent_id = application.agent_id or f"PA-{application.id:06d}"
            application.assigned_manager_id = application.assigned_manager_id or actor_id
            application.activated_at = datetime.utcnow()
            application.approved_at = application.activated_at
        elif action in {"changes", "request_information"}:
            if previous not in {"submitted", "under_review", "pre_approved", "waiting_deposit", "waiting_documents", "final_review"}:
                raise HTTPException(409, "Дополнительную информацию сейчас запросить нельзя.")
            application.resume_state = previous
            _set_status(session, application, "need_information", actor_id, comment)
        elif action == "reject":
            if previous in {"approved", "rejected"}:
                raise HTTPException(409, "Эту заявку сейчас нельзя отклонить.")
            application.resume_state = previous
            _set_status(session, application, "rejected", actor_id, comment)
        else:
            if not comment:
                raise HTTPException(422, "Введите комментарий.")
        if action not in {"comment", "confirm_documents"}:
            application.assigned_manager_id = application.assigned_manager_id or actor_id
        application.manager_comment = comment
        application.updated_at = datetime.utcnow()
        _audit(session, application.id, actor_id, f"manager_{action}", json.dumps({"from": previous, "to": application.status}, ensure_ascii=False))
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def submit_application(user: dict, payload: ApplicationIn) -> dict:
    """Compatibility endpoint for clients still using the previous form."""
    result = start_account(user, AccountStartIn(account_identifier=str(payload.email), phone=payload.phone, email=payload.email))
    with Session(engine) as session:
        application = session.get(AgentApplication, result["id"])
        application.name = payload.name
        application.country = payload.country
        application.experience = payload.experience
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def submit_ticket(user: dict, payload: TicketIn) -> dict:
    with Session(engine) as session:
        ticket = SupportTicket(telegram_id=int(user["id"]), **payload.model_dump())
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        return {"id": ticket.id, "status": ticket.status, "created_at": ticket.created_at.isoformat()}


def check_contact(payload: ContactCheckIn, blocked_only: bool = False) -> dict:
    query = payload.query.strip().lower().lstrip("@")
    with Session(engine) as session:
        clauses = [
            AgentApplication.email.ilike(query),
            AgentApplication.phone.ilike(query),
            AgentApplication.telegram_username.ilike(query),
        ]
        if query.isdigit():
            clauses.append(AgentApplication.telegram_id == int(query))
        application = session.scalar(select(AgentApplication).where(or_(*clauses)))
        if blocked_only:
            return {"blocked": bool(application and application.status == "blocked")}
        verified = bool(application and application.status == "approved" and application.agent_id)
        public_profile = None
        if verified:
            public_profile = {
                "name": application.name,
                "agent_id": application.agent_id,
                "country": application.country,
                "city": application.city,
                "status": "verified",
                "connected_at": (application.activated_at or application.approved_at or application.created_at).isoformat(),
            }
        return {"registered": bool(application), "verified": verified, "agent": public_profile}


def check_manager(payload: ContactCheckIn) -> dict:
    query = payload.query.strip().lower().lstrip("@")
    verified = (query.isdigit() and is_manager_id(query)) or bool(SUPPORT_USERNAME and query == SUPPORT_USERNAME)
    if not verified and query:
        with Session(engine) as session:
            profile = session.scalar(select(TelegramUser).where(TelegramUser.username.ilike(query)))
            verified = bool(profile and is_manager_id(profile.telegram_id))
    return {"verified": verified}
