import hashlib
import hmac
import json
from datetime import datetime
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .storage import AgentApplication, SupportTicket, engine, get_application
import os

TOKEN = os.environ["BOT_TOKEN"]
MANAGER_IDS = {item.strip() for item in os.getenv("ADMIN_IDS", "").split(",") if item.strip()}
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lower().lstrip("@")


def telegram_user(init_data: str | None) -> dict:
    if not init_data:
        raise HTTPException(401, "Open the application from Telegram.")
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", "")
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash) or "user" not in data:
        raise HTTPException(401, "Telegram authorization could not be verified.")
    return json.loads(data["user"])


def current_user(x_telegram_init_data: str | None = Header(default=None)) -> dict:
    return telegram_user(x_telegram_init_data)


def profile_payload(user: dict) -> dict:
    app = get_application(int(user["id"]))
    return {"telegram": user, "application": None if not app else {"id": app.id, "status": app.status, "name": app.name, "created_at": app.created_at.isoformat()}}


class ApplicationIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    country: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=5, max_length=64)
    experience: str | None = Field(default=None, max_length=3000)


class TicketIn(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    body: str = Field(min_length=2, max_length=5000)


class ContactCheckIn(BaseModel):
    query: str = Field(min_length=2, max_length=254)


def submit_application(user: dict, payload: ApplicationIn) -> dict:
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(user["id"])))
        if application:
            raise HTTPException(409, "An application already exists.")
        application = AgentApplication(telegram_id=int(user["id"]), **payload.model_dump())
        session.add(application); session.commit(); session.refresh(application)
        return {"id": application.id, "status": application.status, "created_at": application.created_at.isoformat()}


def submit_ticket(user: dict, payload: TicketIn) -> dict:
    with Session(engine) as session:
        ticket = SupportTicket(telegram_id=int(user["id"]), **payload.model_dump())
        session.add(ticket); session.commit(); session.refresh(ticket)
        return {"id": ticket.id, "status": ticket.status, "created_at": ticket.created_at.isoformat()}


def check_contact(payload: ContactCheckIn, blocked_only: bool = False) -> dict:
    query = payload.query.strip().lower().lstrip("@")
    with Session(engine) as session:
        application = session.scalar(select(AgentApplication).where(AgentApplication.email.ilike(query)))
        if not application and query.isdigit():
            application = session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == int(query)))
        if blocked_only:
            return {"blocked": bool(application and application.status == "blocked")}
        return {"registered": bool(application)}


def check_manager(payload: ContactCheckIn) -> dict:
    """Verify only managers explicitly configured by the project owner."""
    query = payload.query.strip().lower().lstrip("@")
    verified = query in MANAGER_IDS or bool(SUPPORT_USERNAME and query == SUPPORT_USERNAME)
    return {"verified": verified}
