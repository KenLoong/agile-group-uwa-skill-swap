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

from api.tags_models import db
from blueprints import api as api_pkg
from blueprints import auth, messages, posts


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
