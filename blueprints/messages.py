# =============================================================================
# Blueprint: messages  —  conversations, interest threads, notification hooks
# =============================================================================
# Sprint goal: file ownership is clear. Implementation may stay minimal until
# the messaging data model (SQLAlchemy) lands from the design branch.
# =============================================================================
from __future__ import annotations

from flask import Blueprint, jsonify, request

bp = Blueprint("messages", __name__, url_prefix="/messages")


@bp.get("/inbox")
def inbox():
    return jsonify({"items": [], "module": "messages", "unread": 0})


@bp.get("/thread/<int:thread_id>")
def thread_detail(thread_id: int):
    return jsonify({"thread_id": thread_id, "messages": []})


@bp.post("/thread/<int:thread_id>/read")
def mark_read(thread_id: int):
    return jsonify({"ok": True, "thread_id": thread_id})


@bp.get("/_ping")
def messages_ping():
    return jsonify({"module": "messages", "q": request.args.get("q", "")})


# --- placeholders for later REST surface ------------------------------------

@bp.post("/")
def post_stub():
    return jsonify({"ok": False, "detail": "use thread routes"}), 400
