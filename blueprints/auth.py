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
from werkzeug.security import generate_password_hash

from api.tags_models import User, db
from auth.email_verification import default_service
from auth.exceptions import (
    MailDispatchError,
    TokenExpiredError,
    TokenInvalidError,
    VerificationError,
)

bp = Blueprint("auth", __name__, url_prefix="/auth")

UWA_STUDENT_EMAIL_SUFFIX = "@student.uwa.edu.au"

def _request_data() -> dict[str, str]:
    if request.is_json:
        raw = request.get_json(silent=True) or {}
    else:
        raw = request.form

    return {str(k): str(v).strip() for k, v in raw.items() if v is not None}


def _normalise_username(data: dict[str, str], email: str) -> str:
    display_name = (
        data.get("display_name")
        or data.get("username")
        or email.split("@", 1)[0]
    )
    return display_name.strip()[:80]


def _validate_registration(
    data: dict[str, str],
) -> tuple[dict[str, str] | None, tuple[dict[str, object], int] | None]:
    email = (data.get("email") or "").lower().strip()
    password = data.get("password") or ""
    confirm = data.get("confirm_password") or data.get("confirm") or password

    errors: dict[str, list[str]] = {}

    if not email:
        errors.setdefault("email", []).append("Email is required.")
    elif not email.endswith(UWA_STUDENT_EMAIL_SUFFIX):
        errors.setdefault("email", []).append("Use a UWA student email address.")

    if not password:
        errors.setdefault("password", []).append("Password is required.")
    elif len(password) < 8:
        errors.setdefault("password", []).append(
            "Password must be at least 8 characters."
        )

    if password and confirm and password != confirm:
        errors.setdefault("confirm_password", []).append("Passwords do not match.")

    if errors:
        return None, (
            {
                "ok": False,
                "message": "Registration validation failed",
                "errors": errors,
            },
            400,
        )

    return {
        "email": email,
        "password": password,
        "username": _normalise_username(data, email),
    }, None

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
    data = _request_data()
    clean, error = _validate_registration(data)

    if error is not None:
        body, status = error
        return jsonify(body), status

    assert clean is not None

    if db.session.query(User.id).filter_by(email=clean["email"]).first() is not None:
        return jsonify({"ok": False, "message": "Email is already registered."}), 409

    if (
        clean["username"]
        and db.session.query(User.id).filter_by(username=clean["username"]).first()
        is not None
    ):
        return jsonify({"ok": False, "message": "Display name is already taken."}), 409

    user = User(
        email=clean["email"],
        username=clean["username"],
        password_hash=generate_password_hash(clean["password"]),
        email_confirmed=False,
    )
    db.session.add(user)

    try:
        db.session.flush()
        default_service.issue_for_new_user(user)
        db.session.commit()
    except MailDispatchError:
        db.session.rollback()
        return jsonify({"ok": False, "message": "Could not send verification email."}), 502
    except VerificationError as exc:
        db.session.rollback()
        return jsonify({"ok": False, "message": str(exc)}), 400

    return (
        jsonify(
            {
                "ok": True,
                "status": "verification_pending",
                "user_id": user.id,
                "email": user.email,
                "message": (
                    "Registration created. Check your UWA inbox for a "
                    "verification link."
                ),
            }
        ),
        201,
    )


@bp.get("/logout")
def logout():
    return {"ok": True}, 200


def _complete_email_verification(signed: str):
    if not signed:
        return jsonify({"ok": False, "message": "Verification token is required."}), 400

    try:
        user_id = default_service.verify_and_consume(signed)
    except TokenExpiredError:
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "expired",
                    "message": "Verification link expired.",
                }
            ),
            400,
        )
    except TokenInvalidError:
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "invalid",
                    "message": "Verification link is invalid.",
                }
            ),
            400,
        )

    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify({"ok": False, "message": "User not found."}), 404

    user.email_confirmed = True
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "status": "verified",
            "user_id": user.id,
            "email_confirmed": True,
        }
    )


@bp.get("/verify")
def verify_email_query():
    signed = request.args.get("token", "").strip()
    return _complete_email_verification(signed)


@bp.get("/verify/<token>")
def verify_email_token(token: str):
    return _complete_email_verification(token.strip())


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
