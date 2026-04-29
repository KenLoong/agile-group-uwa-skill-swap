# =============================================================================
# Blueprint: auth  —  login, registration, email verification (stub views)
# =============================================================================
# Migrated from monolithic app.py in refactor sprint. Owns everything under
# /auth for human-readable URLs; JSON exchange endpoints may live under
# /api in a later sub-blueprint.
# =============================================================================
from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, render_template_string, request
from flask_login import login_user

from api.tags_models import User, db

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


@bp.post("/test-login")
def test_login_for_automated_clients():
    """Establish a Flask-Login session for browser tests — disabled outside TESTING."""
    if not current_app.config.get("TESTING"):
        abort(404)
    data = request.get_json(silent=True) or {}
    uid_raw = data.get("user_id")
    if uid_raw is None:
        return jsonify({"ok": False, "message": "user_id required"}), 400
    if isinstance(uid_raw, str) and uid_raw.strip().isdigit():
        uid = int(uid_raw.strip())
    elif isinstance(uid_raw, int):
        uid = uid_raw
    else:
        return jsonify({"ok": False, "message": "invalid user_id"}), 400

    user = db.session.get(User, uid)
    if user is None:
        return jsonify({"ok": False, "message": "user not found"}), 404

    login_user(user)
    return jsonify({"ok": True})


@bp.get("/_ping")
def auth_ping():
    return {"module": "auth", "q": request.args.get("q", "")}, 200
