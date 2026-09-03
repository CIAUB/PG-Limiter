"""
Reusable retry helpers for the PasarGuard panel API.

# Modified/Added by CIAUB, 2026-09-03 — part of PasarGuard 5.3.0+
# compatibility fork.
# Licensed under AGPLv3 — see LICENSE.

This module centralises the retry behaviour that was previously
duplicated across `auth.py`, `users.py`, `nodes.py`, etc.

It exposes:

- `RetryPolicy` — dataclass with backoff/jitter settings.
- `async_retry` — decorator that retries an async callable on the given
  exceptions, with exponential backoff + jitter, and gives up after
  `max_attempts` tries.
- `Retry-After` helper that honours `response.headers.get("Retry-After")`
  when the panel tells us to back off.

The retry decorator is intentionally small and framework-free so it can
be reused anywhere (panel calls, downstream HTTP, etc.) without
introducing a new dependency.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable, Optional, Tuple, Type, TypeVar

from utils.logs import get_logger

# Module logger — reuses the existing log plumbing.
retry_logger = get_logger("panel_api.retry")


T = TypeVar("T")


# ─────────────────────────────────────────────────────────────────────────────
# Policy
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RetryPolicy:
    """
    Backoff configuration.

    Defaults match the legacy behaviour in `auth.py`:
      wait = min(max_wait, base * factor ** attempt) + jitter

    Attributes:
        max_attempts: Total tries before raising the last exception.
        base_delay:   Initial delay (seconds) before the first retry.
        max_delay:    Upper bound on the backoff delay (seconds).
        factor:       Multiplier applied each attempt (default 2.0).
        jitter:       Random jitter added to each delay (seconds).
        retry_on:     Tuple of exception classes to retry on. Anything else
                      propagates immediately.
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    factor: float = 2.0
    jitter: float = 0.5
    retry_on: Tuple[Type[BaseException], ...] = (Exception,)


def _compute_delay(policy: RetryPolicy, attempt: int) -> float:
    """Return the delay (seconds) for the given 0-based attempt number."""
    raw = policy.base_delay * (policy.factor ** attempt)
    capped = min(policy.max_delay, raw)
    # Avoid 0-delay tight loops if jitter is set to 0.
    return max(0.0, capped + random.uniform(0, policy.jitter))


# ─────────────────────────────────────────────────────────────────────────────
# Decorator
# ─────────────────────────────────────────────────────────────────────────────

def async_retry(
    policy: Optional[RetryPolicy] = None,
    *,
    log_prefix: str = "",
    on_retry: Optional[Callable[[int, BaseException, float], Awaitable[None]]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator that retries an async callable with exponential backoff + jitter.

    Args:
        policy:     RetryPolicy to use (defaults to `RetryPolicy()`).
        log_prefix: Prepended to log lines (e.g. "🔑 token fetch").
        on_retry:   Optional async callback fired on every retry with
                    (attempt, exception, next_delay).
    """
    if policy is None:
        policy = RetryPolicy()

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Optional[BaseException] = None
            for attempt in range(policy.max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except policy.retry_on as exc:  # type: ignore[misc]
                    last_exc = exc
                    if attempt + 1 >= policy.max_attempts:
                        retry_logger.error(
                            "%s giving up after %d attempt(s): %s",
                            log_prefix or fn.__name__,
                            policy.max_attempts,
                            exc,
                        )
                        raise

                    delay = _compute_delay(policy, attempt)
                    retry_logger.warning(
                        "%s attempt %d/%d failed (%s); retrying in %.1fs",
                        log_prefix or fn.__name__,
                        attempt + 1,
                        policy.max_attempts,
                        type(exc).__name__,
                        delay,
                    )
                    if on_retry is not None:
                        try:
                            await on_retry(attempt, exc, delay)
                        except Exception:  # never let callback break the loop
                            retry_logger.debug("on_retry callback raised", exc_info=True)
                    await asyncio.sleep(delay)
            # Unreachable, but type-checkers like the explicit raise.
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# Retry-After helper
# ─────────────────────────────────────────────────────────────────────────────

def parse_retry_after(value: Optional[str], fallback: float) -> float:
    """
    Parse a `Retry-After` header value into seconds.

    The HTTP spec allows either a delta-seconds integer or an HTTP date.
    We only handle the simple integer form here (panel doesn't emit dates).
    """
    if not value:
        return fallback
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return fallback


def is_retryable_status(status_code: int) -> bool:
    """
    Default classification of HTTP statuses worth retrying.

    - 408: request timeout
    - 425: too early (rare, but harmless to retry)
    - 429: rate limited
    - 500/502/503/504: transient server errors
    """
    return status_code in (408, 425, 429, 500, 502, 503, 504)


def is_terminal_status(status_code: int) -> bool:
    """
    HTTP statuses that should NOT be retried (e.g. auth, permission, not-found).
    """
    return status_code in (400, 401, 403, 404, 409, 410, 422)
