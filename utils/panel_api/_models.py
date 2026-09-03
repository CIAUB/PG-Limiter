"""
Typed response models for PasarGuard panel API (v5.x).

# Modified/Added by CIAUB, 2026-09-03 — part of PasarGuard 5.3.0+
# compatibility fork.
# Licensed under AGPLv3 — see LICENSE.

These dataclasses are *thin* parsers: they take a JSON dict and expose
attributes matching the PasarGuard OpenAPI spec. They're intentionally
loose (no Pydantic dependency) so the code base stays light.

The PasarGuard panel `app/models/*.py` defines the canonical shapes;
this module is a subset that the limiter actually consumes.

Reference: https://github.com/PasarGuard/panel (main branch)

Why dataclasses rather than pydantic:
- Avoid pulling another dependency.
- Match the style of `utils/types.py` (also dataclasses).
- Provide a single source of truth for the JSON keys we read.

When PasarGuard adds or renames a field, this is the only place to
update (plus the corresponding helper in `users.py` etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _opt_int(v: Any) -> Optional[int]:
    """Coerce to int if not None, else None."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _opt_str(v: Any) -> Optional[str]:
    return str(v) if v is not None else None


# ─────────────────────────────────────────────────────────────────────────────
# Admin (lightweight)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AdminContact:
    """Subset of `app.models.admin.AdminContactInfo`."""

    username: Optional[str] = None
    id: Optional[int] = None

    @classmethod
    def from_json(cls, data: Any) -> "AdminContact":
        if not isinstance(data, dict):
            return cls()
        return cls(
            username=_opt_str(data.get("username")),
            id=_opt_int(data.get("id")),
        )


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UserResponse:
    """
    Subset of `app.models.user.UserResponse` (v5.3.0).

    All fields are optional because the panel may omit some depending on
    the caller's permissions. Unknown fields in the input are ignored.
    """

    username: str = ""
    id: Optional[int] = None
    status: Optional[str] = None
    used_traffic: Optional[int] = None
    lifetime_used_traffic: Optional[int] = None
    data_limit: Optional[int] = None
    data_limit_reset_strategy: Optional[str] = None
    expire: Optional[int] = None  # 0 = unlimited, None = unchanged
    online_at: Optional[str] = None
    created_at: Optional[str] = None
    edit_at: Optional[str] = None
    subscription_url: Optional[str] = None
    note: Optional[str] = None
    on_hold_timeout: Optional[int] = None
    on_hold_expire_duration: Optional[int] = None
    auto_delete_in_days: Optional[int] = None
    hwid_limit: Optional[int] = None
    group_ids: List[int] = field(default_factory=list)
    group_names: List[str] = field(default_factory=list)
    admin: Optional[AdminContact] = None
    # Raw passthrough for fields we don't explicitly model yet
    # (e.g. `proxy_settings`, `next_plan`). Kept as `dict` for forward compat.
    proxy_settings: Optional[Dict[str, Any]] = None
    next_plan: Optional[Dict[str, Any]] = None

    @classmethod
    def from_json(cls, data: Any) -> "UserResponse":
        if not isinstance(data, dict):
            return cls()
        admin_raw = data.get("admin")
        return cls(
            username=_opt_str(data.get("username")) or "",
            id=_opt_int(data.get("id")),
            status=_opt_str(data.get("status")),
            used_traffic=_opt_int(data.get("used_traffic")),
            lifetime_used_traffic=_opt_int(data.get("lifetime_used_traffic")),
            data_limit=_opt_int(data.get("data_limit")),
            data_limit_reset_strategy=_opt_str(data.get("data_limit_reset_strategy")),
            expire=_opt_int(data.get("expire")),
            online_at=_opt_str(data.get("online_at")),
            created_at=_opt_str(data.get("created_at")),
            edit_at=_opt_str(data.get("edit_at")),
            subscription_url=_opt_str(data.get("subscription_url")),
            note=_opt_str(data.get("note")),
            on_hold_timeout=_opt_int(data.get("on_hold_timeout")),
            on_hold_expire_duration=_opt_int(data.get("on_hold_expire_duration")),
            auto_delete_in_days=_opt_int(data.get("auto_delete_in_days")),
            hwid_limit=_opt_int(data.get("hwid_limit")),
            group_ids=list(data.get("group_ids") or []),
            group_names=list(data.get("group_names") or []),
            admin=AdminContact.from_json(admin_raw),
            proxy_settings=data.get("proxy_settings"),
            next_plan=data.get("next_plan"),
        )

    def admin_username(self) -> Optional[str]:
        return self.admin.username if self.admin else None


@dataclass
class UserSimple:
    """
    Subset of `app.models.user.UserSimple` — lightweight {id, username}.
    """

    id: int
    username: str

    @classmethod
    def from_json(cls, data: Any) -> Optional["UserSimple"]:
        if not isinstance(data, dict):
            return None
        username = _opt_str(data.get("username"))
        if not username:
            return None
        return cls(id=_opt_int(data.get("id")) or 0, username=username)


# ─────────────────────────────────────────────────────────────────────────────
# Users list
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UsersResponse:
    users: List[UserResponse] = field(default_factory=list)
    total: int = 0

    @classmethod
    def from_json(cls, data: Any) -> "UsersResponse":
        if not isinstance(data, dict):
            return cls()
        raw_users = data.get("users") or []
        users = [UserResponse.from_json(u) for u in raw_users if isinstance(u, dict)]
        total = _opt_int(data.get("total"))
        return cls(users=users, total=total if total is not None else len(users))


@dataclass
class UsersSimpleResponse:
    users: List[UserSimple] = field(default_factory=list)
    total: int = 0

    @classmethod
    def from_json(cls, data: Any) -> "UsersSimpleResponse":
        if not isinstance(data, dict):
            return cls()
        raw_users = data.get("users") or []
        users = []
        for u in raw_users:
            parsed = UserSimple.from_json(u)
            if parsed is not None:
                users.append(parsed)
        total = _opt_int(data.get("total"))
        return cls(users=users, total=total if total is not None else len(users))


# ─────────────────────────────────────────────────────────────────────────────
# Nodes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class NodeResponse:
    """Subset of `app.models.node.NodeResponse`."""

    id: int = 0
    name: str = ""
    address: str = ""
    port: Optional[int] = None
    status: str = "unknown"
    message: Optional[str] = None
    enabled: bool = True

    @classmethod
    def from_json(cls, data: Any) -> Optional["NodeResponse"]:
        if not isinstance(data, dict):
            return None
        nid = _opt_int(data.get("id"))
        if nid is None:
            return None
        return cls(
            id=nid,
            name=_opt_str(data.get("name")) or "",
            address=_opt_str(data.get("address")) or "",
            port=_opt_int(data.get("port")),
            status=_opt_str(data.get("status")) or "unknown",
            message=_opt_str(data.get("message")),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class NodesResponse:
    nodes: List[NodeResponse] = field(default_factory=list)
    total: int = 0

    @classmethod
    def from_json(cls, data: Any) -> "NodesResponse":
        # The panel historically returned either a bare list or
        # `{"nodes": [...], "total": N}`. Support both for safety.
        if isinstance(data, list):
            raw = data
            total = len(raw)
        elif isinstance(data, dict):
            raw = data.get("nodes") or data.get("data") or []
            total = _opt_int(data.get("total")) or len(raw)
        else:
            raw = []
            total = 0
        nodes = []
        for item in raw:
            parsed = NodeResponse.from_json(item)
            if parsed is not None:
                nodes.append(parsed)
        return cls(nodes=nodes, total=total)


# ─────────────────────────────────────────────────────────────────────────────
# Groups
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GroupResponse:
    """Subset of `app.models.group.GroupResponse`."""

    id: int = 0
    name: str = ""
    inbound_tags: List[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: Any) -> Optional["GroupResponse"]:
        if not isinstance(data, dict):
            return None
        gid = _opt_int(data.get("id"))
        if gid is None:
            return None
        return cls(
            id=gid,
            name=_opt_str(data.get("name")) or "",
            inbound_tags=list(data.get("inbound_tags") or []),
        )


@dataclass
class GroupsResponse:
    groups: List[GroupResponse] = field(default_factory=list)
    total: int = 0

    @classmethod
    def from_json(cls, data: Any) -> "GroupsResponse":
        if isinstance(data, list):
            raw = data
            total = len(raw)
        elif isinstance(data, dict):
            raw = data.get("groups") or data.get("data") or []
            total = _opt_int(data.get("total")) or len(raw)
        else:
            raw = []
            total = 0
        groups = []
        for item in raw:
            parsed = GroupResponse.from_json(item)
            if parsed is not None:
                groups.append(parsed)
        return cls(groups=groups, total=total)


# ─────────────────────────────────────────────────────────────────────────────
# Admins
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AdminSummary:
    username: str = ""
    id: Optional[int] = None
    is_sudo: bool = False
    is_disabled: bool = False
    telegram_id: Optional[int] = None

    @classmethod
    def from_json(cls, data: Any) -> Optional["AdminSummary"]:
        if not isinstance(data, dict):
            return None
        username = _opt_str(data.get("username"))
        if not username:
            return None
        return cls(
            username=username,
            id=_opt_int(data.get("id")),
            is_sudo=bool(data.get("is_sudo", False)),
            is_disabled=bool(data.get("is_disabled", False)),
            telegram_id=_opt_int(data.get("telegram_id")),
        )


@dataclass
class AdminsResponse:
    admins: List[AdminSummary] = field(default_factory=list)
    total: int = 0

    @classmethod
    def from_json(cls, data: Any) -> "AdminsResponse":
        if isinstance(data, list):
            raw = data
            total = len(raw)
        elif isinstance(data, dict):
            raw = data.get("admins") or data.get("data") or []
            total = _opt_int(data.get("total")) or len(raw)
        else:
            raw = []
            total = 0
        admins = []
        for item in raw:
            parsed = AdminSummary.from_json(item)
            if parsed is not None:
                admins.append(parsed)
        return cls(admins=admins, total=total)
