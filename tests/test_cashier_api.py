import asyncio

import pytest

from app import cashier_api


def test_cashier_adapter_is_safe_until_vendor_contract_is_available(monkeypatch):
    monkeypatch.delenv("CASHIER_API_KEY", raising=False)
    monkeypatch.delenv("CASHIER_API_BASE_URL", raising=False)
    assert cashier_api.cashier_is_configured() is False

    async def check():
        with pytest.raises(cashier_api.CashierApiUnavailable):
            await cashier_api.verify_player("123456")

    asyncio.run(check())


def test_cashier_adapter_requires_both_secret_settings(monkeypatch):
    monkeypatch.setenv("CASHIER_API_KEY", "secret")
    monkeypatch.delenv("CASHIER_API_BASE_URL", raising=False)
    assert cashier_api.cashier_is_configured() is False
