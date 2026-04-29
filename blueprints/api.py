# =============================================================================
# Blueprint: api  —  JSON routes (tags, discover metadata, future mobile contract)
# =============================================================================
# Wraps existing tag API that lived under api/tags_blueprint.py. Further
# endpoints (search, geo) should register here or in submodules imported below
# so git blame stays local to the API squad.
# =============================================================================
from __future__ import annotations

from flask import Blueprint, Flask, jsonify

from api.tags_blueprint import bp as tags_json_blueprint

bp = Blueprint("api_extra", __name__, url_prefix="/api")


@bp.get("/health")
def api_health():
    return jsonify({"status": "ok", "layer": "blueprints.api"})


@bp.get("/version")
def api_version():
    return jsonify({"name": "skill-swap-api", "slice": "tags+v1"})


def register_api_blueprints(app: Flask) -> None:
    """
    Register tag cloud + cacheable discover JSON. The tags blueprint already
    declares url_prefix `/api`, so we register it at app root; `api_extra`
    also uses `/api` — only different route names (health vs tags).
    """
    app.register_blueprint(tags_json_blueprint)
    app.register_blueprint(bp)
