# =============================================================================
# Minimal app factory for API slice tests (tags). Full app lives in app.py later.
# =============================================================================
from __future__ import annotations

import os
from flask import Flask

from api.post_status import bp as post_status_bp
from api.tags_blueprint import bp as tags_bp
from api.tags_models import db


def create_app(testing: bool = True) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if testing:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
            "DATABASE_URL", "sqlite:///./tags_dev.db"
        )
    db.init_app(app)
    app.register_blueprint(tags_bp)
    app.register_blueprint(post_status_bp)

    with app.app_context():
        db.create_all()

    return app
