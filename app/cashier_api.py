"""CashdeskBotAPI adapter used only by the giveaway Player ID check.

The request composition follows the vendor's BotAPI document: ``GET
/Users/{userId}?confirm={confirm}&cashdeskId={cashdeskId}``, the ``sign``
header, and its documented SHA256/MD5 formulas. No cashier secret is sent to
a browser or stored in the application database.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass

import httpx


REQUEST_TIMEOUT_SECONDS = 5.0
MAX_RETRIES = 1
CACHE_TTL_SECONDS = 300
DEFAULT_API_BASE_URL = "https://partners.servcul.com/CashdeskBotAPI"


class CashierApiUnavailable(RuntimeError):
    """The cashier integration is not configured or cannot be reached."""


@dataclass(frozen=True)
class PlayerVerification:
    exists: bool
    currency_id: str | None = None
    name: str | None = None


_cache: dict[str, tuple[float, PlayerVerification]] = {}
_cache_lock = asyncio.Lock()
_client: httpx.AsyncClient | None = None


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def cashier_is_configured() -> bool:
    """The documented player-search method needs these three credentials."""
    return bool(_env("CASHIER_HASH") and _env("CASHIER_PASS") and _env("CASHDESK_ID"))


def _api_base_url() -> str:
    return (_env("CASHIER_API_BASE_URL") or DEFAULT_API_BASE_URL).rstrip("/")


def _md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def player_search_confirm(player_id: str) -> str:
    """``confirm = MD5(userId:hash)`` from CashdeskBotAPI section 2.2."""
    return _md5(f"{player_id}:{_env('CASHIER_HASH')}")


def player_search_sign(player_id: str) -> str:
    """Create the documented Player Search ``sign`` value (section 2.1)."""
    hash_value = _env("CASHIER_HASH")
    cashdesk_id = _env("CASHDESK_ID")
    cashier_pass = _env("CASHIER_PASS")
    first = _sha256(f"hash={hash_value}&userid={player_id}&cashdeskid={cashdesk_id}")
    second = _md5(f"userid={player_id}&cashierpass={cashier_pass}&hash={hash_value}")
    return _sha256(first + second)


def currency_geo_mapping() -> dict[str, set[str]]:
    """Read the centrally managed non-secret ``currencyId -> GEO`` mapping.

    The value is JSON, e.g. ``{\"7\": \"TJ\", \"8\": [\"UZ\"]}``.
    Invalid values are deliberately treated as empty rather than guessed.
    """
    raw = _env("CASHIER_CURRENCY_GEO_MAP")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    mapping: dict[str, set[str]] = {}
    for currency_id, geo_values in data.items():
        values = geo_values if isinstance(geo_values, list) else [geo_values]
        geos = {str(value).strip().upper() for value in values if str(value).strip()}
        if geos:
            mapping[str(currency_id).strip()] = geos
    return mapping


def currency_matches_geo(currency_id: str | None, geo_code: str) -> bool:
    if not currency_id:
        return False
    return geo_code.strip().upper() in currency_geo_mapping().get(str(currency_id), set())


async def _http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _client


async def close_cashier_client() -> None:
    """Release pooled HTTP connections on application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def verify_player(player_id: str) -> PlayerVerification:
    """Look up a player with one retry for transient external API failures."""
    clean_id = player_id.strip()
    if not clean_id or not clean_id.isdigit():
        raise CashierApiUnavailable("Player ID должен состоять из цифр.")
    if not cashier_is_configured():
        raise CashierApiUnavailable("Cashier API is not configured")

    async with _cache_lock:
        cached = _cache.get(clean_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]

    client = await _http_client()
    response: httpx.Response | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.get(
                f"{_api_base_url()}/Users/{clean_id}",
                params={"confirm": player_search_confirm(clean_id), "cashdeskId": _env("CASHDESK_ID")},
                headers={"sign": player_search_sign(clean_id)},
            )
            if response.status_code == 404:
                return PlayerVerification(exists=False)
            if response.status_code < 500 and response.status_code != 429:
                break
        except httpx.RequestError as error:
            if attempt >= MAX_RETRIES:
                raise CashierApiUnavailable("Cashier API request failed") from error
        if attempt < MAX_RETRIES:
            await asyncio.sleep(0.15)

    if response is None or response.status_code >= 400:
        raise CashierApiUnavailable("Cashier API request failed")
    try:
        data = response.json()
    except ValueError as error:
        raise CashierApiUnavailable("Cashier API returned an invalid response") from error
    if not isinstance(data, dict) or data.get("userId") is None or data.get("currencyId") is None:
        raise CashierApiUnavailable("Cashier API returned an incomplete player record")
    verification = PlayerVerification(
        exists=True,
        currency_id=str(data["currencyId"]),
        name=str(data.get("name") or "") or None,
    )
    await cache_verification(clean_id, verification)
    return verification


async def cache_verification(player_id: str, verification: PlayerVerification) -> None:
    """Helper for the future documented adapter: cache successful results."""
    if verification.exists:
        async with _cache_lock:
            now = time.monotonic()
            if len(_cache) >= 2048:
                for key, (expires_at, _) in list(_cache.items()):
                    if expires_at <= now:
                        _cache.pop(key, None)
            _cache[player_id.strip()] = (now + CACHE_TTL_SECONDS, verification)
