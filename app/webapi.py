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
    AgentDocument,
    ApplicationAuditLog,
    SupportTicket,
    engine,
    save_telegram_user,
)

TOKEN = os.environ["BOT_TOKEN"]
MANAGER_IDS = {item.strip() for item in os.getenv("ADMIN_IDS", "").split(",") if item.strip()}
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


def manager_user(user: dict) -> dict:
    if str(user.get("id")) not in MANAGER_IDS:
        raise HTTPException(403, "Недостаточно прав.")
    return user


def _audit(session: Session, application_id: int, actor_id: int, action: str, details: str | None = None) -> None:
    session.add(ApplicationAuditLog(
        application_id=application_id,
        actor_telegram_id=actor_id,
        action=action,
        details=details[:2000] if details else None,
    ))


def _document_flags(session: Session, application_id: int) -> dict[str, bool]:
    kinds = session.scalars(select(AgentDocument.kind).where(AgentDocument.application_id == application_id)).all()
    return {kind: kind in kinds for kind in DOCUMENT_KINDS}


def application_payload(application: AgentApplication, session: Session) -> dict:
    return {
        "id": application.id,
        "telegram_id": application.telegram_id,
        "telegram_username": application.telegram_username,
        "status": application.status,
        "account_identifier": application.account_identifier,
        "manager_comment": application.manager_comment,
        "resume_state": application.resume_state,
        "name": application.name,
        "email": application.email,
        "phone": application.phone,
        "country": application.country,
        "city": application.city,
        "cashdesk_name": application.cashdesk_name,
        "location": application.location,
        "experience": application.experience,
        "source": application.source,
        "source_other": application.source_other,
        "documents": _document_flags(session, application.id),
        "created_at": application.created_at.isoformat() if application.created_at else None,
        "updated_at": application.updated_at.isoformat() if application.updated_at else None,
        "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
        "approved_at": application.approved_at.isoformat() if application.approved_at else None,
    }


def profile_payload(user: dict) -> dict:
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        return {
            "telegram": user,
            "is_manager": str(user["id"]) in MANAGER_IDS,
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
    name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=120)
    cashdesk_name: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=300)
    experience: str | None = Field(default=None, max_length=3000)
    source: str | None = Field(default=None, max_length=80)
    source_other: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_phone(self):
        if self.phone:
            self.phone = self.phone.strip()
            if not PHONE_RE.fullmatch(self.phone):
                raise ValueError("Проверьте формат телефона.")
        return self


class ApplicationIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    country: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=5, max_length=64)
    experience: str | None = Field(default=None, max_length=3000)


class ManagerActionIn(BaseModel):
    action: Literal["approve", "changes", "reject", "activate", "comment"]
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def reason_required(self):
        if self.action in {"changes", "reject"} and not (self.comment or "").strip():
            raise ValueError("Для этого действия нужен комментарий.")
        return self


class TicketIn(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    body: str = Field(min_length=2, max_length=5000)


class ContactCheckIn(BaseModel):
    query: str = Field(min_length=2, max_length=254)


def start_account(user: dict, payload: AccountStartIn) -> dict:
    telegram_id = int(user["id"])
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == telegram_id))
        can_correct_account = application and application.status == "changes_requested" and application.resume_state == "account_review"
        if application and application.status != "rejected" and not can_correct_account:
            raise HTTPException(409, "Регистрация уже начата.")
        full_name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")])).strip() or "Telegram user"
        if application is None:
            application = AgentApplication(
                telegram_id=telegram_id,
                telegram_username=user.get("username"),
                name=full_name,
                email=str(payload.email or ""),
                phone=payload.phone or "",
                country="",
                account_identifier=payload.account_identifier.strip(),
                status="account_review",
            )
            session.add(application)
            session.flush()
        else:
            application.telegram_username = user.get("username")
            application.account_identifier = payload.account_identifier.strip()
            application.phone = payload.phone or application.phone
            application.email = str(payload.email or application.email)
            application.status = "account_review"
            application.manager_comment = None
            application.updated_at = datetime.utcnow()
        _audit(session, application.id, telegram_id, "account_submitted")
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def save_application_draft(user: dict, payload: ApplicationDraftIn) -> dict:
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        if not application:
            raise HTTPException(404, "Регистрация не найдена.")
        if application.status not in {"profile_form", "changes_requested"}:
            raise HTTPException(409, "Сейчас анкету изменить нельзя.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(application, field, str(value).strip() if value is not None else None)
        application.updated_at = datetime.utcnow()
        _audit(session, application.id, int(user["id"]), "draft_saved")
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def mark_deposit(user: dict) -> dict:
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        can_correct = application and application.status == "changes_requested" and application.resume_state == "deposit_review"
        if not application or (application.status != "account_approved" and not can_correct):
            raise HTTPException(409, "Этот этап пока недоступен.")
        application.status = "deposit_review"
        application.updated_at = datetime.utcnow()
        _audit(session, application.id, int(user["id"]), "deposit_submitted")
        session.commit()
        session.refresh(application)
        return application_payload(application, session)


def submit_profile(user: dict) -> dict:
    required = ["name", "phone", "email", "country", "city", "cashdesk_name", "location", "source"]
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        if not application or application.status not in {"profile_form", "changes_requested"}:
            raise HTTPException(409, "Анкета пока недоступна.")
        missing = [field for field in required if not str(getattr(application, field, "") or "").strip()]
        flags = _document_flags(session, application.id)
        if not flags["passport"] or not flags["selfie"]:
            missing.append("documents")
        if application.source == "other" and not (application.source_other or "").strip():
            missing.append("source_other")
        if missing:
            raise HTTPException(422, "Заполните обязательные поля и загрузите документы.")
        application.status = "application_review"
        application.manager_comment = None
        application.resume_state = None
        application.submitted_at = datetime.utcnow()
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
        deposit_correction = kind == "deposit" and application.status == "changes_requested" and application.resume_state == "deposit_review"
        allowed = {"account_approved"} if kind == "deposit" else {"profile_form", "changes_requested"}
        if application.status not in allowed and not deposit_correction:
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
        if not application or application.status not in {"account_approved", "profile_form", "changes_requested"}:
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


def manager_application_action(user: dict, application_id: int, payload: ManagerActionIn) -> dict:
    manager_user(user)
    with Session(engine) as session:
        application = session.get(AgentApplication, application_id)
        if not application:
            raise HTTPException(404, "Заявка не найдена.")
        previous = application.status
        if payload.action == "approve":
            transitions = {"account_review": "account_approved", "deposit_review": "profile_form", "application_review": "approved", "reviewing": "approved"}
            if previous not in transitions:
                raise HTTPException(409, "Эту заявку сейчас нельзя одобрить.")
            application.status = transitions[previous]
            if application.status == "approved":
                application.approved_at = datetime.utcnow()
        elif payload.action == "activate":
            if previous != "approved":
                raise HTTPException(409, "Сначала одобрите заявку.")
            application.status = "active_agent"
        elif payload.action == "changes":
            if previous not in {"account_review", "deposit_review", "application_review"}:
                raise HTTPException(409, "Изменения сейчас запросить нельзя.")
            application.resume_state = previous
            application.status = "changes_requested"
        elif payload.action == "reject":
            if previous not in {"account_review", "deposit_review", "application_review", "reviewing", "changes_requested"}:
                raise HTTPException(409, "Эту заявку сейчас нельзя отклонить.")
            application.resume_state = previous
            application.status = "rejected"
        else:
            if not (payload.comment or "").strip():
                raise HTTPException(422, "Введите комментарий.")
        application.manager_comment = (payload.comment or "").strip() or None
        application.updated_at = datetime.utcnow()
        _audit(session, application.id, int(user["id"]), f"manager_{payload.action}", json.dumps({"from": previous, "to": application.status}, ensure_ascii=False))
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
        clauses = [AgentApplication.email.ilike(query), AgentApplication.telegram_username.ilike(query)]
        if query.isdigit():
            clauses.append(AgentApplication.telegram_id == int(query))
        application = session.scalar(select(AgentApplication).where(or_(*clauses)))
        if blocked_only:
            return {"blocked": bool(application and application.status == "blocked")}
        return {"registered": bool(application)}


def check_manager(payload: ContactCheckIn) -> dict:
    query = payload.query.strip().lower().lstrip("@")
    verified = query in MANAGER_IDS or bool(SUPPORT_USERNAME and query == SUPPORT_USERNAME)
    return {"verified": verified}
