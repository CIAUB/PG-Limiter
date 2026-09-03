"""
CLI tests for the `bulk` subcommand.

We deliberately keep these tests small and focused on the
*plumbing* (argument parsing, username resolution, file I/O) rather
than the full Typer invocation. The underlying `bulk_disable_users`
and `bulk_enable_users` calls are already exercised in
`tests/test_pasarguard_compat.py`.

The full CLI invocation path (with `CliRunner`) is excluded because
importing `cli_main` pulls in the entire Telegram bot stack, which
spins up the dispatcher in test contexts. We test the helper logic
that the CLI delegates to instead.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_resolve_usernames_dedupes_and_preserves_order():
    from cli.bulk import _resolve_usernames

    out = _resolve_usernames(["alice", "bob", "alice", "carol", "bob"], None)
    assert out == ["alice", "bob", "carol"]


def test_resolve_usernames_filters_blanks_and_comments_from_file(tmp_path):
    from cli.bulk import _resolve_usernames

    f = tmp_path / "users.txt"
    f.write_text(
        "alice\n"
        "\n"
        "  \n"
        "# this is a comment\n"
        "bob\n"
        "alice\n",
        encoding="utf-8",
    )
    out = _resolve_usernames(["dave"], str(f))
    assert out == ["dave", "alice", "bob"]


def test_resolve_usernames_raises_when_empty(tmp_path):
    from cli import bulk as cli_bulk
    from typer import Exit

    with pytest.raises((Exit, SystemExit)):
        # No positional args and no file → must abort.
        cli_bulk._resolve_usernames([], None)


def test_resolve_usernames_errors_on_missing_file(tmp_path):
    from cli import bulk as cli_bulk
    from typer import Exit

    missing = tmp_path / "no-such-file.txt"
    with pytest.raises((Exit, SystemExit)):
        cli_bulk._resolve_usernames([], str(missing))


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch logic — the part that actually calls the panel API
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_CONFIG = {
    "panel": {
        "domain": "test.panel.example.com",
        "username": "admin",
        "password": "pw",
        "api_key": "",
    },
}


@pytest.mark.asyncio
async def test_run_dispatches_to_bulk_disable(monkeypatch):
    """`_run(["alice", "bob"], enable=False)` must call `bulk_disable_users`."""
    from cli import bulk as cli_bulk
    from utils.types import PanelType

    captured = {"calls": []}

    async def _fake_disable(panel, usernames, **kwargs):
        captured["calls"].append(("disable", panel, list(usernames)))
        return mock.Mock(as_dict=lambda: {
            "succeeded": list(usernames),
            "failed": [],
            "not_found": [],
        })

    async def _fake_read_config(*args, **kwargs):
        return SAMPLE_CONFIG

    monkeypatch.setattr("utils.read_config.read_config", _fake_read_config)
    # cli.bulk does `from utils.panel_api import bulk_disable_users`,
    # so we must patch the re-exported attribute, not the source module.
    monkeypatch.setattr("utils.panel_api.bulk_disable_users", _fake_disable)
    monkeypatch.setattr("utils.panel_api.bulk_enable_users", _fake_disable)  # should NOT be called

    rc = await cli_bulk._run(["alice", "bob"], enable=False)
    assert rc == 0
    assert len(captured["calls"]) == 1
    kind, panel, users = captured["calls"][0]
    assert kind == "disable"
    assert isinstance(panel, PanelType)
    assert panel.panel_domain == "test.panel.example.com"
    assert users == ["alice", "bob"]


@pytest.mark.asyncio
async def test_run_dispatches_to_bulk_enable(monkeypatch):
    """`_run([...], enable=True)` must call `bulk_enable_users`."""
    from cli import bulk as cli_bulk
    from utils.types import PanelType

    captured = {"calls": []}

    async def _fake_enable(panel, usernames, **kwargs):
        captured["calls"].append(("enable", panel, list(usernames)))
        return mock.Mock(as_dict=lambda: {
            "succeeded": list(usernames),
            "failed": [],
            "not_found": [],
        })

    async def _fake_read_config(*args, **kwargs):
        return SAMPLE_CONFIG

    monkeypatch.setattr("utils.read_config.read_config", _fake_read_config)
    monkeypatch.setattr("utils.panel_api.bulk_enable_users", _fake_enable)
    monkeypatch.setattr("utils.panel_api.bulk_disable_users", _fake_enable)  # should NOT be called

    rc = await cli_bulk._run(["alice", "bob"], enable=True)
    assert rc == 0
    assert len(captured["calls"]) == 1
    kind, panel, _ = captured["calls"][0]
    assert kind == "enable"
    assert panel.panel_domain == "test.panel.example.com"


@pytest.mark.asyncio
async def test_run_returns_error_code_when_some_users_fail(monkeypatch):
    """If any user ends up in `failed`, exit code is 1 (matches the helper's contract)."""
    from cli import bulk as cli_bulk

    async def _fake_disable(panel, usernames, **kwargs):
        return mock.Mock(as_dict=lambda: {
            "succeeded": ["alice"],
            "failed": ["bob"],
            "not_found": [],
        })

    async def _fake_read_config(*args, **kwargs):
        return SAMPLE_CONFIG

    monkeypatch.setattr("utils.read_config.read_config", _fake_read_config)
    monkeypatch.setattr("utils.panel_api.bulk_disable_users", _fake_disable)

    rc = await cli_bulk._run(["alice", "bob"], enable=False)
    assert rc == 1
