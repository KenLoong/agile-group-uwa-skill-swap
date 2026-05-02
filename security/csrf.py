# =============================================================================
# CSRF configuration and error handling
# =============================================================================
from __future__ import annotations

from flask import jsonify, render_template_string, request
from flask_wtf.csrf import CSRFError, CSRFProtect

CSRF_AJAX_HEADER = "X-CSRFToken"
CSRF_ALT_AJAX_HEADER = "X-CSRF-Token"
CSRF_META_NAME = "csrf-token"
DEFAULT_CSRF_TIME_LIMIT_SECONDS = 60 * 60

csrf = CSRFProtect()


def _wants_json_response() -> bool:
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])

    return (
        best == "application/json"
        or request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def _csrf_error_message(error: CSRFError) -> str:
    return error.description or "The CSRF token is missing or invalid."


def init_csrf(app) -> None:
    """Initialise Flask-WTF CSRF support and standard response handling.

    `WTF_CSRF_CHECK_DEFAULT` is intentionally false for this slice. FlaskForm
    submissions still validate their own CSRF tokens, while JSON/AJAX endpoints
    can opt in deliberately as those routes are finalised.
    """
    app.config.setdefault(
        "WTF_CSRF_HEADERS",
        [CSRF_AJAX_HEADER, CSRF_ALT_AJAX_HEADER],
    )
    app.config.setdefault("WTF_CSRF_TIME_LIMIT", DEFAULT_CSRF_TIME_LIMIT_SECONDS)
    app.config.setdefault("WTF_CSRF_CHECK_DEFAULT", False)

    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError):
        message = _csrf_error_message(error)

        if _wants_json_response():
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "csrf_failed",
                        "message": message,
                    }
                ),
                400,
            )

        return (
            render_template_string(
                """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Security check failed · UWA Skill-Swap</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <main>
    <h1>Security check failed</h1>
    <p>{{ message }}</p>
    <p>Please refresh the page and try again.</p>
  </main>
</body>
</html>""",
                message=message,
            ),
            400,
            {"Content-Type": "text/html; charset=utf-8"},
        )