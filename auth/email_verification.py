# =============================================================================
# Email verification service — token lifecycle, resend policy, mail body build
# =============================================================================
#
# This module is the intended single entry point for:
#   - issuing a link after /register
#   - GET /auth/verify?token=…  (or similar route when Flask app is merged)
#   - POST /auth/resend-verification (authenticated or email-only, TBD)
#
# Persistence today: in-process dict for the demo branch; replace with
# SQLAlchemy `EmailVerificationToken` in the next milestone so workers share state.
#
# Security notes (for code review in agile coursework):
#   * Tokens are random + optionally HMAC’ed; never embed only user id in link.
#   * Log only hashes of tokens in application logs, not raw values.
#   * Short TTL and single-use (consume token on success) to limit replay.
#
# =============================================================================
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass, field
from email.utils import formatdate
from typing import Callable, Protocol

from auth.constants import (
    EMAIL_VERIFY_RESEND_COOLDOWN_HOURS,
    EMAIL_VERIFY_TOKEN_TTL_SECONDS,
    ENV_BASE_URL,
    ENV_EMAIL_FROM,
    ENV_SECRET_KEY,
)
from auth.exceptions import (
    MailDispatchError,
    ResendThrottledError,
    TokenExpiredError,
    TokenInvalidError,
    UserAlreadyVerifiedError,
    VerificationError,
)
from auth.mailer import DevConsoleMailer, OutgoingMessage, get_mailer

# Type alias for a future User model id (int) — kept loose until models.py lands.
UserId = int


class _UserLike(Protocol):
    id: UserId
    email: str
    email_confirmed: bool  # or email_verified_at: datetime | None


@dataclass
class VerificationTokenRecord:
    user_id: UserId
    email: str
    token_hash: str
    created_at: float
    expires_at: float
    consumed_at: float | None = None
    jti: str = field(default_factory=lambda: secrets.token_urlsafe(12))


# ---------------------------------------------------------------------------
# In-memory token table — NOT for multi-worker production; OK for the demo PR.
# ---------------------------------------------------------------------------


class _InMemoryTokenStore:
    def __init__(self) -> None:
        self._by_user: dict[UserId, list[VerificationTokenRecord]] = {}
        self._by_hash: dict[str, VerificationTokenRecord] = {}
        self._resend_map: dict[UserId, float] = {}

    def add(self, rec: VerificationTokenRecord) -> None:
        self._by_user.setdefault(rec.user_id, []).append(rec)
        self._by_hash[rec.token_hash] = rec

    def get_by_hash(self, h: str) -> VerificationTokenRecord | None:
        return self._by_hash.get(h)

    def mark_consumed(self, h: str) -> None:
        r = self._by_hash.get(h)
        if r:
            r.consumed_at = time.time()

    def last_resend_at(self, user_id: UserId) -> float | None:
        t = self._resend_map.get(user_id)
        return t

    def set_resend(self, user_id: UserId) -> None:
        self._resend_map[user_id] = time.time()

    def clear_for_user(self, user_id: UserId) -> None:
        for r in self._by_user.get(user_id, []):
            self._by_hash.pop(r.token_hash, None)
        self._by_user.pop(user_id, None)


_store_singleton = _InMemoryTokenStore()


def _app_secret() -> bytes:
    """Return the configured application secret for token signing/hashing.

    Email verification tokens must use the same secret as Flask sessions.
    There is intentionally no development fallback here: tests should set
    SECRET_KEY explicitly, and normal runtime should load it from the
    environment.
    """
    secret = None

    try:
        from flask import current_app, has_app_context

        if has_app_context():
            secret = current_app.config.get("SECRET_KEY")
    except RuntimeError:
        secret = None

    secret = secret or os.environ.get(ENV_SECRET_KEY)

    if not secret:
        raise RuntimeError(
            "SECRET_KEY must be set before issuing or verifying email tokens."
        )

    return str(secret).encode("utf-8")


def _hash_token(raw: str) -> str:
    return hashlib.sha256(_app_secret() + raw.encode("utf-8"), usedforsecurity=True).hexdigest()


def _sign_payload(user_id: UserId, raw_token: str) -> str:
    data = f"{user_id}|{raw_token}".encode()
    mac = hmac.new(_app_secret(), data, hashlib.sha256).hexdigest()[:32]
    return f"{raw_token}|{user_id}|{mac}"


def _parse_signed_payload(
    s: str,
) -> tuple[str, UserId, str] | None:
    parts = s.split("|", maxsplit=2)
    if len(parts) < 2:
        return None
    raw, uid = parts[0], int(parts[1]) if len(parts) > 1 else -1
    mac = parts[2] if len(parts) > 2 else ""
    if uid < 0:
        return None
    return raw, UserId(uid), mac


def _public_base() -> str:
    return (os.environ.get(ENV_BASE_URL) or "http://127.0.0.1:5000").rstrip("/")


class EmailVerificationService:
    """
    Orchestrates: token mint → mail render → send → (later) DB flag flip.

    `on_success` is injected for unit tests; production will call into User model.
    """

    def __init__(
        self,
        store: _InMemoryTokenStore,
        mailer: Callable[[], "DevConsoleMailer"] = get_mailer,
        token_ttl: int = EMAIL_VERIFY_TOKEN_TTL_SECONDS,
    ) -> None:
        self._store = store
        self._get_mailer = mailer
        self._token_ttl = token_ttl

    def issue_for_new_user(
        self,
        user: _UserLike,
    ) -> str:
        """
        Called right after a row is created in the `users` table. Returns
        the **opaque** public token (only used inside the link we email).
        """
        if user.email_confirmed:
            raise UserAlreadyVerifiedError("already verified")
        raw = secrets.token_urlsafe(32)
        t_hash = _hash_token(raw)
        now = time.time()
        rec = VerificationTokenRecord(
            user_id=user.id,
            email=user.email,
            token_hash=t_hash,
            created_at=now,
            expires_at=now + self._token_ttl,
        )
        self._store.add(rec)
        link = self._build_link(_sign_payload(user.id, raw), user)
        self._send_mail(user.email, link)
        self._store.set_resend(user.id)
        return raw

    def resend(
        self,
        user: _UserLike,
    ) -> str:
        if user.email_confirmed:
            raise UserAlreadyVerifiedError("already verified")
        last = self._store.last_resend_at(user.id)
        if last is not None:
            delta = time.time() - last
            if delta < EMAIL_VERIFY_RESEND_COOLDOWN_HOURS * 3600:
                raise ResendThrottledError("wait before re-requesting")
        return self.issue_for_new_user(user)

    def verify_and_consume(
        self,
        signed: str,
    ) -> UserId:
        """
        Validates signed payload, token hash, expiry, single use; returns user_id.
        """
        parsed = _parse_signed_payload(signed)
        if not parsed:
            raise TokenInvalidError("bad format")
        raw, uid, mac = parsed
        expect_mac = hmac.new(
            _app_secret(), f"{uid}|{raw}".encode(), hashlib.sha256
        ).hexdigest()[:32]
        if not hmac.compare_digest(expect_mac, mac):
            raise TokenInvalidError("bad mac")
        t_hash = _hash_token(raw)
        rec = self._store.get_by_hash(t_hash)
        if not rec:
            raise TokenInvalidError("unknown token")
        if rec.consumed_at is not None:
            raise TokenInvalidError("replayed")
        if time.time() > rec.expires_at:
            raise TokenExpiredError("expired")
        if rec.user_id != uid:
            raise TokenInvalidError("mismatch")
        self._store.mark_consumed(t_hash)
        return uid

    def _build_link(self, signed: str, user: _UserLike) -> str:
        from urllib.parse import quote

        b = _public_base()
        # Route name will be registered as auth.verify in Flask merge
        return f"{b}/auth/verify?token={quote(signed, safe='')}&uid={user.id}"

    def _send_mail(self, to: str, link: str) -> None:
        subject = "Confirm your UWA Skill-Swap account"
        version_line = f"Request-ID: {formatdate()}"
        text = _TEXT_TEMPLATE.format(
            to=to,
            link=link,
            from_addr=os.environ.get(ENV_EMAIL_FROM, "UWA Skill-Swap <no-reply@uwa.local>"),
            version_line=version_line,
        )
        html = _HTML_TEMPLATE.format(link=link, to=to, version_line=version_line)
        m = self._get_mailer()
        try:
            m.send(OutgoingMessage(to, subject, text, html))
        except OSError as e:
            raise MailDispatchError(str(e)) from e


# ---------------------------------------------------------------------------
# Mail templates (keep verbose for coursework; production uses Jinja2 files)
# ---------------------------------------------------------------------------

_TEXT_TEMPLATE = """
Hello,

Thanks for creating an UWA Skill-Swap account with {to}.

To confirm you control this UWA email address, open the link below. It is
valid for a limited time and can only be used once.

{link}

If you did not create this account, you can ignore this message.

{version_line}

— UWA Skill-Swap
""".strip()

_HTML_TEMPLATE = (
    """
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Confirm email</title></head>
<body style="font-family:system-ui,sans-serif;max-width:40rem">
  <p>Please confirm your UWA email for Skill-Swap:</p>
  <p><a href="{link}">{link}</a></p>
  <p style="color:#555;font-size:0.9em">To: {to} — {version_line}</p>
</body></html>
"""
).strip()


# Single shared instance for blueprints to import; swap store in unit tests
default_service = EmailVerificationService(_store_singleton)


def _smoke() -> None:
    """If run as `python -m auth.email_verification` — does not need Flask."""

    @dataclass
    class _Fake:
        id: int
        email: str
        email_confirmed: bool = False

    u = _Fake(1, "123456@student.uwa.edu.au", False)
    svc = EmailVerificationService(_InMemoryTokenStore())
    t = svc.issue_for_new_user(u)  # noqa: F841
    print("smoke: issued token, check stdout for DevConsole output")


if __name__ == "__main__":
    _smoke()
