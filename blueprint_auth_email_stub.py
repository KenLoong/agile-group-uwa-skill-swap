# =============================================================================
# STUB: Flask blueprint for email verification (wire-up in a later milestone)
# =============================================================================
# This file is not imported by a root `app.py` until the backend is merged.
# It exists so the team can see route names and `url_for` targets during code review.
#
# Suggested registration in app factory:
#   from blueprint_auth_email_stub import bp as auth_email_bp
#   app.register_blueprint(auth_email_bp, url_prefix="/auth")
#
# Endpoints (draft):
#   GET  /auth/verify      — consume token, flash success, set session / redirect
#   POST /auth/resend      — JSON or form, requires login, calls EmailVerificationService.resend
#
# The real implementation will use Flask-Login's `current_user` and a User model
# with `email_confirmed: bool` or `email_verified_at: datetime | None`.
# =============================================================================
from __future__ import annotations

# from flask import Blueprint, flash, redirect, request, url_for, render_template
# from auth.email_verification import default_service
# from auth.exceptions import (
#     TokenInvalidError, TokenExpiredError, ResendThrottledError, UserAlreadyVerifiedError,
# )

# bp = Blueprint("auth_email", __name__)


# @bp.route("/verify", methods=["GET"])
# def verify_get():
#     token = request.args.get("token", "")
#     if not token:
#         flash("Missing verification link.", "danger")
#         return redirect(url_for("login"))
#     try:
#         uid = default_service.verify_and_consume(token)
#     except TokenExpiredError:
#         flash("This link has expired. Request a new one from the pending page.", "warning")
#         return redirect(url_for("auth_email.verify_pending"))
#     except TokenInvalidError:
#         flash("This link is invalid or already used.", "danger")
#         return redirect(url_for("register"))
#     # set User.query.get(uid).email_confirmed = True; db.session.commit()
#     flash("Your UWA email is verified — welcome!", "success")
#     return redirect(url_for("login"))


# @bp.route("/resend", methods=["POST"])
# @login_required
# def resend():
#     ...
#     return redirect(url_for("auth_email.verify_pending"))
