# =============================================================================
# Request identity — matches POST /post/set-status: X-User-Id in tests; session
# via Flask-Login in the browser for HTML + AJAX.
# =============================================================================
from __future__ import annotations

from flask import request
from flask_login import current_user


def effective_user_id() -> int | None:
    """Return the acting user id, or None if the request is anonymous."""
    raw = request.headers.get("X-User-Id", "").strip()
    if raw.isdigit():
        return int(raw)
    if current_user.is_authenticated:
        return int(current_user.get_id())
    return None
