"""
Smoke tests for PasarGuard v5.x API compatibility.

These tests don't hit a real panel. They assert that our code
*would* hit the right URLs, parse the v5.x response shapes, and
forward the right fields.

Run with:
    pytest tests/test_pasarguard_compat.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

# Make sure the project root is on sys.path when the test is run from
# any working directory.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Test data — mirrors the PasarGuard panel v5.x OpenAPI spec
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_USER_RESPONSE = {
    "id": 42,
    "username": "alice",
    "status": "active",
    "used_traffic": 1024,
    "lifetime_used_traffic": 8192,
    "data_limit": 0,
    "data_limit_reset_strategy": "no_reset",
    "expire": 0,
    "online_at": "2026-09-03T12:00:00",
    "created_at": "2026-01-01T00:00:00",
    "edit_at": None,
    "subscription_url": "https://panel.example.com/sub/abc",
    "note": "VIP",
    "group_ids": [1, 5],
    "group_names": ["default", "vip"],
    "admin": {"username": "owner1", "id": 1},
    "proxy_settings": {"vless": {"id": "u-1"}, "vmess": {"id": "u-2"}},
    "next_plan": None,
}

SAMPLE_USERS_RESPONSE = {
    "users": [SAMPLE_USER_RESPONSE, {**SAMPLE_USER_RESPONSE, "username": "bob", "id": 43}],
    "total": 2,
}

SAMPLE_USERS_SIMPLE_RESPONSE = {
    "users": [{"id": 42, "username": "alice"}, {"id": 43, "username": "bob"}],
    "total": 2,
}

SAMPLE_NODES_RESPONSE = [
    {"id": 1, "name": "node1", "address": "10.0.0.1", "status": "connected", "enabled": True},
    {"id": 2, "name": "node2", "address": "10.0.0.2", "status": "disconnected", "enabled": True},
]

SAMPLE_TOKEN_RESPONSE = {
    "access_token": "eyJ.fake.jwt",
    "access_token_expires_minutes": 60,  # PasarGuard v5+
}


# ─────────────────────────────────────────────────────────────────────────────
# _models
# ─────────────────────────────────────────────────────────────────────────────

def test_user_response_parses_v5x():
    from utils.panel_api._models import UserResponse

    u = UserResponse.from_json(SAMPLE_USER_RESPONSE)
    assert u.username == "alice"
    assert u.id == 42
    assert u.status == "active"
    assert u.used_traffic == 1024
    assert u.lifetime_used_traffic == 8192
    assert u.subscription_url == "https://panel.example.com/sub/abc"
    assert u.note == "VIP"
    assert u.group_ids == [1, 5]
    assert u.group_names == ["default", "vip"]
    assert u.admin is not None
    assert u.admin.username == "owner1"
    assert u.admin.id == 1
    # Round-trip the admin_username helper
    assert u.admin_username() == "owner1"
    # New fields are passed through
    assert u.proxy_settings == {"vless": {"id": "u-1"}, "vmess": {"id": "u-2"}}


def test_user_response_handles_missing_fields():
    from utils.panel_api._models import UserResponse

    u = UserResponse.from_json({})  # empty dict
    assert u.username == ""
    assert u.id is None
    assert u.status is None
    assert u.group_ids == []
    # admin is an empty AdminContact when the key is absent (we don't
    # distinguish "missing" vs "empty" — either way it's a no-op).
    assert u.admin is not None
    assert u.admin.username is None
    assert u.admin.id is None


def test_users_response_parses_v5x():
    from utils.panel_api._models import UsersResponse

    parsed = UsersResponse.from_json(SAMPLE_USERS_RESPONSE)
    assert parsed.total == 2
    assert len(parsed.users) == 2
    assert {u.username for u in parsed.users} == {"alice", "bob"}


def test_users_simple_response_parses_v5x():
    from utils.panel_api._models import UsersSimpleResponse

    parsed = UsersSimpleResponse.from_json(SAMPLE_USERS_SIMPLE_RESPONSE)
    assert parsed.total == 2
    assert {u.username for u in parsed.users} == {"alice", "bob"}
    assert {u.id for u in parsed.users} == {42, 43}


def test_nodes_response_handles_bare_list():
    """The panel historically returned either a bare list or {nodes:[]}.
    We accept both for backward compat."""
    from utils.panel_api._models import NodesResponse

    parsed = NodesResponse.from_json(SAMPLE_NODES_RESPONSE)
    assert len(parsed.nodes) == 2
    assert parsed.total == 2
    assert parsed.nodes[0].id == 1
    assert parsed.nodes[0].name == "node1"


def test_nodes_response_handles_wrapped_dict():
    from utils.panel_api._models import NodesResponse

    parsed = NodesResponse.from_json({"nodes": SAMPLE_NODES_RESPONSE, "total": 2})
    assert len(parsed.nodes) == 2
    assert parsed.total == 2


# ─────────────────────────────────────────────────────────────────────────────
# _connection (lazy singleton)
# ─────────────────────────────────────────────────────────────────────────────

def test_connection_singleton_is_lazy():
    from utils.panel_api import _connection

    _connection.reset_panel_client()
    c1 = _connection.get_panel_client()
    c2 = _connection.get_panel_client()
    assert c1 is c2, "Expected a single shared client instance"

    cfg = _connection.panel_client_config()
    assert "pool_size" in cfg
    assert "default_timeout" in cfg


# ─────────────────────────────────────────────────────────────────────────────
# Auth — API key short-circuit
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_token_short_circuits_with_api_key(monkeypatch):
    """When PANEL_API_KEY is set, get_token returns the key without HTTP."""
    from utils.panel_api import auth as auth_mod
    from utils.types import PanelType

    monkeypatch.setenv("PANEL_API_KEY", "pg_key_test-uuid-1234")
    panel = PanelType("admin", "pw", "panel.example.com")

    result = await auth_mod.get_token(panel)
    assert result is panel
    assert result.panel_token == "pg_key_test-uuid-1234"


@pytest.mark.asyncio
async def test_get_token_uses_explicit_api_key(monkeypatch):
    """Explicit `panel_api_key` takes precedence over env."""
    from utils.panel_api import auth as auth_mod
    from utils.types import PanelType

    monkeypatch.setenv("PANEL_API_KEY", "pg_key_env-uuid")
    panel = PanelType("admin", "pw", "panel.example.com", panel_api_key="pg_key_explicit-uuid")

    result = await auth_mod.get_token(panel)
    assert result.panel_token == "pg_key_explicit-uuid"


def test_has_api_key_and_headers():
    from utils.panel_api import auth as auth_mod
    from utils.types import PanelType

    panel_no_key = PanelType("admin", "pw", "x")
    assert auth_mod.has_api_key(panel_no_key) is False

    panel_key = PanelType("admin", "pw", "x", panel_api_key="pg_key_x")
    assert auth_mod.has_api_key(panel_key) is True

    headers = auth_mod.get_auth_headers("pg_key_x")
    assert headers["X-Api-Key"] == "pg_key_x"
    assert headers["Authorization"] == "ApiKey pg_key_x"


# ─────────────────────────────────────────────────────────────────────────────
# Users — `/api/users/simple` adapter
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_users_simple_uses_v5x_endpoint(monkeypatch):
    """`get_users_simple` must hit `/api/users/simple`, not `/api/users`."""
    from utils.panel_api import users as users_mod
    from utils.types import PanelType

    captured = {"endpoint": None}

    class _FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.status_code = 200

        def json(self):
            return self._payload

    async def _fake_panel_get(panel, endpoint, **kwargs):
        captured["endpoint"] = endpoint
        return _FakeResponse(SAMPLE_USERS_SIMPLE_RESPONSE)

    monkeypatch.setattr(users_mod, "panel_get", _fake_panel_get)

    panel = PanelType("admin", "pw", "panel.example.com")
    out = await users_mod.get_users_simple(panel)
    assert "/api/users/simple" in captured["endpoint"]
    assert out == ["alice", "bob"]


# ─────────────────────────────────────────────────────────────────────────────
# Bulk — endpoint preference
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bulk_disable_prefers_native_endpoint(monkeypatch):
    """`bulk_disable_users` should try `/api/users/bulk/disable` first."""
    from utils.panel_api import bulk as bulk_mod
    from utils.types import PanelType

    seen = {"endpoint": None, "calls": 0}

    class _FakeResponse:
        def __init__(self, status=200, body=None):
            self.status_code = status
            self._body = body or {}
            self.text = json.dumps(self._body)

        def json(self):
            return self._body

    async def _fake_get_token_for_request(panel):
        return "fake-token"

    async def _fake_panel_request(panel, method, endpoint, **kwargs):
        seen["calls"] += 1
        seen["endpoint"] = endpoint
        return _FakeResponse(200, {}), None

    monkeypatch.setattr(bulk_mod, "_get_token_for_request", _fake_get_token_for_request)
    monkeypatch.setattr(bulk_mod, "panel_request", _fake_panel_request)

    panel = PanelType("admin", "pw", "panel.example.com")
    result = await bulk_mod.bulk_disable_users(panel, ["alice", "bob"])
    assert seen["calls"] == 1
    assert seen["endpoint"] == "/api/users/bulk/disable"
    assert set(result.as_dict()["succeeded"]) == {"alice", "bob"}


@pytest.mark.asyncio
async def test_bulk_disable_falls_back_to_per_user(monkeypatch):
    """When the native endpoint returns 404, fall back to per-user PUTs."""
    from utils.panel_api import bulk as bulk_mod
    from utils.types import PanelType

    seen = {"calls": []}

    class _FakeResponse:
        def __init__(self, status=200, body=None):
            self.status_code = status
            self._body = body or {}
            self.text = json.dumps(self._body)

        def json(self):
            return self._body

    async def _fake_get_token_for_request(panel):
        return "fake-token"

    async def _fake_panel_request(panel, method, endpoint, **kwargs):
        seen["calls"].append((method, endpoint))
        if "/api/users/bulk/" in endpoint:
            return _FakeResponse(404, {"detail": "not found"}), "Not Found"
        # Per-user PUT
        return _FakeResponse(200, {}), None

    monkeypatch.setattr(bulk_mod, "_get_token_for_request", _fake_get_token_for_request)
    monkeypatch.setattr(bulk_mod, "panel_request", _fake_panel_request)

    panel = PanelType("admin", "pw", "panel.example.com")
    result = await bulk_mod.bulk_disable_users(panel, ["alice", "bob"])
    # First call hits the native endpoint, the other two are per-user.
    assert seen["calls"][0][0] == "POST"
    assert seen["calls"][0][1] == "/api/users/bulk/disable"
    assert any(call[1].startswith("/api/user/") for call in seen["calls"][1:])
    assert set(result.as_dict()["succeeded"]) == {"alice", "bob"}


# ─────────────────────────────────────────────────────────────────────────────
# _retry
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_async_retry_eventually_succeeds():
    from utils.panel_api._retry import RetryPolicy, async_retry

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=0.001,
        max_delay=0.01,
        factor=2.0,
        jitter=0.0,
        retry_on=(ValueError,),
    )

    attempts = {"n": 0}

    @async_retry(policy, log_prefix="test")
    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ValueError("boom")
        return "ok"

    assert await flaky() == "ok"
    assert attempts["n"] == 3


@pytest.mark.asyncio
async def test_async_retry_gives_up_after_max():
    from utils.panel_api._retry import RetryPolicy, async_retry

    policy = RetryPolicy(
        max_attempts=2,
        base_delay=0.001,
        max_delay=0.01,
        factor=2.0,
        jitter=0.0,
        retry_on=(ValueError,),
    )

    @async_retry(policy, log_prefix="test")
    async def always_fail():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        await always_fail()


def test_retry_status_helpers():
    from utils.panel_api._retry import is_retryable_status, is_terminal_status, parse_retry_after

    # Retryable
    assert is_retryable_status(429) is True
    assert is_retryable_status(503) is True
    # Terminal
    assert is_terminal_status(401) is True
    assert is_terminal_status(404) is True
    # parse_retry_after
    assert parse_retry_after("3", fallback=1) == 3.0
    assert parse_retry_after(None, fallback=2) == 2.0
    assert parse_retry_after("not-a-number", fallback=4) == 4.0
