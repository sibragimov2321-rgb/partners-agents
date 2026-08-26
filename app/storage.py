import os
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, create_engine, inspect, select, text
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
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
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
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geo_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    has_experience: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    planned_players: Mapped[str | None] = mapped_column(String(32), nullable=True)
    physical_point: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    referral_agent: Mapped[str | None] = mapped_column(String(160), nullable=True)
    assigned_manager_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True, index=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deposit_submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    documents_submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    documents_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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


class DeletedApplicationAudit(Base):
    """Minimal immutable record kept after a manager removes an application."""
    __tablename__ = "deleted_application_audits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(Integer, index=True)
    application_number: Mapped[str] = mapped_column(String(32), index=True)
    applicant_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(500))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentApplicationHistory(Base):
    __tablename__ = "agent_application_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("agent_applications.id", ondelete="CASCADE"), index=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GeoAgentSetting(Base):
    __tablename__ = "geo_agent_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    geo_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(100), unique=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    minimum_deposit: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ManagerAccess(Base):
    __tablename__ = "manager_access"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    granted_by: Mapped[int] = mapped_column(BigInteger, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ManagerAccessAudit(Base):
    __tablename__ = "manager_access_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    target_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(40))
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


class Giveaway(Base):
    """A manager-controlled giveaway. Existing program tables stay independent."""
    __tablename__ = "giveaways"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    prize: Mapped[str] = mapped_column(String(300))
    winner_count: Mapped[int] = mapped_column(Integer, default=1)
    entry_deadline: Mapped[datetime] = mapped_column(DateTime, index=True)
    draw_date: Mapped[datetime] = mapped_column(DateTime)
    # New scheduled giveaways use these explicit start/end values. The legacy
    # columns remain populated so existing rows and integrations keep working.
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    geo_codes: Mapped[str] = mapped_column(Text, default="[]")
    rules: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    banner_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner_mime_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    banner_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GiveawayParticipant(Base):
    __tablename__ = "giveaway_participants"
    __table_args__ = (
        UniqueConstraint("giveaway_id", "telegram_id", name="uq_giveaway_participant_telegram"),
        UniqueConstraint("giveaway_id", "player_id", name="uq_giveaway_participant_player"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    player_id: Mapped[str] = mapped_column(String(80))
    geo_code: Mapped[str] = mapped_column(String(16), index=True)
    participant_number: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    excluded_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    excluded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GiveawayWinner(Base):
    __tablename__ = "giveaway_winners"
    __table_args__ = (UniqueConstraint("giveaway_id", "participant_id", name="uq_giveaway_winner_participant"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("giveaway_participants.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    selected_by: Mapped[int] = mapped_column(BigInteger, index=True)
    selected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    replacement_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class GiveawayAuditLog(Base):
    __tablename__ = "giveaway_audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), index=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    participant_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class GiveawayBroadcast(Base):
    __tablename__ = "giveaway_broadcasts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int | None] = mapped_column(ForeignKey("giveaways.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    audience: Mapped[str] = mapped_column(String(40))
    geo_codes: Mapped[str] = mapped_column(Text, default="[]")
    message: Mapped[str] = mapped_column(Text)
    button_text: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def init_storage() -> None:
    Base.metadata.create_all(engine)
    # create_all does not add columns to an existing Railway table. These
    # nullable additions keep legacy applications intact during deployment.
    existing = {column["name"] for column in inspect(engine).get_columns("agent_applications")}
    document_columns = {column["name"] for column in inspect(engine).get_columns("agent_documents")}
    giveaway_columns = {column["name"] for column in inspect(engine).get_columns("giveaways")}
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
        "first_name": "VARCHAR(100)",
        "last_name": "VARCHAR(100)",
        "geo_code": "VARCHAR(16)",
        "has_experience": "BOOLEAN",
        "planned_players": "VARCHAR(32)",
        "physical_point": "BOOLEAN",
        "referral_agent": "VARCHAR(160)",
        "assigned_manager_id": "BIGINT",
        "agent_id": "VARCHAR(32)",
        "activated_at": "TIMESTAMP",
        "deposit_submitted_at": "TIMESTAMP",
        "documents_submitted_at": "TIMESTAMP",
        "documents_verified_at": "TIMESTAMP",
    }
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE agent_applications ADD COLUMN {name} {sql_type}"))
        for name, sql_type in {"start_at": "TIMESTAMP", "end_at": "TIMESTAMP"}.items():
            if name not in giveaway_columns:
                connection.execute(text(f"ALTER TABLE giveaways ADD COLUMN {name} {sql_type}"))
        if "expires_at" not in document_columns:
            connection.execute(text("ALTER TABLE agent_documents ADD COLUMN expires_at TIMESTAMP"))
        if engine.dialect.name == "postgresql":
            connection.execute(text("ALTER TABLE agent_applications ALTER COLUMN telegram_id TYPE BIGINT"))
            connection.execute(text("ALTER TABLE support_tickets ALTER COLUMN telegram_id TYPE BIGINT"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_agent_applications_agent_id ON agent_applications (agent_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_telegram_users_username ON telegram_users (username)"))
        connection.execute(text("DELETE FROM agent_documents WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"))

    defaults = [
        ("KG", "Кыргызстан", 50),
        ("UZ", "Узбекистан", 100),
        ("TM", "Туркменистан", 100),
        ("KZ", "Казахстан", 100),
        ("TJ", "Таджикистан", 100),
        ("AZ", "Азербайджан", 100),
        ("TR", "Турция", 100),
        ("RU", "Россия", 100),
    ]
    status_map = {
        "reviewing": "under_review",
        "account_review": "under_review",
        "account_approved": "waiting_deposit",
        "deposit_review": "waiting_deposit",
        "profile_form": "waiting_documents",
        "application_review": "final_review",
        "changes_requested": "need_information",
        "active_agent": "approved",
    }
    geo_by_country = {country: code for code, country, _ in defaults}
    with Session(engine) as session:
        for geo_code, country, minimum_deposit in defaults:
            existing_setting = session.scalar(select(GeoAgentSetting).where(GeoAgentSetting.geo_code == geo_code))
            if existing_setting is None:
                session.add(GeoAgentSetting(
                    geo_code=geo_code,
                    country=country,
                    currency="USD",
                    minimum_deposit=minimum_deposit,
                ))
        applications = session.scalars(select(AgentApplication)).all()
        for application in applications:
            legacy_status = application.status
            if legacy_status in status_map:
                application.status = status_map[legacy_status]
            if legacy_status == "deposit_review" and application.deposit_submitted_at is None:
                application.deposit_submitted_at = application.updated_at
            if legacy_status == "active_agent":
                application.activated_at = application.activated_at or application.approved_at or application.updated_at
                application.agent_id = application.agent_id or f"PA-{application.id:06d}"
            if not application.first_name and application.name:
                parts = application.name.strip().split(maxsplit=1)
                application.first_name = parts[0] if parts else None
                application.last_name = parts[1] if len(parts) > 1 else None
            application.geo_code = application.geo_code or geo_by_country.get(application.country)
        session.commit()


def save_telegram_user(user: dict) -> TelegramUser:
    """Persist a verified Telegram user and refresh mutable profile fields."""
    telegram_id = int(user["id"])
    with Session(engine) as session:
        username = (user.get("username") or "").strip().lstrip("@") or None
        if username:
            duplicates = session.scalars(select(TelegramUser).where(
                TelegramUser.username.ilike(username),
                TelegramUser.telegram_id != telegram_id,
            )).all()
            for duplicate in duplicates:
                duplicate.username = None
        stored = session.scalar(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id))
        if stored is None:
            stored = TelegramUser(telegram_id=telegram_id)
            session.add(stored)
        stored.username = username
        stored.first_name = user.get("first_name")
        stored.last_name = user.get("last_name")
        stored.language_code = user.get("language_code")
        if "photo_url" in user:
            stored.photo_url = user.get("photo_url")
        stored.last_seen_at = datetime.utcnow()
        session.commit()
        session.refresh(stored)
        session.expunge(stored)
        return stored


def get_application(telegram_id: int) -> AgentApplication | None:
    with Session(engine) as session:
        return session.scalar(select(AgentApplication).where(AgentApplication.telegram_id == telegram_id))
