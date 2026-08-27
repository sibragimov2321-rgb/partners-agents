import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Unit tests never use a production secret, but webapi requires the variable at
# import time in exactly the same way as the deployed application.
os.environ.setdefault("BOT_TOKEN", "123456:test-token")

from app import storage, webapi
from app.storage import (
    AgentApplicationHistory,
    Base,
    DeletedApplicationAudit,
    GeoAgentSetting,
    ManagerAccess,
    ManagerAccessAudit,
    TelegramUser,
)


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(storage, "engine", test_engine)
    monkeypatch.setattr(webapi, "engine", test_engine)
    monkeypatch.setattr(webapi, "MANAGER_IDS", {"900"})
    monkeypatch.setattr(webapi, "MANAGER_ID_LIST", ["900"])
    monkeypatch.setattr(webapi, "SUPERADMIN_IDS", {"900"})
    storage.init_storage()
    yield test_engine


def user(user_id=101):
    return {"id": user_id, "username": f"user{user_id}", "first_name": "Test", "last_name": "Agent", "language_code": "ru"}


def signed_init_data(payload):
    data = {"auth_date": str(int(time.time())), "user": json.dumps(payload, separators=(",", ":"))}
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", webapi.TOKEN.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def create_draft(applicant=None):
    applicant = applicant or user()
    return webapi.save_application_draft(applicant, webapi.ApplicationDraftIn(
        first_name="Test",
        last_name="Agent",
        phone="+996 700 123456",
        telegram_username="test_agent",
        email="agent@example.com",
        country="Кыргызстан",
        city="Бишкек",
        has_experience=True,
        experience="Работа с платежами",
        planned_players="10_30",
        cashdesk_name="Agent Cash",
        location="Центральный район",
        physical_point=True,
        source="telegram",
    ))


PNG = b"\x89PNG\r\n\x1a\n" + b"test-image"
JPEG = b"\xff\xd8\xff" + b"test-image"


def test_verified_telegram_user_is_saved(isolated_database):
    current = webapi.current_user(signed_init_data(user()))
    assert current["id"] == 101
    with Session(isolated_database) as session:
        stored = session.scalar(select(TelegramUser).where(TelegramUser.telegram_id == 101))
        assert stored.username == "user101"
        assert stored.language_code == "ru"


def test_manager_can_delete_unneeded_application_and_user_can_reapply(isolated_database):
    applicant, manager = user(111), user(900)
    application = create_draft(applicant)

    with pytest.raises(HTTPException) as denied:
        webapi.delete_manager_application(applicant, application["id"], webapi.DeleteApplicationIn(reason="Тестовая заявка"))
    assert denied.value.status_code == 403

    result = webapi.delete_manager_application(manager, application["id"], webapi.DeleteApplicationIn(reason="Тестовая заявка"))
    assert result["deleted"] is True
    assert webapi.manager_applications(manager) == []
    with Session(isolated_database) as session:
        audit = session.scalar(select(DeletedApplicationAudit).where(
            DeletedApplicationAudit.application_id == application["id"],
        ))
        assert audit.reason == "Тестовая заявка"
        assert audit.actor_telegram_id == 900

    replacement = create_draft(applicant)
    assert replacement["telegram_id"] == applicant["id"]
    assert len(webapi.manager_applications(manager)) == 1


def test_confirmed_agent_cannot_be_deleted(isolated_database):
    application = create_draft(user(112))
    with Session(isolated_database) as session:
        stored = session.get(storage.AgentApplication, application["id"])
        stored.status = "approved"
        session.commit()
    with pytest.raises(HTTPException) as blocked:
        webapi.delete_manager_application(user(900), application["id"], webapi.DeleteApplicationIn(reason="Не нужна"))
    assert blocked.value.status_code == 409


def test_complete_agent_flow_and_resume(isolated_database):
    applicant, manager = user(), user(900)
    application = create_draft(applicant)
    assert application["status"] == "draft"
    assert application["geo_code"] == "KG"
    assert application["geo_setting"]["minimum_deposit"] == 50

    application = webapi.submit_profile(applicant, confirmed_truth=True)
    assert application["status"] == "submitted"
    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="start_review"))
    assert application["status"] == "under_review"

    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(
        action="request_information", comment="Уточните район",
    ))
    assert application["status"] == "need_information"
    assert application["manager_comment"] == "Уточните район"
    webapi.save_application_draft(applicant, webapi.ApplicationDraftIn(location="Новый центральный район"))
    application = webapi.submit_profile(applicant, confirmed_truth=True)
    assert application["status"] == "under_review"

    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="pre_approve"))
    assert application["status"] == "pre_approved"
    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="open_deposit"))
    assert application["status"] == "waiting_deposit"

    with pytest.raises(HTTPException) as error:
        webapi.mark_deposit(applicant)
    assert error.value.status_code == 422
    webapi.save_document(applicant, "deposit", "deposit.png", "image/png", PNG)
    application = webapi.mark_deposit(applicant)
    assert application["status"] == "waiting_deposit"
    assert application["deposit_submitted_at"] is not None
    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="confirm_deposit"))
    assert application["status"] == "waiting_documents"

    webapi.save_document(applicant, "passport", "passport.jpg", "image/jpeg", JPEG)
    webapi.save_document(applicant, "selfie", "selfie.jpg", "image/jpeg", JPEG)
    application = webapi.submit_profile(applicant, confirmed_truth=True)
    assert application["status"] == "final_review"
    with pytest.raises(HTTPException) as error:
        webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="activate"))
    assert error.value.status_code == 409

    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="confirm_documents"))
    assert application["documents_verified_at"] is not None
    application = webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="activate"))
    assert application["status"] == "approved"
    assert application["agent_id"].startswith("PA-")
    assert application["assigned_manager_id"] == 900
    assert application["activated_at"] is not None

    verification = webapi.check_contact(webapi.ContactCheckIn(query="agent@example.com"))
    assert verification["verified"] is True
    assert verification["agent"]["agent_id"] == application["agent_id"]
    assert verification["agent"]["country"] == "Кыргызстан"
    assert verification["agent"]["cashdesk_name"] == "Agent Cash"
    assert "name" not in verification["agent"]
    assert "email" not in verification["agent"]
    assert "phone" not in verification["agent"]

    with Session(isolated_database) as session:
        history = session.scalars(select(AgentApplicationHistory).where(
            AgentApplicationHistory.application_id == application["id"],
        ).order_by(AgentApplicationHistory.id)).all()
        assert history[0].new_status == "draft"
        assert history[-1].new_status == "approved"
        assert any(item.new_status == "need_information" and item.comment == "Уточните район" for item in history)


def test_validation_and_stage_gated_documents():
    with pytest.raises(ValidationError):
        webapi.ApplicationDraftIn(phone="wrong")
    with pytest.raises(ValidationError):
        webapi.ApplicationDraftIn(telegram_username="bad name")

    applicant = user()
    partial = webapi.save_application_draft(applicant, webapi.ApplicationDraftIn(first_name="Test", last_name="Agent"))
    with pytest.raises(HTTPException) as error:
        webapi.submit_profile(applicant, confirmed_truth=True)
    assert error.value.status_code == 422
    with pytest.raises(HTTPException) as error:
        webapi.save_document(applicant, "passport", "passport.jpg", "image/jpeg", JPEG)
    assert error.value.status_code == 409
    assert partial["documents"]["passport"] is False


def test_only_manager_can_open_another_users_document():
    applicant, manager = user(), user(900)
    application = create_draft(applicant)
    application = webapi.submit_profile(applicant, confirmed_truth=True)
    webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="start_review"))
    webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="pre_approve"))
    webapi.manager_application_action(manager, application["id"], webapi.ManagerActionIn(action="open_deposit"))
    webapi.save_document(applicant, "deposit", "proof.png", "image/png", PNG)
    with pytest.raises(HTTPException) as error:
        webapi.load_document(user(777), "deposit", application["id"])
    assert error.value.status_code == 403
    data, mime, _ = webapi.load_document(manager, "deposit", application["id"])
    assert data == PNG
    assert mime == "image/png"


def test_geo_settings_are_database_driven(isolated_database):
    owner = user(900)
    public = webapi.list_geo_settings(user())
    assert any(item["geo_code"] == "KG" and item["minimum_deposit"] == 50 for item in public)
    updated = webapi.update_geo_setting(owner, "KG", webapi.GeoSettingIn(
        country="Кыргызстан", currency="USD", minimum_deposit=75, active=True,
    ))
    assert updated["minimum_deposit"] == 75
    with Session(isolated_database) as session:
        setting = session.scalar(select(GeoAgentSetting).where(GeoAgentSetting.geo_code == "KG"))
        assert setting.minimum_deposit == 75
    with pytest.raises(HTTPException) as error:
        webapi.update_geo_setting(user(777), "KG", webapi.GeoSettingIn(
            country="Кыргызстан", currency="USD", minimum_deposit=10,
        ))
    assert error.value.status_code == 403


def test_only_owner_can_manage_manager_access(isolated_database):
    owner = user(900)
    new_manager = user(901)
    granted = webapi.grant_manager_access(owner, webapi.ManagerAccessIn(telegram_id=901))
    assert granted == {"telegram_id": 901, "username": None, "active": True}
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


def test_owner_can_add_manager_by_saved_username():
    owner = user(900)
    candidate = user(902)
    storage.save_telegram_user(candidate)

    granted = webapi.grant_manager_access(owner, webapi.ManagerAccessIn(username="@user902"))
    assert granted == {"telegram_id": 902, "username": "user902", "active": True}
    assert webapi.is_manager_id(902) is True

    with pytest.raises(HTTPException) as error:
        webapi.grant_manager_access(owner, webapi.ManagerAccessIn(username="@unknown_manager"))
    assert error.value.status_code == 404
    assert "/start" in error.value.detail


def test_legacy_database_gets_workflow_migration(monkeypatch, tmp_path):
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
        connection.execute(text("""
            INSERT INTO agent_applications (id, telegram_id, name, email, country, phone, status, created_at)
            VALUES (1, 101, 'Legacy Agent', 'legacy@example.com', 'Кыргызстан', '+996700000000', 'active_agent', CURRENT_TIMESTAMP)
        """))
    monkeypatch.setattr(storage, "engine", legacy_engine)
    storage.init_storage()
    columns = {column["name"] for column in inspect(legacy_engine).get_columns("agent_applications")}
    assert {"geo_code", "agent_id", "activated_at", "deposit_submitted_at", "documents_verified_at"}.issubset(columns)
    assert inspect(legacy_engine).has_table("agent_application_history")
    assert inspect(legacy_engine).has_table("geo_agent_settings")
    with Session(legacy_engine) as session:
        migrated = session.get(storage.AgentApplication, 1)
        assert migrated.status == "approved"
        assert migrated.agent_id == "PA-000001"
        assert migrated.geo_code == "KG"
