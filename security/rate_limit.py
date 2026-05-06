# ===========================================================================
# Login rate limiting helpers
# ===========================================================================
from __future__ import annotations

import os
import time
from dataclasses import dataclass

ENV_LOGIN_RATE_LIMIT_ENABLED = "LOGIN_RATE_LIMIT_ENABLED"
ENV_LOGIN_RATE_LIMIT_MAX_ATTEMPTS = "LOGIN_RATE_LIMIT_MAX_ATTEMPTS"
ENV_LOGIN_RATE_LIMIT_WINDOW_SECONDS = "LOGIN_RATE_LIMIT_WINDOW_SECONDS"

DEFAULT_LOGIN_RATE_LIMIT_ENABLED = True
DEFAULT_LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 5
DEFAULT_LOGIN_RATE_LIMIT_WINDOW_SECONDS = 10 * 60


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0
    attempts_remaining: int = 0


def _truthy(value: object | None, *, default: bool = False) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _positive_int(value: object | None, *, default: int) -> int:
    if value is None:
        return default

    try:
        out = int(str(value).strip())
    except (TypeError, ValueError):
        return default

    return out if out > 0 else default


def login_rate_limit_enabled(app) -> bool:
    configured = app.config.get(ENV_LOGIN_RATE_LIMIT_ENABLED)

    if configured is not None:
        return _truthy(configured, default=DEFAULT_LOGIN_RATE_LIMIT_ENABLED)

    return _truthy(
        os.environ.get(ENV_LOGIN_RATE_LIMIT_ENABLED),
        default=DEFAULT_LOGIN_RATE_LIMIT_ENABLED,
    )


def login_rate_limit_max_attempts(app) -> int:
    configured = app.config.get(ENV_LOGIN_RATE_LIMIT_MAX_ATTEMPTS)

    if configured is not None:
        return _positive_int(
            configured,
            default=DEFAULT_LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        )

    return _positive_int(
        os.environ.get(ENV_LOGIN_RATE_LIMIT_MAX_ATTEMPTS),
        default=DEFAULT_LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    )


def login_rate_limit_window_seconds(app) -> int:
    configured = app.config.get(ENV_LOGIN_RATE_LIMIT_WINDOW_SECONDS)

    if configured is not None:
        return _positive_int(
            configured,
            default=DEFAULT_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )

    return _positive_int(
        os.environ.get(ENV_LOGIN_RATE_LIMIT_WINDOW_SECONDS),
        default=DEFAULT_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )


def login_rate_limit_key(email: str, remote_addr: str | None) -> str:
    """Build a stable rate-limit bucket key for one IP/email pair."""
    normalised_email = (email or "").strip().lower()
    ip = (remote_addr or "unknown").strip().lower()
    return f"{ip}:{normalised_email}"


class InMemoryLoginRateLimiter:
    """Small process-local limiter for login attempts.

    This is sufficient for the coursework app and local tests. A production
    deployment with multiple workers should replace this with a shared store.
    """

    def __init__(self) -> None:
        self._failures: dict[str, list[float]] = {}

    def check(self, key: str, *, max_attempts: int, window_seconds: int) -> RateLimitResult:
        now = time.time()
        attempts = self._pruned_attempts(key, now=now, window_seconds=window_seconds)

        if len(attempts) >= max_attempts:
            oldest = attempts[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=retry_after,
                attempts_remaining=0,
            )

        return RateLimitResult(
            allowed=True,
            retry_after_seconds=0,
            attempts_remaining=max(0, max_attempts - len(attempts)),
        )

    def record_failure(
        self,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
    ) -> RateLimitResult:
        now = time.time()
        attempts = self._pruned_attempts(key, now=now, window_seconds=window_seconds)
        attempts.append(now)
        self._failures[key] = attempts

        return self.check(
            key,
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def clear(self) -> None:
        self._failures.clear()

    def _pruned_attempts(
        self,
        key: str,
        *,
        now: float,
        window_seconds: int,
    ) -> list[float]:
        cutoff = now - window_seconds
        attempts = [ts for ts in self._failures.get(key, []) if ts >= cutoff]

        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)

        return attempts


default_login_rate_limiter = InMemoryLoginRateLimiter()


def reset_default_login_rate_limiter() -> None:
    default_login_rate_limiter.clear()