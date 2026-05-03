# =============================================================================
# Blueprint: interaction — express interest, future notification-adjacent POSTs
# =============================================================================
from __future__ import annotations

from flask import Blueprint, jsonify

from api.auth_identity import effective_user_id
from services.interaction_service import record_interest

bp = Blueprint("interaction", __name__)

_HTTP = {
    "not_found": 404,
    "duplicate": 409,
    "self_interest": 400,
    "no_owner": 400,
}


@bp.post("/interest/<int:post_id>")
def express_interest(post_id: int):
    """Record interest and notify listing owner via ``services.notification_service``."""
    uid = effective_user_id()
    if uid is None:
        return jsonify({"ok": False, "message": "Authentication required"}), 401

    ok, code = record_interest(uid, post_id)
    if ok:
        return jsonify({"ok": True}), 200

    return jsonify({"ok": False, "error": code}), _HTTP.get(code, 400)
