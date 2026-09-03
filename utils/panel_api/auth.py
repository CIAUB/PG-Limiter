"""
Authentication and token management for the PasarGuard panel API.

Supports two credential modes:

1. **Username / password** (legacy): POSTs to `/api/admin/token` using
   the OAuth2PasswordRequestForm format. The returned `access_token` is
   cached (in-process + Redis when available) for ~30 minutes.

2. **API key** (new in PasarGuard v5+): a `pg_key_<uuid>` key passed via
   the `X-Api-Key` header or `Authorization: ApiKey <key>`. No login
   roundtrip is required. Set `PANEL_API_KEY` in the environment to use
   this mode; the key bypasses admin-password rotation issues.

The active mode is decided at call time by `get_token()`, which keeps
backward compatibility with existing setups that only configure
`PANEL_USERNAME` / `PANEL_PASSWORD`.
"""

import asyncio
import os
import random
import sys
import time
from ssl import SSLError

try:
    import httpx
except ImportError:
    print("Module 'httpx' is not installed use: 'pip install httpx' to install it")
    sys.exit()

from utils.logs import logger, log_api_request, get_logger
from utils.types import PanelType

# Try to import Redis cache
try:
    from utils.redis_cache import (
        get_cached_token, cache_token, invalidate_token as redis_invalidate_token
    )
    REDIS_CACHE_AVAILABLE = True
except ImportError:
    REDIS_CACHE_AVAILABLE = False

# Shared HTTP client (NEW) — when available, reuses one connection pool
try:
    from utils.panel_api._connection import get_panel_client
    SHARED_CLIENT_AVAILABLE = True
except ImportError:  # pragma: no cover - defensive
    SHARED_CLIENT_AVAILABLE = False

# Module logger
auth_logger = get_logger("panel_api.auth")

# Fallback in-memory token cache (used if Redis not available)
_token_cache = {
    "token": None,
    "expires_at": 0,
    "panel_domain": None
}

# API-key support: resolved lazily, so test rigs can set PANEL_API_KEY
# at runtime without re-importing this module.
_API_KEY_ENV = "PANEL_API_KEY"


def _resolve_api_key(panel_data: PanelType) -> str | None:
    """
    Return the API key to use for the given panel, or None if not configured.

    Resolution order:
      1. `panel_data.panel_api_key` (set programmatically by callers).
      2. `PANEL_API_KEY` env var.
    """
    key = getattr(panel_data, "panel_api_key", None)
    if key:
        return key
    env = os.environ.get(_API_KEY_ENV, "").strip()
    return env or None


def has_api_key(panel_data: PanelType) -> bool:
    """Whether `panel_data` should authenticate via API key."""
    return _resolve_api_key(panel_data) is not None


def get_auth_headers(api_key: str) -> dict:
    """
    Build the HTTP headers PasarGuard expects for API-key auth.

    PasarGuard accepts either:
      - `X-Api-Key: pg_key_<uuid>`, or
      - `Authorization: ApiKey pg_key_<uuid>`
    We send both to be safe across panel versions.
    """
    return {
        "X-Api-Key": api_key,
        "Authorization": f"ApiKey {api_key}",
    }


async def invalidate_token_cache():
    """Invalidate the cached token (useful when getting 401 errors)"""
    if REDIS_CACHE_AVAILABLE:
        # Invalidate Redis cache
        try:
            await redis_invalidate_token(_token_cache.get("panel_domain", "default"))
        except Exception as e:
            auth_logger.warning(f"Failed to invalidate Redis token cache: {e}")
    
    # Always clear in-memory cache too
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0
    auth_logger.info("🔑 Token cache invalidated")


async def safe_send_logs_panel(message: str):
    """Safely send logs from panel_api, handling import errors gracefully"""
    try:
        from telegram_bot.send_message import send_logs
        await send_logs(message)
    except ImportError as e:
        auth_logger.warning(f"Could not import send_logs: {e}")
    except Exception as e:
        auth_logger.error(f"Failed to send telegram message: {e}")


async def get_token(panel_data: PanelType, force_refresh: bool = False) -> PanelType | ValueError:
    """
    Get access token from the panel API with caching (Redis or in-memory).

    Two credential modes are supported:

    - **API key** (`PANEL_API_KEY` env or `panel_data.panel_api_key`):
      PasarGuard v5+ lets you mint long-lived `pg_key_<uuid>` keys. We
      skip the login roundtrip and return the panel_data unchanged so
      callers can use the key directly via `get_auth_headers(api_key)`.

    - **Username / password** (legacy default): we POST to
      `/api/admin/token` and cache the resulting `access_token` for
      ~30 minutes (or whatever `access_token_expires_minutes` the panel
      returns, if present).

    Args:
        panel_data:    Panel connection info.
        force_refresh: Force a new login even if a token is cached.

    Returns:
        PanelType with `panel_token` set (or, in API-key mode, unchanged).

    Raises:
        ValueError: If username/password login fails after all retries.
    """
    # API-key short-circuit: no login needed.
    api_key = _resolve_api_key(panel_data)
    if api_key:
        panel_data.panel_token = api_key
        auth_logger.debug("🔑 Using API key for auth (skipping /api/admin/token)")
        return panel_data

    current_time = time.time()

    # Try Redis cache first
    if not force_refresh and REDIS_CACHE_AVAILABLE:
        try:
            cached_token = await get_cached_token(panel_data.panel_domain)
            if cached_token:
                panel_data.panel_token = cached_token
                auth_logger.debug(f"🔑 Using Redis cached token")
                return panel_data
        except Exception as e:
            auth_logger.warning(f"Redis cache error: {e}, falling back to in-memory")

    # Fallback: Check in-memory cache
    if (not force_refresh and
        _token_cache["token"] is not None and
        _token_cache["panel_domain"] == panel_data.panel_domain and
        current_time < _token_cache["expires_at"]):
        panel_data.panel_token = _token_cache["token"]
        remaining = int(_token_cache["expires_at"] - current_time)
        auth_logger.debug(f"🔑 Using in-memory cached token (expires in {remaining}s)")
        return panel_data

    auth_logger.info(f"🔑 Fetching new token for {panel_data.panel_domain} (force_refresh={force_refresh})")

    # Need to fetch a new token
    payload = {
        "username": f"{panel_data.panel_username}",
        "password": f"{panel_data.panel_password}",
    }
    max_attempts = 5
    for attempt in range(max_attempts):
        auth_logger.debug(f"🔑 Token fetch attempt {attempt + 1}/{max_attempts}")
        for scheme in ["https", "http"]:
            url = f"{scheme}://{panel_data.panel_domain}/api/admin/token"
            start_time = time.perf_counter()
            try:
                if SHARED_CLIENT_AVAILABLE:
                    client = get_panel_client()
                else:
                    client = httpx.AsyncClient(verify=False)
                    owns_client = True
                try:
                    response = await client.post(url, data=payload, timeout=5)
                    elapsed = (time.perf_counter() - start_time) * 1000
                    response.raise_for_status()
                finally:
                    if not SHARED_CLIENT_AVAILABLE:
                        await client.aclose()

                log_api_request("POST", url, response.status_code, elapsed)

                # Try to parse JSON response
                try:
                    json_obj = response.json()
                except Exception as json_error:
                    auth_logger.error(f"Failed to parse JSON from {url}: {json_error}")
                    auth_logger.debug(f"Response text: {response.text[:200]}")
                    continue

                # Check if response is a dict and has access_token
                if not isinstance(json_obj, dict):
                    auth_logger.error(f"Response is not a dict: {type(json_obj)} - {json_obj}")
                    continue

                if "access_token" not in json_obj:
                    auth_logger.error(f"Response missing 'access_token' key. Keys: {list(json_obj.keys())}")
                    continue

                token = json_obj["access_token"]

                # Determine TTL.
                # PasarGuard v5+ may return `access_token_expires_minutes`;
                # fall back to 30 minutes (the historical hard-coded value)
                # when not present.
                ttl_minutes = json_obj.get("access_token_expires_minutes")
                try:
                    ttl_seconds = max(60, int(ttl_minutes) * 60) if ttl_minutes else 1800
                except (TypeError, ValueError):
                    ttl_seconds = 1800
                # Apply a small safety margin (5%) so we refresh slightly
                # before the panel's hard expiry.
                ttl_seconds = int(ttl_seconds * 0.95)

                # Cache the token in Redis if available
                if REDIS_CACHE_AVAILABLE:
                    try:
                        await cache_token(panel_data.panel_domain, token)
                        auth_logger.debug("🔑 Token cached in Redis")
                    except Exception as e:
                        auth_logger.warning(f"Failed to cache token in Redis: {e}")

                # Always store in in-memory cache as fallback
                _token_cache["token"] = token
                _token_cache["expires_at"] = current_time + ttl_seconds
                _token_cache["panel_domain"] = panel_data.panel_domain

                panel_data.panel_token = token
                auth_logger.info(
                    f"🔑 Token obtained (cached for {ttl_seconds // 60}m) [{elapsed:.0f}ms]"
                )
                return panel_data
            except httpx.HTTPStatusError:
                elapsed = (time.perf_counter() - start_time) * 1000
                log_api_request("POST", url, response.status_code, elapsed, f"HTTP {response.status_code}")
                message = f"[{response.status_code}] {response.text}"
                await safe_send_logs_panel(message)
                auth_logger.error(f"HTTP error: {message}")
                continue
            except SSLError as ssl_err:
                elapsed = (time.perf_counter() - start_time) * 1000
                log_api_request("POST", url, None, elapsed, f"SSL Error: {ssl_err}")
                auth_logger.debug(f"SSL error for {scheme}, trying next scheme")
                continue
            except httpx.TimeoutException:
                elapsed = (time.perf_counter() - start_time) * 1000
                log_api_request("POST", url, None, elapsed, "Timeout")
                auth_logger.warning(f"Timeout connecting to {url}")
                continue
            except httpx.ConnectError as conn_err:
                elapsed = (time.perf_counter() - start_time) * 1000
                log_api_request("POST", url, None, elapsed, f"Connection error: {conn_err}")
                auth_logger.warning(f"Connection error to {url}: {conn_err}")
                continue
            except Exception as error:  # pylint: disable=broad-except
                elapsed = (time.perf_counter() - start_time) * 1000
                log_api_request("POST", url, None, elapsed, str(error))
                message = f"An unexpected error occurred: {error}"
                await safe_send_logs_panel(message)
                auth_logger.error(message)
                continue
        wait_time = min(30, random.randint(2, 5) * (attempt + 1))
        auth_logger.debug(f"🔑 Waiting {wait_time}s before retry...")
        await asyncio.sleep(wait_time)

    message = (
        f"Failed to get token after {max_attempts} attempts. Make sure the panel is running "
        + "and the username and password are correct."
    )
    await safe_send_logs_panel(message)
    auth_logger.error(f"🔑 {message}")
    raise ValueError(message)
