# =============================================================================
# Blueprint: auth  —  login, registration, email verification (stub views)
# =============================================================================
# Migrated from monolithic app.py in refactor sprint. Owns everything under
# /auth for human-readable URLs; JSON exchange endpoints may live under
# /api in a later sub-blueprint.
# =============================================================================
from __future__ import annotations

from flask import Blueprint, render_template_string, request

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.get("/login")
def login_form():
    """Placeholder until templates ship from the pages/ directory."""
    return (
        render_template_string("<!doctype html><title>login</title><p>auth/login stub</p>"),
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


@bp.post("/login")
def login_submit():
    return {"ok": False, "reason": "not_implemented"}, 501


@bp.get("/register")
def register_form():
    return (
        render_template_string("<!doctype html><title>register</title><p>auth/register stub</p>"),
        200,
    )


@bp.post("/register")
def register_submit():
    return {"ok": False}, 501


@bp.get("/logout")
def logout():
    return {"ok": True}, 200


@bp.get("/verify/<token>")
def verify_email_token(token: str):
    # Token validation is handled in auth/email_verification; wire later
    if not token:
        return {"ok": False}, 400
    return {"ok": True, "token": token[:8]}, 200


# -----------------------------------------------------------------------------
# Health / internal — remove or protect before production
# -----------------------------------------------------------------------------


@bp.get("/_ping")
def auth_ping():
    return {"module": "auth", "q": request.args.get("q", "")}, 200
