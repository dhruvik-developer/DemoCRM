"""
Login rate limiter backed by Django cache (Redis).

Strategy (Time + Admin unlock):
  1. After LOGIN_MAX_ATTEMPTS consecutive failures, the account enters a
     LOGIN_COOLDOWN_SECONDS window. During this window all login attempts
     are rejected.
  2. If the user fails AGAIN after the cooldown expires, the account is
     permanently locked until an Admin calls the unlock endpoint.
  3. A successful login resets all counters.

Cache keys (per email):
  login:attempts:<email>   – dict {count, first_failure_at}   TTL = cooldown * 2
  login:locked:<email>     – "1" (permanent lock)              TTL = 30 days
"""

import time

from django.conf import settings
from django.core.cache import cache

_PREFIX_ATTEMPTS = "login:attempts:"
_PREFIX_LOCKED = "login:locked:"


def _attempts_key(email: str) -> str:
    return f"{_PREFIX_ATTEMPTS}{email.lower()}"


def _locked_key(email: str) -> str:
    return f"{_PREFIX_LOCKED}{email.lower()}"


def _cooldown() -> int:
    return getattr(settings, "LOGIN_COOLDOWN_SECONDS", 600)


def _max_attempts() -> int:
    return getattr(settings, "LOGIN_MAX_ATTEMPTS", 5)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def is_locked(email: str) -> dict:
    """
    Check whether *email* is currently blocked.

    Returns:
        {"blocked": False}
        or {"blocked": True, "reason": "cooldown", "retry_after": <seconds>}
        or {"blocked": True, "reason": "permanent"}
    """
    # 1. Permanent lock (set by admin unlock clearing, or escalation)
    if cache.get(_locked_key(email)):
        return {"blocked": True, "reason": "permanent"}

    # 2. Cooldown window
    data = cache.get(_attempts_key(email))
    if data is None:
        return {"blocked": False}

    count = data.get("count", 0)
    first_failure = data.get("first_failure_at", 0)

    if count >= _max_attempts():
        elapsed = time.time() - first_failure
        remaining = _cooldown() - elapsed
        if remaining > 0:
            return {
                "blocked": True,
                "reason": "cooldown",
                "retry_after": int(remaining),
            }
        # Cooldown expired — but we do NOT auto-clear here.
        # The next failure will escalate to permanent lock (handled in record_failure).
        # A success will clear everything (handled in reset).

    return {"blocked": False}


def record_failure(email: str) -> dict:
    """
    Record a failed login for *email*.

    Returns the same shape as ``is_locked`` so the caller can immediately
    decide the response.
    """
    key = _attempts_key(email)
    data = cache.get(key)

    now = time.time()
    cooldown = _cooldown()
    max_attempts = _max_attempts()

    if data is None:
        # First failure
        cache.set(key, {"count": 1, "first_failure_at": now}, timeout=cooldown * 2)
        remaining = max_attempts - 1
        return {
            "blocked": False,
            "remaining_attempts": remaining,
        }

    count = data.get("count", 0)
    first_failure = data.get("first_failure_at", now)
    elapsed = now - first_failure

    if count >= max_attempts and elapsed >= cooldown:
        # Cooldown expired and user failed again → escalate to permanent lock
        cache.delete(key)
        cache.set(_locked_key(email), "1", timeout=60 * 60 * 24 * 30)  # 30 days
        return {"blocked": True, "reason": "permanent"}

    if elapsed >= cooldown:
        # Cooldown expired, this is a fresh failure window
        cache.set(key, {"count": 1, "first_failure_at": now}, timeout=cooldown * 2)
        remaining = max_attempts - 1
        return {"blocked": False, "remaining_attempts": remaining}

    # Still inside the cooldown window (or under max attempts)
    new_count = count + 1
    if new_count >= max_attempts:
        # Lock starts NOW
        cache.set(
            key,
            {"count": new_count, "first_failure_at": first_failure},
            timeout=cooldown * 2,
        )
        return {
            "blocked": True,
            "reason": "cooldown",
            "retry_after": cooldown,
        }

    cache.set(
        key,
        {"count": new_count, "first_failure_at": first_failure},
        timeout=cooldown * 2,
    )
    remaining = max_attempts - new_count
    return {"blocked": False, "remaining_attempts": remaining}


def reset(email: str) -> None:
    """Clear all rate-limit state for *email* (called on successful login)."""
    cache.delete(_attempts_key(email))
    cache.delete(_locked_key(email))


def unlock(email: str) -> None:
    """Admin unlock — clear permanent lock + any cooldown state."""
    cache.delete(_locked_key(email))
    cache.delete(_attempts_key(email))
