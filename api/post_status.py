# =============================================================================
# POST /post/set-status  —  owner updates listing lifecycle (open / matched / closed)
# =============================================================================
# Coursework slice: authenticated caller must match Post.owner_id. Test client
# passes identity via X-User-Id (dev/test); production would replace with session.
# =============================================================================
from __future__ import annotations

from flask import Blueprint, jsonify, request

from api.tags_models import POST_STATUS_VALUES, Post, db
from api.taxonomy_helpers import is_allowed_post_status

bp = Blueprint("post_status", __name__)


def _caller_user_id() -> int | None:
    """
    Identity for this request. In unit tests we set X-User-Id; later merge may use
    flask_login.current_user or session without changing the ownership check here.
    """
    raw = request.headers.get("X-User-Id", "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    return None


@bp.post("/post/set-status")
def post_set_status():
    """
    Body JSON: { "post_id": <int>, "status": "open" | "matched" | "closed" }

    200: { "ok": true, "post_id", "status" } — persisted
    400: bad JSON or bad status
    401: missing X-User-Id (unauthenticated in this slice)
    404: no such post
    403: caller is not the owner
    """
    if not request.is_json:
        return jsonify({"ok": False, "error": "content_type", "detail": "application/json required"}), 400

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "body", "detail": "object expected"}), 400

    post_id = payload.get("post_id")
    status_raw = payload.get("status", "")
    if not isinstance(post_id, int) and not (isinstance(post_id, str) and post_id.isdigit()):
        return jsonify({"ok": False, "error": "post_id", "detail": "integer post_id required"}), 400
    pid = int(post_id)

    if not isinstance(status_raw, str):
        return jsonify({"ok": False, "error": "status", "detail": "string status required"}), 400

    if not is_allowed_post_status(status_raw):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "status",
                    "detail": f"must be one of {sorted(POST_STATUS_VALUES)}",
                }
            ),
            400,
        )
    st = status_raw.strip().lower()

    uid = _caller_user_id()
    if uid is None:
        return jsonify({"ok": False, "error": "auth", "detail": "X-User-Id required"}), 401

    rec = db.session.get(Post, pid)
    if rec is None:
        return jsonify({"ok": False, "error": "not_found", "detail": "post"}), 404

    if rec.owner_id is None or rec.owner_id != uid:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "forbidden",
                    "detail": "only the owner may set status",
                }
            ),
            403,
        )

    rec.status = st
    db.session.add(rec)
    db.session.commit()

    return (
        jsonify(
            {
                "ok": True,
                "post_id": rec.id,
                "status": rec.status,
            }
        ),
        200,
    )
