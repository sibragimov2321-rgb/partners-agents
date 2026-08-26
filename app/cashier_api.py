"""Safe integration boundary for a future cashier Player ID API.

The cashier vendor contract has not been supplied yet, so this module does
not guess an endpoint, HTTP method, authentication scheme, or response shape.
It gives the application one async, cached entry point to wire up once those
details are available.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass

import httpx


REQUEST_TIMEOUT_SECONDS = 5.0
MAX_RETRIES = 1
CACHE_TTL_SECONDS = 300


class CashierApiUnavailable(RuntimeError):
    """The cashier integration is not configured or cannot be reached."""


@dataclass(frozen=True)
class PlayerVerification:
    exists: bool
    currency: str | None = None
    geo_code: str | None = None
    country: str | None = None


_cache: dict[str, tuple[float, PlayerVerification]] = {}
_cache_lock = asyncio.Lock()
_client: httpx.AsyncClient | None = None


def cashier_is_configured() -> bool:
    """Only credentials are configured now; the vendor contract comes later."""
    return bool(os.getenv("CASHIER_API_KEY", "").strip() and os.getenv("CASHIER_API_BASE_URL", "").strip())


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
    """Validate a Player ID after the cashier API contract is configured.

    The method intentionally refuses to make a request until the provider
    documents the endpoint, method, headers and response mapping. Once known,
    only the private adapter below needs implementation; callers keep this
    stable async API, including its 5-second timeout, one retry and cache.
    """
    clean_id = player_id.strip()
    if not clean_id:
        raise CashierApiUnavailable("Player ID is empty")
    if not cashier_is_configured():
        raise CashierApiUnavailable("Cashier API is not configured")

    async with _cache_lock:
        cached = _cache.get(clean_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]

    # No endpoint is guessed here. Implement this adapter only from the
    # official cashier API documentation; use _http_client() for pooled async
    # requests and retry at most MAX_RETRIES once on transient failures.
    raise CashierApiUnavailable("Cashier API contract is not configured")


async def cache_verification(player_id: str, verification: PlayerVerification) -> None:
    """Helper for the future documented adapter: cache successful results."""
    if verification.exists:
        async with _cache_lock:
            now = time.monotonic()
            if len(_cache) >= 2048:
                expired = [key for key, (expires_at, _) in _cache.items() if expires_at <= now]
                for key in expired:
                    _cache.pop(key, None)
            _cache[player_id.strip()] = (now + CACHE_TTL_SECONDS, verification)
