# =============================================================================
# Browser security response headers
# =============================================================================
from __future__ import annotations

import os

from flask import Response

ENV_SECURITY_HSTS_ENABLED = "SECURITY_HSTS_ENABLED"

SECURITY_HEADER_CSP = "Content-Security-Policy"
SECURITY_HEADER_CONTENT_TYPE_OPTIONS = "X-Content-Type-Options"
SECURITY_HEADER_FRAME_OPTIONS = "X-Frame-Options"
SECURITY_HEADER_REFERRER_POLICY = "Referrer-Policy"
SECURITY_HEADER_PERMISSIONS_POLICY = "Permissions-Policy"
SECURITY_HEADER_HSTS = "Strict-Transport-Security"

DEFAULT_REFERRER_POLICY = "strict-origin-when-cross-origin"
DEFAULT_FRAME_OPTIONS = "DENY"
DEFAULT_CONTENT_TYPE_OPTIONS = "nosniff"
DEFAULT_PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=()"
DEFAULT_HSTS_VALUE = "max-age=31536000; includeSubDomains"

DEFAULT_CSP_DIRECTIVES: tuple[str, ...] = (
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "img-src 'self' data:",
    "connect-src 'self'",
    "font-src 'self' https://cdn.jsdelivr.net data:",
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'",
    "script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com",
)


def _truthy(value: object | None, *, default: bool = False) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def build_content_security_policy() -> str:
    """Return the project CSP as a single header value."""
    return "; ".join(DEFAULT_CSP_DIRECTIVES)


def _hsts_enabled(app) -> bool:
    configured = app.config.get(ENV_SECURITY_HSTS_ENABLED)

    if configured is not None:
        return _truthy(configured)

    return _truthy(os.environ.get(ENV_SECURITY_HSTS_ENABLED), default=False)


def apply_security_headers(response: Response, app) -> Response:
    """Attach standard browser security headers to one response."""
    response.headers.setdefault(SECURITY_HEADER_CSP, build_content_security_policy())
    response.headers.setdefault(
        SECURITY_HEADER_CONTENT_TYPE_OPTIONS,
        DEFAULT_CONTENT_TYPE_OPTIONS,
    )
    response.headers.setdefault(SECURITY_HEADER_FRAME_OPTIONS, DEFAULT_FRAME_OPTIONS)
    response.headers.setdefault(SECURITY_HEADER_REFERRER_POLICY, DEFAULT_REFERRER_POLICY)
    response.headers.setdefault(
        SECURITY_HEADER_PERMISSIONS_POLICY,
        DEFAULT_PERMISSIONS_POLICY,
    )

    if _hsts_enabled(app):
        response.headers.setdefault(SECURITY_HEADER_HSTS, DEFAULT_HSTS_VALUE)

    return response


def init_security_headers(app) -> None:
    """Register after-request security headers for the Flask app."""
    app.config.setdefault(ENV_SECURITY_HSTS_ENABLED, False)

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        return apply_security_headers(response, app)