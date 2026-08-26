import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ.setdefault("BOT_TOKEN", "123456:test-token")

from app import storage, webapi
from app.storage import GiveawayAuditLog


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


def new_giveaway(manager=None):
    now = datetime.utcnow()
    return webapi.create_giveaway(manager or user(900), webapi.GiveawayCreateIn(
        title="Test Giveaway",
        description="A test giveaway for the automated test suite.",
        prize="500 USDT",
        winner_count=3,
        entry_deadline=now + timedelta(days=1),
        draw_date=now + timedelta(days=2),
        geo_codes=["UZ", "KG", "TJ", "TM"],
        rules="One player ID and one Telegram account per draw.",
    ))


def test_player_join_duplicates_exclusion_and_secure_draw(isolated_database):
    manager = user(900)
    giveaway = new_giveaway(manager)
    giveaway = webapi.giveaway_action(manager, giveaway["id"], "launch")
    participants = []
    for offset, geo in enumerate(["UZ", "KG", "TJ", "TM", "UZ"], start=1):
        participants.append(webapi.join_giveaway(user(100 + offset), giveaway["id"], webapi.GiveawayJoinIn(
            geo_code=geo, player_id=f"player-{offset}",
        )))

    with pytest.raises(HTTPException) as duplicate_telegram:
        webapi.join_giveaway(user(101), giveaway["id"], webapi.GiveawayJoinIn(geo_code="UZ", player_id="new-player"))
    assert duplicate_telegram.value.status_code == 409
    with pytest.raises(HTTPException) as duplicate_player:
        webapi.join_giveaway(user(200), giveaway["id"], webapi.GiveawayJoinIn(geo_code="UZ", player_id="player-1"))
    assert duplicate_player.value.status_code == 409

    excluded = webapi.set_participant_excluded(manager, giveaway["id"], participants[-1]["id"], webapi.GiveawayParticipantActionIn(reason="Тестовое исключение"))
    assert excluded["status"] == "excluded"
    restored = webapi.restore_participant(manager, giveaway["id"], participants[-1]["id"])
    assert restored["status"] == "active"

    drawn = webapi.draw_giveaway(manager, giveaway["id"])
    assert drawn["status"] == "drawn"
    assert len(drawn["winners"]) == 3
    numbers = [winner["participant"]["participant_number"] for winner in drawn["winners"]]
    assert len(numbers) == len(set(numbers)) == 3
    assert all(winner["participant"]["player_id"].endswith("er-" + winner["participant"]["player_id"][-1]) for winner in drawn["winners"])
    public = webapi.public_winners(user(501), giveaway["id"])
    assert public and all(item["participant"]["player_id"].startswith("****") for item in public)

    with pytest.raises(HTTPException) as second_draw:
        webapi.draw_giveaway(manager, giveaway["id"])
    assert second_draw.value.status_code == 409

    history = webapi.giveaway_history(manager, giveaway["id"])
    assert any(item["action"] == "draw_completed" for item in history)
    with Session(isolated_database) as session:
        assert session.query(GiveawayAuditLog).filter_by(giveaway_id=giveaway["id"]).count() >= 8


def test_only_manager_can_control_giveaway_and_broadcast_targets(isolated_database):
    giveaway = new_giveaway()
    with pytest.raises(HTTPException) as denied:
        webapi.giveaway_action(user(111), giveaway["id"], "launch")
    assert denied.value.status_code == 403

    manager = user(900)
    webapi.giveaway_action(manager, giveaway["id"], "launch")
    joined = webapi.join_giveaway(user(111), giveaway["id"], webapi.GiveawayJoinIn(geo_code="UZ", player_id="partner-111"))
    webapi.join_giveaway(user(112), giveaway["id"], webapi.GiveawayJoinIn(geo_code="KG", player_id="partner-112"))
    targets = webapi.create_giveaway_broadcast(manager, giveaway["id"], webapi.GiveawayBroadcastIn(
        audience="geo", geo_codes=["UZ"], message="Тестовое сообщение", button_text="Участвовать",
    ))
    assert targets["recipients"] == [111]
    listed = webapi.list_giveaway_participants(manager, giveaway["id"], query=joined["participant_number"])
    assert listed["total"] == 2
    assert listed["participants"][0]["player_id"] == "partner-111"


def test_user_manager_and_superadmin_giveaway_permissions(isolated_database):
    owner = user(900)
    manager = user(901)
    regular_user = user(902)
    webapi.grant_manager_access(owner, webapi.ManagerAccessIn(telegram_id=manager["id"]))

    regular_profile = webapi.profile_payload(regular_user)
    manager_profile = webapi.profile_payload(manager)
    owner_profile = webapi.profile_payload(owner)
    assert regular_profile["can_manage_giveaways"] is False
    assert manager_profile["is_manager"] is True
    assert manager_profile["can_manage_giveaways"] is True
    assert owner_profile["is_superadmin"] is True
    assert owner_profile["can_manage_giveaways"] is True

    with pytest.raises(HTTPException) as denied:
        webapi.create_giveaway(regular_user, webapi.GiveawayCreateIn(
            title="No access", description="Regular user cannot create giveaways.", prize="Prize",
            winner_count=1, entry_deadline=datetime.utcnow() + timedelta(days=1),
            draw_date=datetime.utcnow() + timedelta(days=2), geo_codes=["UZ"], rules="Rules",
        ))
    assert denied.value.status_code == 403
    assert webapi.create_giveaway(manager, webapi.GiveawayCreateIn(
        title="Manager access", description="Manager can create a giveaway.", prize="Prize",
        winner_count=1, entry_deadline=datetime.utcnow() + timedelta(days=1),
        draw_date=datetime.utcnow() + timedelta(days=2), geo_codes=["UZ"], rules="Rules",
    ))["status"] == "draft"
    assert webapi.create_giveaway(owner, webapi.GiveawayCreateIn(
        title="Owner access", description="Superadmin can create a giveaway.", prize="Prize",
        winner_count=1, entry_deadline=datetime.utcnow() + timedelta(days=3),
        draw_date=datetime.utcnow() + timedelta(days=4), geo_codes=["UZ"], rules="Rules",
    ))["status"] == "draft"


def test_only_one_giveaway_can_be_active_at_a_time(isolated_database):
    manager = user(900)
    first = new_giveaway(manager)
    webapi.giveaway_action(manager, first["id"], "launch")
    second = new_giveaway(manager)
    with pytest.raises(HTTPException) as error:
        webapi.giveaway_action(manager, second["id"], "launch")
    assert error.value.status_code == 409


def test_giveaway_accepts_webapp_iso_dates_and_owner_sees_own_player_id(isolated_database):
    now = datetime.now(timezone.utc)
    payload = webapi.GiveawayCreateIn(
        title="ISO date test",
        description="Timezone-safe Mini App date input.",
        prize="Test prize",
        winner_count=1,
        entry_deadline=(now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        draw_date=(now + timedelta(days=2)).isoformat().replace("+00:00", "Z"),
        geo_codes=["UZ"],
        rules="Test rules.",
    )
    giveaway = webapi.create_giveaway(user(900), payload)
    assert giveaway["entry_deadline"].endswith("+00:00") is False
    webapi.giveaway_action(user(900), giveaway["id"], "launch")
    joined = webapi.join_giveaway(user(333), giveaway["id"], webapi.GiveawayJoinIn(geo_code="UZ", player_id="player-333"))
    assert joined["player_id"] == "player-333"
    own = webapi.giveaway_participation(user(333), giveaway["id"])
    assert own["player_id"] == "player-333"
