import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import storage, webapi
from app.storage import Base, ManagerAccess, ManagerAccessAudit, TelegramUser


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr(storage, "engine", test_engine)
    monkeypatch.setattr(webapi, "engine", test_engine)
    monkeypatch.setattr(webapi, "MANAGER_IDS", {"900"})
    monkeypatch.setattr(webapi, "MANAGER_ID_LIST", ["900"])
    monkeypatch.setattr(webapi, "SUPERADMIN_IDS", {"900"})
    yield test_engine


def user(user_id=101):
    return {"id": user_id, "username": f"user{user_id}", "first_name": "Test", "last_name": "Agent", "language_code": "ru"}


def signed_init_data(payload):
    data = {"auth_date": str(int(time.time())), "user": json.dumps(payload, separators=(",", ":"))}
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", webapi.TOKEN.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


PNG = b"\x89PNG\r\n\x1a\n" + b"test-image"
JPEG = b"\xff\xd8\xff" + b"test-image"


def test_verified_telegram_user_is_saved(isolated_database):
    current = webapi.current_user(signed_init_data(user()))
    assert current["id"] == 101
    with Session(isolated_database) as session:
        stored = session.scalar(select(TelegramUser).where(TelegramUser.telegram_id == 101))
        assert stored.username == "user101"
        assert stored.language_code == "ru"


def test_complete_agent_flow_and_resume():
    applicant, manager = user(), user(900)
    application = webapi.start_account(applicant, webapi.AccountStartIn(
        account_identifier="agent@example.com", phone="+7 999 123-45-67", email="agent@example.com"
    ))
    assert application["status"] == "account_review"
    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="approve"))
    assert application["status"] == "account_approved"
    webapi.save_document(applicant, "deposit", "deposit.png", "image/png", PNG)
    application = webapi.mark_deposit(applicant)
    assert application["status"] == "deposit_review"
    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="approve"))
    assert application["status"] == "profile_form"

    application = webapi.save_application_draft(applicant, webapi.ApplicationDraftIn(
        name="Test Agent", phone="+7 999 123-45-67", email="agent@example.com",
        country="Kyrgyzstan", city="Bishkek", cashdesk_name="Agent Cash",
        location="Center", source="telegram", experience="Payments",
    ))
    assert application["city"] == "Bishkek"
    webapi.save_document(applicant, "passport", "passport.jpg", "image/jpeg", JPEG)
    webapi.save_document(applicant, "selfie", "selfie.jpg", "image/jpeg", JPEG)
    application = webapi.submit_profile(applicant)
    assert application["status"] == "application_review"

    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="changes", comment="Уточните район"))
    assert application["status"] == "changes_requested"
    assert application["manager_comment"] == "Уточните район"
    webapi.save_application_draft(applicant, webapi.ApplicationDraftIn(location="Central district"))
    application = webapi.submit_profile(applicant)
    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="approve"))
    assert application["status"] == "approved"
    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="activate"))
    assert application["status"] == "active_agent"
    assert webapi.profile_payload(applicant)["application"]["location"] == "Central district"


def test_validation_and_required_documents():
    with pytest.raises(ValidationError):
        webapi.AccountStartIn(account_identifier="abc", phone="wrong", email=None)
    with pytest.raises(ValidationError):
        webapi.AccountStartIn(account_identifier="abc", phone=None, email=None)

    applicant, manager = user(), user(900)
    application = webapi.start_account(applicant, webapi.AccountStartIn(account_identifier="agent@example.com", email="agent@example.com"))
    webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="approve"))
    webapi.mark_deposit(applicant)
    webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="approve"))
    webapi.save_application_draft(applicant, webapi.ApplicationDraftIn(
        name="Test Agent", phone="+996 700 123456", email="agent@example.com", country="KG",
        city="Bishkek", cashdesk_name="Cash", location="Center", source="telegram",
    ))
    with pytest.raises(HTTPException) as error:
        webapi.submit_profile(applicant)
    assert error.value.status_code == 422


def test_only_manager_can_open_another_users_document():
    applicant, manager = user(), user(900)
    application = webapi.start_account(applicant, webapi.AccountStartIn(account_identifier="agent@example.com", email="agent@example.com"))
    webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="approve"))
    webapi.save_document(applicant, "deposit", "proof.png", "image/png", PNG)
    with pytest.raises(HTTPException) as error:
        webapi.load_document(user(777), "deposit", application["id"])
    assert error.value.status_code == 403
    data, mime, _ = webapi.load_document(manager, "deposit", application["id"])
    assert data == PNG
    assert mime == "image/png"


def test_only_owner_can_manage_manager_access(isolated_database):
    owner = user(900)
    new_manager = user(901)

    granted = webapi.grant_manager_access(owner, webapi.ManagerAccessIn(telegram_id=901))
    assert granted == {"telegram_id": 901, "active": True}
    assert webapi.is_manager_id(901) is True

    with pytest.raises(HTTPException) as error:
        webapi.grant_manager_access(new_manager, webapi.ManagerAccessIn(telegram_id=902))
    assert error.value.status_code == 403

    managers = webapi.list_manager_access(owner)
    assert any(item["telegram_id"] == 901 and item["active"] for item in managers)

    revoked = webapi.revoke_manager_access(owner, 901)
    assert revoked == {"telegram_id": 901, "active": False}
    assert webapi.is_manager_id(901) is False

    with Session(isolated_database) as session:
        access = session.scalar(select(ManagerAccess).where(ManagerAccess.telegram_id == 901))
        audit = session.scalars(select(ManagerAccessAudit).where(ManagerAccessAudit.target_telegram_id == 901)).all()
        assert access.active is False
        assert [item.action for item in audit] == ["granted", "revoked"]


def test_legacy_database_gets_new_columns(monkeypatch, tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with legacy_engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE agent_applications (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER NOT NULL UNIQUE,
                name VARCHAR(160) NOT NULL,
                email VARCHAR(254) NOT NULL,
                country VARCHAR(100) NOT NULL,
                phone VARCHAR(64) NOT NULL,
                experience TEXT,
                status VARCHAR(32),
                created_at TIMESTAMP
            )
        """))
    monkeypatch.setattr(storage, "engine", legacy_engine)
    storage.init_storage()
    columns = {column["name"] for column in inspect(legacy_engine).get_columns("agent_applications")}
    assert {"updated_at", "account_identifier", "cashdesk_name", "source"}.issubset(columns)
    assert inspect(legacy_engine).has_table("telegram_users")
    assert inspect(legacy_engine).has_table("agent_documents")
