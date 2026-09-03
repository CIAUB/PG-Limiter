"""
Bulk user operations against the PasarGuard panel via the CLI.

# Modified/Added by CIAUB, 2026-09-03 — part of PasarGuard 5.3.0+
# compatibility fork.
# Licensed under AGPLv3 — see LICENSE.

These commands call the panel directly (not the JSON state file) using
the shared `utils.panel_api.bulk` module. They are intended for
operational use: quickly enabling/disabling a list of users without
editing `config.json` or waiting for the limiter's auto-loop.

Examples:
    python cli_main.py bulk disable alice bob charlie
    python cli_main.py bulk enable --from-file users.txt
    python cli_main.py bulk disable --status limited
"""

import asyncio
import os
import sys
from typing import List, Optional

import typer

from cli.utils import console, error, info, success, warning


app = typer.Typer(
    no_args_is_help=True,
    help="Bulk enable/disable users via the panel API",
)


async def _run(usernames: List[str], enable: bool) -> int:
    """Internal: build a PanelType from .env and call the bulk helpers."""
    # Defer heavy imports so `cli --help` stays fast.
    from utils.read_config import read_config
    from utils.types import PanelType
    from utils.panel_api import bulk_disable_users, bulk_enable_users

    config = await read_config()
    panel_cfg = (config or {}).get("panel", {}) or {}

    if not panel_cfg.get("domain"):
        error("PANEL_DOMAIN is not configured. Run the limiter once or set env vars.")
        return 2

    panel = PanelType(
        panel_username=panel_cfg.get("username", ""),
        panel_password=panel_cfg.get("password", ""),
        panel_domain=panel_cfg.get("domain", ""),
        panel_api_key=panel_cfg.get("api_key") or None,
    )

    if enable:
        result = await bulk_enable_users(panel, usernames)
    else:
        result = await bulk_disable_users(panel, usernames)

    summary = result.as_dict()
    console.print(
        f"[green]✓ succeeded:[/green] {len(summary['succeeded'])}  "
        f"[yellow]failed:[/yellow] {len(summary['failed'])}  "
        f"[red]not found:[/red] {len(summary['not_found'])}"
    )
    if summary["failed"]:
        console.print("[yellow]Failed:[/yellow]")
        for u in summary["failed"]:
            console.print(f"  - {u}")
    if summary["not_found"]:
        console.print("[red]Missing in panel:[/red]")
        for u in summary["not_found"]:
            console.print(f"  - {u}")
    return 0 if not summary["failed"] else 1


def _resolve_usernames(
    names: List[str], from_file: Optional[str]
) -> List[str]:
    """Read usernames from positional args + a file (one per line)."""
    users: List[str] = list(names)
    if from_file:
        if not os.path.exists(from_file):
            error(f"File not found: {from_file}")
            raise typer.Exit(1)
        with open(from_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                users.append(line)
    if not users:
        error("Provide at least one username (positional or --from-file).")
        raise typer.Exit(1)
    # dedupe, preserve order
    seen: set[str] = set()
    out: List[str] = []
    for u in users:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


@app.command(name="disable", help="Disable many users at once")
def bulk_disable_cmd(
    usernames: List[str] = typer.Argument(..., help="Usernames to disable"),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f", help="Read usernames from a file (one per line)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    names = _resolve_usernames(usernames, from_file)
    if not yes:
        confirmed = typer.confirm(
            f"Disable {len(names)} user(s) on the panel?", default=False
        )
        if not confirmed:
            raise typer.Abort()
    sys.exit(asyncio.run(_run(names, enable=False)))


@app.command(name="enable", help="Re-enable many users at once")
def bulk_enable_cmd(
    usernames: List[str] = typer.Argument(..., help="Usernames to enable"),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f", help="Read usernames from a file (one per line)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    names = _resolve_usernames(usernames, from_file)
    if not yes:
        confirmed = typer.confirm(
            f"Enable {len(names)} user(s) on the panel?", default=False
        )
        if not confirmed:
            raise typer.Abort()
    sys.exit(asyncio.run(_run(names, enable=True)))
