"""
Bulk operations against the PasarGuard panel API.

# Modified/Added by CIAUB, 2026-09-03 — part of PasarGuard 5.3.0+
# compatibility fork.
# Licensed under AGPLv3 — see LICENSE.

The panel v5.x exposes native bulk endpoints under `/api/users/bulk/*`
(add, remove, delete, disable, enable). This module wraps those,
falling back to per-user PUT when the bulk endpoint isn't available
or the call fails.

All operations are async and bounded by a configurable semaphore so we
don't accidentally fan out hundreds of concurrent requests.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from utils.logs import get_logger, log_user_action
from utils.panel_api.auth import invalidate_token_cache
from utils.panel_api.request_helper import (
    panel_get,
    panel_post,
    panel_request,
    _get_token_for_request,
)
from utils.types import PanelType
from utils.panel_api._retry import (
    RetryPolicy,
    async_retry,
    is_retryable_status,
    parse_retry_after,
)

bulk_logger = get_logger("panel_api.bulk")


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BulkResult:
    """Per-username outcome of a bulk operation."""

    succeeded: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    not_found: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "succeeded": list(self.succeeded),
            "failed": list(self.failed),
            "not_found": list(self.not_found),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Bulk disable
# ─────────────────────────────────────────────────────────────────────────────

async def bulk_disable_users(
    panel_data: PanelType,
    usernames: Iterable[str],
    *,
    disabled_group_id: Optional[int] = None,
    concurrency: int = 8,
    timeout: float = 30.0,
) -> BulkResult:
    """
    Disable many users in parallel.

    If `disabled_group_id` is provided, users are moved into that group
    AND their status is set to `disabled` (matches the group-disable
    flow used elsewhere in the codebase). Otherwise only `status=disabled`
    is set.

    Tries the native `/api/users/bulk/disable` endpoint first (single
    request, faster, atomic from the panel's perspective). If the panel
    rejects the payload or returns an unexpected shape, falls back to
    per-user PUT.

    Args:
        panel_data: Panel connection info.
        usernames:  Iterable of usernames to disable.
        disabled_group_id: Optional target group for group-based disable.
        concurrency: Max parallel per-user PUTs in fallback mode.
        timeout:    Per-request timeout in seconds.

    Returns:
        BulkResult with `succeeded` / `failed` / `not_found` lists.
    """
    user_list = [u for u in {str(u) for u in usernames} if u]
    if not user_list:
        return BulkResult()

    bulk_logger.info(f"🚫 Bulk-disabling {len(user_list)} users...")
    result = BulkResult()

    # Try native bulk endpoint first.
    native_status = await _try_native_bulk_disable(
        panel_data, user_list, disabled_group_id, timeout
    )
    # native_status: True  = endpoint returned 2xx, all disabled
    #                 None  = endpoint not available (404/405), fall back
    #                 False = transient error, fall back
    if native_status is True:
        result.succeeded.extend(user_list)
        log_user_action(
            "BULK_DISABLE", ",".join(user_list), f"count={len(user_list)}", success=True
        )
        bulk_logger.info(f"✅ Bulk-disabled {len(user_list)} users via /api/users/bulk/disable")
        return result

    # Fall back to per-user PUT.
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [
        _disable_one(panel_data, username, disabled_group_id, sem, timeout, result)
        for username in user_list
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    bulk_logger.info(
        f"✅ Bulk-disable done: {len(result.succeeded)} ok, "
        f"{len(result.failed)} failed, {len(result.not_found)} missing"
    )
    return result


async def _try_native_bulk_disable(
    panel_data: PanelType,
    usernames: List[str],
    disabled_group_id: Optional[int],
    timeout: float,
) -> Optional[bool]:
    """
    Try the native `/api/users/bulk/disable` endpoint.

    Returns:
        True  -> call succeeded (the panel disabled them all)
        False -> endpoint returned 4xx/5xx we can't recover from, fall back
        None  -> endpoint isn't available in this panel version
    """
    token = await _get_token_for_request(panel_data)
    if not token:
        return False

    payload: dict = {"usernames": usernames}
    if disabled_group_id is not None:
        payload["group_ids"] = [disabled_group_id]

    response, error = await panel_request(
        panel_data,
        "POST",
        "/api/users/bulk/disable",
        token=token,
        json_data=payload,
        timeout=timeout,
        max_retries=2,
    )

    if response is None:
        bulk_logger.debug(f"Native bulk disable failed: {error}")
        return False

    if response.status_code in (200, 201):
        return True
    if response.status_code == 404:
        bulk_logger.debug("Native /api/users/bulk/disable not available (404)")
        return None
    if response.status_code == 401:
        await invalidate_token_cache()
        return False
    if response.status_code == 405:
        bulk_logger.debug("Native /api/users/bulk/disable not allowed (405)")
        return None
    # Other 4xx: payload rejected; fall back.
    bulk_logger.warning(
        f"Native bulk disable returned {response.status_code}; falling back to per-user"
    )
    return False


async def _disable_one(
    panel_data: PanelType,
    username: str,
    disabled_group_id: Optional[int],
    sem: asyncio.Semaphore,
    timeout: float,
    result: BulkResult,
) -> None:
    async with sem:
        token = await _get_token_for_request(panel_data)
        if not token:
            result.failed.append(username)
            return

        payload: dict = {"status": "disabled"}
        if disabled_group_id is not None:
            payload["group_ids"] = [disabled_group_id]

        response, error = await panel_request(
            panel_data,
            "PUT",
            f"/api/user/{username}",
            token=token,
            json_data=payload,
            timeout=timeout,
            max_retries=3,
        )

        if response is None:
            bulk_logger.warning(f"Disable {username}: {error}")
            result.failed.append(username)
            return

        if response.status_code in (200, 201):
            result.succeeded.append(username)
        elif response.status_code == 404:
            result.not_found.append(username)
        elif response.status_code == 401:
            result.failed.append(username)
        else:
            bulk_logger.warning(
                f"Disable {username}: HTTP {response.status_code} {response.text[:80]}"
            )
            result.failed.append(username)


# ─────────────────────────────────────────────────────────────────────────────
# Bulk enable
# ─────────────────────────────────────────────────────────────────────────────

async def bulk_enable_users(
    panel_data: PanelType,
    usernames: Iterable[str],
    *,
    group_ids: Optional[List[int]] = None,
    concurrency: int = 8,
    timeout: float = 30.0,
) -> BulkResult:
    """
    Enable many users in parallel.

    Restores the user's original `group_ids` (if provided) and sets
    status to `active`.

    Tries `/api/users/bulk/enable` first; falls back to per-user PUT.
    """
    user_list = [u for u in {str(u) for u in usernames} if u]
    if not user_list:
        return BulkResult()

    bulk_logger.info(f"✅ Bulk-enabling {len(user_list)} users...")
    result = BulkResult()

    native_status = await _try_native_bulk_enable(
        panel_data, user_list, group_ids, timeout
    )
    # native_status: True  = endpoint returned 2xx, all enabled
    #                 None  = endpoint not available (404/405), fall back
    #                 False = transient error, fall back
    if native_status is True:
        result.succeeded.extend(user_list)
        log_user_action(
            "BULK_ENABLE", ",".join(user_list), f"count={len(user_list)}", success=True
        )
        bulk_logger.info(f"✅ Bulk-enabled {len(user_list)} users via /api/users/bulk/enable")
        return result

    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [
        _enable_one(panel_data, username, group_ids, sem, timeout, result)
        for username in user_list
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    bulk_logger.info(
        f"✅ Bulk-enable done: {len(result.succeeded)} ok, "
        f"{len(result.failed)} failed, {len(result.not_found)} missing"
    )
    return result


async def _try_native_bulk_enable(
    panel_data: PanelType,
    usernames: List[str],
    group_ids: Optional[List[int]],
    timeout: float,
) -> Optional[bool]:
    token = await _get_token_for_request(panel_data)
    if not token:
        return False

    payload: dict = {"usernames": usernames}
    if group_ids is not None:
        payload["group_ids"] = group_ids

    response, error = await panel_request(
        panel_data,
        "POST",
        "/api/users/bulk/enable",
        token=token,
        json_data=payload,
        timeout=timeout,
        max_retries=2,
    )

    if response is None:
        bulk_logger.debug(f"Native bulk enable failed: {error}")
        return False

    if response.status_code in (200, 201):
        return True
    if response.status_code in (404, 405):
        bulk_logger.debug(f"Native /api/users/bulk/enable not available ({response.status_code})")
        return None
    if response.status_code == 401:
        await invalidate_token_cache()
        return False
    bulk_logger.warning(
        f"Native bulk enable returned {response.status_code}; falling back to per-user"
    )
    return False


async def _enable_one(
    panel_data: PanelType,
    username: str,
    group_ids: Optional[List[int]],
    sem: asyncio.Semaphore,
    timeout: float,
    result: BulkResult,
) -> None:
    async with sem:
        token = await _get_token_for_request(panel_data)
        if not token:
            result.failed.append(username)
            return

        payload: dict = {"status": "active"}
        if group_ids is not None:
            payload["group_ids"] = group_ids

        response, error = await panel_request(
            panel_data,
            "PUT",
            f"/api/user/{username}",
            token=token,
            json_data=payload,
            timeout=timeout,
            max_retries=3,
        )

        if response is None:
            bulk_logger.warning(f"Enable {username}: {error}")
            result.failed.append(username)
            return
        if response.status_code in (200, 201):
            result.succeeded.append(username)
        elif response.status_code == 404:
            result.not_found.append(username)
        elif response.status_code == 401:
            result.failed.append(username)
        else:
            bulk_logger.warning(
                f"Enable {username}: HTTP {response.status_code} {response.text[:80]}"
            )
            result.failed.append(username)


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: bulk user-details fetch (for dashboard warmup, etc.)
# ─────────────────────────────────────────────────────────────────────────────

async def get_user_details_batch(
    panel_data: PanelType,
    usernames: List[str],
    *,
    concurrency: int = 10,
    timeout: float = 10.0,
    on_missing: bool = True,
) -> List[dict]:
    """
    Fetch full user details for many usernames in parallel.

    Returns a list of raw JSON dicts (one per existing user). Missing
    users are silently dropped unless `on_missing` is False (in which
    case they appear as `None` in the output list).

    Uses `/api/user/{username}` (canonical) rather than `/api/user/by-id/`.
    """
    if not usernames:
        return []

    sem = asyncio.Semaphore(max(1, concurrency))

    async def _fetch(name: str):
        async with sem:
            return await panel_get(
                panel_data,
                f"/api/user/{name}",
                timeout=timeout,
                max_retries=2,
            )

    responses = await asyncio.gather(*[_fetch(u) for u in usernames], return_exceptions=True)

    out: List[dict] = []
    for username, resp in zip(usernames, responses):
        if isinstance(resp, Exception):
            bulk_logger.debug(f"get_user_details_batch: {username} raised {resp}")
            if not on_missing:
                out.append(None)  # type: ignore[arg-type]
            continue
        if resp is None:
            if not on_missing:
                out.append(None)  # type: ignore[arg-type]
            continue
        if resp.status_code == 200:
            try:
                out.append(resp.json())
            except Exception as e:  # noqa: BLE001
                bulk_logger.debug(f"get_user_details_batch: parse error for {username}: {e}")
        elif resp.status_code == 404:
            if not on_missing:
                out.append(None)  # type: ignore[arg-type]
        else:
            bulk_logger.debug(
                f"get_user_details_batch: {username} -> {resp.status_code}"
            )
            if not on_missing:
                out.append(None)  # type: ignore[arg-type]
    return out
