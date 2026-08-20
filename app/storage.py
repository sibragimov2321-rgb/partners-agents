import os
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./partners-agent.db")
    url = url.replace("postgres://", "postgresql://", 1)
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


engine = create_engine(database_url(), pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class TelegramUser(Base):
    __tablename__ = "telegram_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(800), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentApplication(Base):
    __tablename__ = "agent_applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254))
    country: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(64))
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="reviewing")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_identifier: Mapped[str | None] = mapped_column(String(160), nullable=True)
    manager_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cashdesk_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_other: Mapped[str | None] = mapped_column(String(300), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentDocument(Base):
    __tablename__ = "agent_documents"
    __table_args__ = (UniqueConstraint("application_id", "kind", name="uq_agent_document_kind"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("agent_applications.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ApplicationAuditLog(Base):
    __tablename__ = "application_audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("agent_applications.id", ondelete="CASCADE"), index=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(80))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    subject: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def init_storage() -> None:
    Base.metadata.create_all(engine)
    # create_all does not add columns to an existing Railway table. These
    # nullable additions keep legacy applications intact during deployment.
    existing = {column["name"] for column in inspect(engine).get_columns("agent_applications")}
    document_columns = {column["name"] for column in inspect(engine).get_columns("agent_documents")}
    additions = {
        "updated_at": "TIMESTAMP",
        "telegram_username": "VARCHAR(64)",
        "account_identifier": "VARCHAR(160)",
        "manager_comment": "TEXT",
        "resume_state": "VARCHAR(32)",
        "city": "VARCHAR(120)",
        "cashdesk_name": "VARCHAR(160)",
        "location": "VARCHAR(300)",
        "source": "VARCHAR(80)",
        "source_other": "VARCHAR(300)",
        "submitted_at": "TIMESTAMP",
        "approved_at": "TIMESTAMP",
    }
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE agent_applications ADD COLUMN {name} {sql_type}"))
        if "expires_at" not in document_columns:
            connection.execute(text("ALTER TABLE agent_documents ADD COLUMN expires_at TIMESTAMP"))
        if engine.dialect.name == "postgresql":
            connection.execute(text("ALTER TABLE agent_applications ALTER COLUMN telegram_id TYPE BIGINT"))
            connection.execute(text("ALTER TABLE support_tickets ALTER COLUMN telegram_id TYPE BIGINT"))
        connection.execute(text("DELETE FROM agent_documents WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"))


def save_telegram_user(user: dict) -> TelegramUser:
    """Persist a verified Telegram user and refresh mutable profile fields."""
    telegram_id = int(user["id"])
    with Session(engine) as session:
        stored = session.scalar(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id))
        if stored is None:
            stored = TelegramUser(telegram_id=telegram_id)
            session.add(stored)
        stored.username = user.get("username")
        stored.first_name = user.get("first_name")
        stored.last_name = user.get("last_name")
        stored.language_code = user.get("language_code")
        stored.photo_url = user.get("photo_url")
        stored.last_seen_at = datetime.utcnow()
        session.commit()
        session.refresh(stored)
        session.expunge(stored)
        return stored


def get_application(telegram_id: int) -> AgentApplication | None:
    with Session(engine) as session:
        return session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == telegram_id))
