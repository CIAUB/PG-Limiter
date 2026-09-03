"""
Smoke tests for the dashboard endpoint.

These tests don't start uvicorn. They use FastAPI's TestClient
to dispatch requests directly against the ASGI app.
"""

from __future__ import annotations

import base64
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make sure the project root is on sys.path.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def fake_files(monkeypatch, tmp_path):
    """
    Create a fake `config.json` + `.disable_users.json` under a temp
    directory and patch `api_server` to read from there.
    """
    config = {
        "panel": {
            "domain": "test.panel.example.com",
            "username": "admin",
            "password": "pw",
            "api_key": "pg_key_fake-uuid",
        },
        "limits": {"general": 3, "special": {"alice": 5, "bob": 2}},
        "timing": {"check_interval": 90, "time_to_active_users": 600},
        "monitoring": {"check_interval": 90},
        "country_code": "IR",
        "users": {"except": ["carol"]},
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(__import__("json").dumps(config), encoding="utf-8")

    disabled_file = tmp_path / ".disable_users.json"
    disabled_file.write_text(
        __import__("json").dumps({
            "disabled_users": {"dave": 1.0, "erin": 2.0},
            "enable_at": {},
        }),
        encoding="utf-8",
    )

    return {
        "config_file": str(config_file),
        "disabled_file": str(disabled_file),
    }


def _basic_auth(user: str, password: str) -> dict:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _patch_credentials(monkeypatch, fake_files, user="tester", password="s3cret"):
    """Write `api.username/password` into the same config file and patch
    `api_server` to point at it."""
    import json
    cfg_path = Path(fake_files["config_file"])
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    data.setdefault("api", {})
    data["api"]["username"] = user
    data["api"]["password"] = password
    cfg_path.write_text(json.dumps(data), encoding="utf-8")


def test_dashboard_html_is_served(fake_files, monkeypatch):
    """`GET /dashboard` returns the HTML file with HTTP 200."""
    from fastapi.testclient import TestClient

    _patch_credentials(monkeypatch, fake_files)

    # Patch the file paths the api_server uses.
    import api_server

    monkeypatch.setattr(api_server, "CONFIG_FILE", fake_files["config_file"])
    monkeypatch.setattr(api_server, "DISABLED_USERS_FILE", fake_files["disabled_file"])

    with TestClient(api_server.app) as client:
        r = client.get("/dashboard", headers=_basic_auth("tester", "s3cret"))
        assert r.status_code == 200, r.text
        # The HTML is the one we wrote to api/dashboard.html.
        assert "PG-Limiter" in r.text
        assert "/api/dashboard/state" in r.text


def test_dashboard_state_aggregates_json_files(fake_files, monkeypatch):
    """`GET /api/dashboard/state` reads the legacy JSON state."""
    from fastapi.testclient import TestClient

    _patch_credentials(monkeypatch, fake_files)

    import api_server

    monkeypatch.setattr(api_server, "CONFIG_FILE", fake_files["config_file"])
    monkeypatch.setattr(api_server, "DISABLED_USERS_FILE", fake_files["disabled_file"])

    with TestClient(api_server.app) as client:
        r = client.get("/api/dashboard/state", headers=_basic_auth("tester", "s3cret"))
        assert r.status_code == 200, r.text
        data = r.json()

        # Aggregated counts
        assert data["counts"]["special_limits"] == 2
        assert data["counts"]["except_users"] == 1
        assert data["counts"]["disabled_users"] == 2

        # Auth mode reflects the API key in config
        assert data["auth_mode"] == "api_key"
        assert data["panel_domain"] == "test.panel.example.com"

        # General limit / interval / country all surfaced
        assert data["config"]["general_limit"] == 3
        assert data["config"]["check_interval"] == 90
        assert data["config"]["country_code"] == "IR"


def test_dashboard_state_requires_auth(fake_files, monkeypatch):
    from fastapi.testclient import TestClient

    _patch_credentials(monkeypatch, fake_files)

    import api_server

    monkeypatch.setattr(api_server, "CONFIG_FILE", fake_files["config_file"])
    monkeypatch.setattr(api_server, "DISABLED_USERS_FILE", fake_files["disabled_file"])

    with TestClient(api_server.app) as client:
        r = client.get("/api/dashboard/state")
        assert r.status_code == 401


def test_dashboard_state_rejects_wrong_password(fake_files, monkeypatch):
    from fastapi.testclient import TestClient

    _patch_credentials(monkeypatch, fake_files)

    import api_server

    monkeypatch.setattr(api_server, "CONFIG_FILE", fake_files["config_file"])
    monkeypatch.setattr(api_server, "DISABLED_USERS_FILE", fake_files["disabled_file"])

    with TestClient(api_server.app) as client:
        r = client.get(
            "/api/dashboard/state",
            headers=_basic_auth("tester", "wrong"),
        )
        assert r.status_code == 401
