# =============================================================================
# Application entry — blueprints: auth, posts, api, messages
# =============================================================================
# This module replaces a single monolithic `app.py` that mixed routes. Splitting
# by feature area reduces merge conflicts when the team works in parallel and
# makes `git blame` point at the right subsystem. Factory pattern preserved for
# tests and WSGI (`flask run`, gunicorn `app:app` once wired).
# =============================================================================
from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify

from auth.constants import ENV_SECRET_KEY, TEST_SECRET_KEY

from api.tags_models import db
from blueprints import api as api_pkg
from blueprints import auth, messages, posts

def _configured_secret(value: object | None) -> str | None:
    """Return a non-empty secret value, or None when unset/blank."""
    if value is None:
        return None

    secret = str(value).strip()
    return secret or None


def _resolve_secret_key(app: Flask, *, testing: bool) -> str:
    """Resolve the Flask secret key without using runtime fallbacks.

    Normal runtime must provide SECRET_KEY through the environment or explicit
    app config. Tests may use a fixed test-only value so unit tests remain
    reproducible without committing real secrets.
    """
    configured = _configured_secret(app.config.get("SECRET_KEY"))
    env_secret = _configured_secret(os.environ.get(ENV_SECRET_KEY))

    if configured:
        return configured

    if env_secret:
        return env_secret

    if testing:
        return TEST_SECRET_KEY

    raise RuntimeError(
        "SECRET_KEY must be set in the environment before starting the app "
        "outside testing mode. Copy .env.example to .env and provide a long "
        "random value."
    )

def create_app(
    test_config: dict[str, Any] | None = None,
    *,
    testing: bool = True,
) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if test_config:
        app.config.update(test_config)
    app.config["SECRET_KEY"] = _resolve_secret_key(app, testing=testing)
    if testing and "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    if not testing and "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
            "DATABASE_URL", "sqlite:///./app.db"
        )

    db.init_app(app)

    # -------------------------------------------------------------------------
    # Blueprint registration order: auth, posts (includes set-status), api, msgs
    # -------------------------------------------------------------------------
    app.register_blueprint(auth.bp)
    posts.register_posts_blueprints(app)
    api_pkg.register_api_blueprints(app)
    app.register_blueprint(messages.bp)

    @app.get("/")
    def root_index():
        return jsonify(
            {
                "app": "uwa-skill-swap",
                "blueprints": ["auth", "posts", "api", "messages"],
            }
        )

    with app.app_context():
        db.create_all()

    return app


# WSGI: use `flask --app "app:create_app" run`  (no eager global `app` object)
def create_production_app() -> Flask:
    return create_app(testing=False)


__all__ = ["create_app", "create_production_app"]
