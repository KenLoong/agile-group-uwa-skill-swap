# =============================================================================
# Blueprint: posts  —  listings, filters, /post/set-status ownership
# =============================================================================
# The post lifecycle endpoint used by dashboard JS used to be registered
# next to the tag API. We pull it in here to group everything that mutates
# TPost rows in one import graph for code review.
# =============================================================================
from __future__ import annotations

from flask import Blueprint, Flask, jsonify, render_template_string

from api.post_status import bp as post_status_slice

bp = Blueprint("posts", __name__, url_prefix="/posts")


@bp.get("/")
def list_posts_stub():
    return jsonify({"items": [], "module": "posts", "note": "stub list"})


@bp.get("/create")
def create_form_stub():
    return (
        render_template_string(
            "<!doctype html><title>new post</title><p>posts/create html stub</p>"
        ),
        200,
    )


@bp.get("/<int:post_id>")
def get_post_stub(post_id: int):
    return jsonify({"id": post_id, "title": "stub", "status": "open"})


def register_posts_blueprints(app: Flask) -> None:
    """
    Register the HTML/JSON `posts` blueprint plus the post_status slice
    (includes POST /post/set-status at application root of that module).
    """
    app.register_blueprint(bp)
    app.register_blueprint(post_status_slice)
