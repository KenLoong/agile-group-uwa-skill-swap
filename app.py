# =============================================================================
# Application entry — blueprints: auth, posts, api, messages, dashboard
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
from flask_login import LoginManager

from auth.constants import ENV_SECRET_KEY, TEST_SECRET_KEY
from api.dashboard_api import bp as dashboard_api_bp
from api.tags_models import CATEGORY_SLUG_GENERAL, Category, User, db
from blueprints import api as api_pkg
from blueprints import auth, dashboard_page, messages, posts


def _seed_categories_if_empty() -> None:
    """
    Populate default taxonomy on first boot: ``general`` (post FK sanity) plus
    discover/dashboard buckets from product defaults.
    """
    defaults: list[tuple[str, str, int]] = [
        (CATEGORY_SLUG_GENERAL, "General", 0),
        ("coding", "Coding", 10),
        ("languages", "Languages", 20),
        ("music", "Music", 30),
        ("sports", "Sports", 40),
        ("communication", "Communication", 50),
    ]
    if Category.query.first() is None:
        for slug, label, sort in defaults:
            db.session.add(Category(slug=slug, label=label, sort_order=sort))
        db.session.commit()

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

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login_form"

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        if not user_id.strip().isdigit():
            return None
        out = db.session.get(User, int(user_id))
        return out

    # -------------------------------------------------------------------------
    # Blueprint registration order: auth, posts (includes set-status), api, msgs
    # -------------------------------------------------------------------------
    app.register_blueprint(auth.bp)
    posts.register_posts_blueprints(app)
    api_pkg.register_api_blueprints(app)
    app.register_blueprint(messages.bp)

    app.register_blueprint(dashboard_api_bp)
    app.register_blueprint(dashboard_page.bp)

    @app.get("/")
    def root_index():
        return jsonify(
            {
                "app": "uwa-skill-swap",
                "blueprints": ["auth", "posts", "api", "messages", "dashboard"],
            }
        )

    with app.app_context():
        db.create_all()
        _seed_categories_if_empty()

    return app


# WSGI: use `flask --app "app:create_app" run`  (no eager global `app` object)
def create_production_app() -> Flask:
    return create_app(testing=False)


__all__ = ["create_app", "create_production_app"]
