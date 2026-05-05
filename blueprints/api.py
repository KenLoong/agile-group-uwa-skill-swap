# =============================================================================
# Blueprint: api  —  JSON routes (tags, discover metadata, future mobile contract)
# =============================================================================
# Wraps existing tag API that lived under api/tags_blueprint.py. Further
# endpoints (search, geo) should register here or in submodules imported below
# so git blame stays local to the API squad.
# =============================================================================
from __future__ import annotations

from flask import Blueprint, Flask, jsonify

from api.featured_blueprint import bp as featured_posts_bp
from api.filter_blueprint import bp as discover_filter_bp
from api.tags_blueprint import bp as tags_json_blueprint

bp = Blueprint("api_extra", __name__, url_prefix="/api")


@bp.get("/health")
def api_health():
    return jsonify({"status": "ok", "layer": "blueprints.api"})


@bp.get("/version")
def api_version():
    return jsonify({"name": "skill-swap-api", "slice": "tags+filter+featured+v1"})


def register_api_blueprints(app: Flask) -> None:
    """
    Register tag cloud, discover filter, pinned featured JSON, ``/api/health``.
    """
    app.register_blueprint(tags_json_blueprint)
    app.register_blueprint(discover_filter_bp)
    app.register_blueprint(featured_posts_bp)
    app.register_blueprint(bp)
