import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ.setdefault("BOT_TOKEN", "123456:test-token")

from app import storage, webapi
from app.storage import AgentApplication, Giveaway, GiveawayAuditLog


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(storage, "engine", test_engine)
    monkeypatch.setattr(webapi, "engine", test_engine)
    monkeypatch.setattr(webapi, "MANAGER_IDS", {"900"})
    monkeypatch.setattr(webapi, "MANAGER_ID_LIST", ["900"])
    monkeypatch.setattr(webapi, "SUPERADMIN_IDS", {"900"})
    storage.init_storage()
    return test_engine


def user(user_id: int):
    return {"id": user_id, "username": f"user{user_id}", "first_name": "Test", "last_name": "User"}


def giveaway_input(**overrides):
    now = datetime.now(webapi.PROJECT_TIMEZONE)
    values = {
        "title": "Test Giveaway",
        "description": "A test giveaway for the automated test suite.",
        "prize": "500",
        "winner_count": 3,
        "start_at": now - timedelta(minutes=1),
        "end_at": now + timedelta(days=1),
        "geo_codes": ["UZ", "KG", "TJ", "TM"],
        "rules": "One player ID and one Telegram account per draw.",
    }
    values.update(overrides)
    return webapi.GiveawayCreateIn(**values)


def new_giveaway(manager=None, **overrides):
    return webapi.create_giveaway(manager or user(900), giveaway_input(**overrides))


def close_giveaway_for_draw(engine, giveaway_id: int):
    with Session(engine) as session:
        giveaway = session.get(Giveaway, giveaway_id)
        giveaway.end_at = datetime.utcnow() - timedelta(seconds=1)
        giveaway.entry_deadline = giveaway.end_at
        giveaway.draw_date = giveaway.end_at
        session.commit()


def test_same_day_start_and_end_are_allowed_when_end_is_in_the_future(isolated_database):
    now = datetime.now(webapi.PROJECT_TIMEZONE)
    giveaway = new_giveaway(title="", description="", start_at=now + timedelta(minutes=1), end_at=now + timedelta(minutes=10))
    assert giveaway["status"] == "draft"
    assert giveaway["title"] == "🎁 Розыгрыш"
    assert giveaway["description"] == ""
    assert giveaway["start_at"] < giveaway["end_at"]


def test_end_time_must_be_after_start_and_current_time(isolated_database):
    now = datetime.now(webapi.PROJECT_TIMEZONE)
    with pytest.raises(ValueError, match="Окончание розыгрыша должно быть позже начала"):
        giveaway_input(start_at=now + timedelta(minutes=10), end_at=now + timedelta(minutes=5))
    with pytest.raises(HTTPException, match="Дата и время окончания розыгрыша должны быть позже текущего времени"):
        new_giveaway(start_at=now - timedelta(minutes=2), end_at=now - timedelta(minutes=1))


def test_webapp_utc_dates_keep_the_correct_order(isolated_database):
    now = datetime.now(timezone.utc)
    giveaway = new_giveaway(
        start_at=(now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        end_at=(now + timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
    )
    assert giveaway["start_at"].endswith("+00:00")
    assert giveaway["end_at"].endswith("+00:00")


def test_player_join_duplicates_exclusion_and_secure_draw(isolated_database):
    manager = user(900)
    giveaway = new_giveaway(manager)
    assert giveaway["status"] == "active"
    participants = []
    for offset, geo in enumerate(["UZ", "KG", "TJ", "TM", "UZ"], start=1):
        participants.append(webapi.join_giveaway(user(100 + offset), giveaway["id"], webapi.GiveawayJoinIn(geo_code=geo, player_id=f"player-{offset}")))
    with pytest.raises(HTTPException) as duplicate_telegram:
        webapi.join_giveaway(user(101), giveaway["id"], webapi.GiveawayJoinIn(geo_code="UZ", player_id="new-player"))
    assert duplicate_telegram.value.status_code == 409
    with pytest.raises(HTTPException) as duplicate_player:
        webapi.join_giveaway(user(200), giveaway["id"], webapi.GiveawayJoinIn(geo_code="UZ", player_id="player-1"))
    assert duplicate_player.value.status_code == 409
    assert webapi.set_participant_excluded(manager, giveaway["id"], participants[-1]["id"], webapi.GiveawayParticipantActionIn(reason="Тестовое исключение"))["status"] == "excluded"
    assert webapi.restore_participant(manager, giveaway["id"], participants[-1]["id"])["status"] == "active"
    with pytest.raises(HTTPException, match="после его окончания"):
        webapi.draw_giveaway(manager, giveaway["id"])
    close_giveaway_for_draw(isolated_database, giveaway["id"])
    drawn = webapi.draw_giveaway(manager, giveaway["id"])
    assert drawn["status"] == "drawn"
    assert len(drawn["winners"]) == 3
    assert len({winner["participant"]["participant_number"] for winner in drawn["winners"]}) == 3
    assert all(winner["participant"]["player_id"].startswith("player-") for winner in drawn["winners"])
    public = webapi.public_winners(user(501), giveaway["id"])
    assert public and all(item["participant"]["player_id"].startswith("****") for item in public)
    with pytest.raises(HTTPException) as second_draw:
        webapi.draw_giveaway(manager, giveaway["id"])
    assert second_draw.value.status_code == 409
    assert any(item["action"] == "draw_completed" for item in webapi.giveaway_history(manager, giveaway["id"]))
    with Session(isolated_database) as session:
        assert session.query(GiveawayAuditLog).filter_by(giveaway_id=giveaway["id"]).count() >= 5


def test_only_manager_can_control_giveaway_and_broadcast_targets(isolated_database):
    giveaway = new_giveaway()
    with pytest.raises(HTTPException) as denied:
        webapi.create_giveaway(user(111), giveaway_input())
    assert denied.value.status_code == 403
    manager = user(900)
    joined = webapi.join_giveaway(user(111), giveaway["id"], webapi.GiveawayJoinIn(geo_code="UZ", player_id="partner-111"))
    webapi.join_giveaway(user(112), giveaway["id"], webapi.GiveawayJoinIn(geo_code="KG", player_id="partner-112"))
    targets = webapi.create_giveaway_broadcast(manager, giveaway["id"], webapi.GiveawayBroadcastIn(audience="geo", geo_codes=["UZ"], message="Тестовое сообщение", button_text="Участвовать"))
    assert targets["recipients"] == [111]
    listed = webapi.list_giveaway_participants(manager, giveaway["id"], query=joined["participant_number"])
    assert listed["total"] == 2
    assert listed["participants"][0]["player_id"] == "partner-111"


def test_role_display_priority_for_user_manager_agent_and_superadmin(isolated_database):
    owner, manager, agent, regular_user = user(900), user(901), user(902), user(903)
    webapi.grant_manager_access(owner, webapi.ManagerAccessIn(telegram_id=manager["id"]))
    with Session(isolated_database) as session:
        session.add(AgentApplication(telegram_id=agent["id"], name="Agent Test", email="agent@example.com", country="Tajikistan", phone="+992900000000", status="approved", agent_id="PA-000902"))
        session.commit()
    assert webapi.profile_payload(regular_user)["display_role"] == "user"
    assert webapi.profile_payload(agent)["display_role"] == "agent"
    assert webapi.profile_payload(manager)["display_role"] == "manager"
    assert webapi.profile_payload(owner)["display_role"] == "superadmin"


def test_manager_and_superadmin_can_create_scheduled_giveaways(isolated_database):
    owner, manager = user(900), user(901)
    webapi.grant_manager_access(owner, webapi.ManagerAccessIn(telegram_id=manager["id"]))
    now = datetime.now(webapi.PROJECT_TIMEZONE)
    assert new_giveaway(manager, start_at=now + timedelta(hours=1), end_at=now + timedelta(hours=2))["status"] == "draft"
    assert new_giveaway(owner, start_at=now + timedelta(hours=3), end_at=now + timedelta(hours=4))["status"] == "draft"
