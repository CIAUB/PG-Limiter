"""
Shared HTTP connection pool for PasarGuard panel API.

# Modified/Added by CIAUB, 2026-09-03 — part of PasarGuard 5.3.0+
# compatibility fork.
# Licensed under AGPLv3 — see LICENSE.

Provides a single, lazily-initialized `httpx.AsyncClient` that all
panel API helpers reuse. This:

- Eliminates the per-call TCP+TLS handshake overhead.
- Honors `HTTP2_ENABLED` and `HTTP_POOL_SIZE` env vars.
- Can be cleanly closed on application shutdown via `close_panel_client()`.
- Avoids the "many short-lived clients" pattern that previously existed
  in `auth.py`, `users.py`, and `request_helper.py`.

This module is intentionally tiny and dependency-light. It does NOT
perform any panel-specific work; it only manages the transport.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    import httpx
except ImportError:  # pragma: no cover - httpx is a hard requirement at runtime
    httpx = None  # type: ignore[assignment]


# ─────────────────────────────────────────────────────────────────────────────
# Env-driven defaults
# ─────────────────────────────────────────────────────────────────────────────

# Verify TLS certs by default. Set PANEL_INSECURE=true to skip (matches the
# `verify=False` used elsewhere in the codebase). The flag is opt-in.
_PANEL_INSECURE = os.environ.get("PANEL_INSECURE", "false").lower() in (
    "1", "true", "yes", "on"
)

# Optional HTTP/2 support. httpx>=0.20 supports `http2=True` but it requires
# the `h2` package; we keep it off by default so the install footprint stays
# minimal. Users opt in by installing `h2` and setting HTTP2_ENABLED=true.
_HTTP2_ENABLED = os.environ.get("HTTP2_ENABLED", "false").lower() in (
    "1", "true", "yes", "on"
)

# Connection pool size. httpx limits concurrent connections per host;
# bumping this from the default 100 helps when we fan out for bulk ops.
_POOL_SIZE = int(os.environ.get("HTTP_POOL_SIZE", "100"))

# Default per-request timeout. Individual calls can still override via
# the `timeout` arg on `panel_request` / `panel_get` etc.
_DEFAULT_TIMEOUT = float(os.environ.get("PANEL_REQUEST_TIMEOUT", "30"))


# ─────────────────────────────────────────────────────────────────────────────
# Lazy singleton
# ─────────────────────────────────────────────────────────────────────────────

_client: Optional["httpx.AsyncClient"] = None


def _build_client() -> "httpx.AsyncClient":
    """Build a fresh `httpx.AsyncClient` honoring env config."""
    if httpx is None:  # pragma: no cover - httpx missing is a hard error
        raise RuntimeError(
            "httpx is required. Install with: pip install httpx"
        )

    limits = httpx.Limits(
        max_connections=_POOL_SIZE,
        max_keepalive_connections=max(10, _POOL_SIZE // 5),
    )

    timeout = httpx.Timeout(_DEFAULT_TIMEOUT, connect=10.0)

    # `http2` kwarg only valid if h2 is installed. Wrap in try/except so a
    # missing h2 doesn't break the app.
    kwargs = {
        "verify": not _PANEL_INSECURE,
        "limits": limits,
        "timeout": timeout,
        "follow_redirects": False,
    }

    if _HTTP2_ENABLED:
        try:
            return httpx.AsyncClient(http2=True, **kwargs)
        except (TypeError, ImportError):
            # h2 not installed; fall back to HTTP/1.1.
            pass

    return httpx.AsyncClient(**kwargs)


def get_panel_client() -> "httpx.AsyncClient":
    """Return the process-wide shared client, creating it on first use."""
    global _client
    if _client is None:
        _client = _build_client()
    return _client


async def close_panel_client() -> None:
    """Close the shared client. Safe to call multiple times."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        finally:
            _client = None


def reset_panel_client() -> None:
    """
    Drop the cached client reference without awaiting close.

    Useful in tests where the client is replaced with a MockTransport.
    The caller is responsible for closing the previous client.
    """
    global _client
    _client = None


def panel_client_config() -> dict:
    """Return a snapshot of the current config (for diagnostics / logs)."""
    return {
        "verify": not _PANEL_INSECURE,
        "http2": _HTTP2_ENABLED,
        "pool_size": _POOL_SIZE,
        "default_timeout": _DEFAULT_TIMEOUT,
        "client_initialized": _client is not None,
    }
