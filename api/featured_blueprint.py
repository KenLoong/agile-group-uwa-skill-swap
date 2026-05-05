# =============================================================================
# GET /api/featured-posts — JSON for homepage/widgets (pinned open listings)
# =============================================================================
from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from api.featured_posts import featured_post_cards

bp = Blueprint("featured_posts_api", __name__, url_prefix="/api")


@bp.get("/featured-posts")
def list_featured_posts():
    """Return pinned ``open`` posts ordered by ``featured_pin_order`` (ASC)."""
    lim = int(current_app.config.get("FEATURED_POSTS_HOME_LIMIT", 8))
    body = {"posts": featured_post_cards(lim)}
    resp = jsonify(body)
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp, 200
