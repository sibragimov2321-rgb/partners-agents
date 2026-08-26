import asyncio
import hashlib

import httpx
import pytest

from app import cashier_api


def configure_cashdesk(monkeypatch):
    monkeypatch.setenv("CASHIER_HASH", "fhd.ncbf9hf2ythr")
    monkeypatch.setenv("CASHIER_PASS", "123123")
    monkeypatch.setenv("CASHDESK_ID", "123")


def test_player_search_confirm_and_sign_follow_documented_formula(monkeypatch):
    configure_cashdesk(monkeypatch)
    player_id = "321"
    expected_confirm = hashlib.md5(b"321:fhd.ncbf9hf2ythr").hexdigest()
    first = hashlib.sha256(b"hash=fhd.ncbf9hf2ythr&userid=321&cashdeskid=123").hexdigest()
    second = hashlib.md5(b"userid=321&cashierpass=123123&hash=fhd.ncbf9hf2ythr").hexdigest()
    expected_sign = hashlib.sha256((first + second).encode()).hexdigest()

    assert cashier_api.player_search_confirm(player_id) == expected_confirm
    assert cashier_api.player_search_sign(player_id) == expected_sign


def test_cashier_adapter_is_disabled_without_documented_credentials(monkeypatch):
    for key in ("CASHIER_HASH", "CASHIER_PASS", "CASHDESK_ID"):
        monkeypatch.delenv(key, raising=False)
    assert cashier_api.cashier_is_configured() is False

    async def check():
        with pytest.raises(cashier_api.CashierApiUnavailable):
            await cashier_api.verify_player("123456")

    asyncio.run(check())


def test_player_lookup_uses_documented_url_query_and_sign(monkeypatch):
    configure_cashdesk(monkeypatch)
    cashier_api._cache.clear()
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"userId": 321, "currencyId": 77, "name": "Test Player"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def check():
        async def get_client():
            return client

        monkeypatch.setattr(cashier_api, "_http_client", get_client)
        result = await cashier_api.verify_player("321")
        assert result.exists is True
        assert result.currency_id == "77"
        assert result.name == "Test Player"
        assert calls[0].url.path.endswith("/CashdeskBotAPI/Users/321")
        assert calls[0].url.params["cashdeskId"] == "123"
        assert calls[0].url.params["confirm"] == cashier_api.player_search_confirm("321")
        assert calls[0].headers["sign"] == cashier_api.player_search_sign("321")
        await client.aclose()

    asyncio.run(check())


def test_currency_mapping_is_centralized_and_never_guessed(monkeypatch):
    monkeypatch.setenv("CASHIER_CURRENCY_GEO_MAP", '{"77":"TJ","80":["UZ","KG"]}')
    assert cashier_api.currency_matches_geo("77", "tj") is True
    assert cashier_api.currency_matches_geo("80", "KG") is True
    assert cashier_api.currency_matches_geo("77", "UZ") is False
    monkeypatch.setenv("CASHIER_CURRENCY_GEO_MAP", "not-json")
    assert cashier_api.currency_matches_geo("77", "TJ") is False
