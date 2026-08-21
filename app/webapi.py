import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timedelta
import time
from typing import Literal
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from .storage import (
    AgentApplication,
    AgentApplicationHistory,
    AgentDocument,
    ApplicationAuditLog,
    DeletedApplicationAudit,
    GeoAgentSetting,
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
        return {
            "telegram": user,
            "is_manager": is_manager_id(user["id"]),
            "is_superadmin": is_superadmin_id(user["id"]),
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
