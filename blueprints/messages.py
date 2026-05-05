# =============================================================================
# Blueprint: messages — private threads (pairwise) + minimal thread messages
# =============================================================================
from __future__ import annotations

from flask import Blueprint, jsonify, request

from api.auth_identity import effective_user_id
from api.tags_models import User, db
from services.message_service import (
    MAX_MESSAGE_BODY_LEN,
    append_message,
    get_or_create_thread,
    inbox_for_user,
    mark_thread_read,
    other_participant_id,
    thread_for_user,
    thread_messages_for_api,
    thread_poll_payload,
)

bp = Blueprint("messages", __name__, url_prefix="/messages")


def _require_user():
    uid = effective_user_id()
    if uid is None:
        return None, (jsonify({"message": "Authentication required"}), 401)
    if db.session.get(User, int(uid)) is None:
        return None, (jsonify({"message": "User not found"}), 404)
    return int(uid), None


@bp.get("/inbox")
def inbox():
    maybe = _require_user()
    if maybe[0] is None:
        return maybe[1]
    uid = maybe[0]
    items = inbox_for_user(uid)
    total_unread = sum(int(x.get("unread_for_me") or 0) for x in items)
    return jsonify({"items": items, "module": "messages", "unread": total_unread})


@bp.post("/thread/open")
def open_thread():
    """Open or create a 1:1 thread with ``other_user_id`` in JSON body."""
    maybe = _require_user()
    if maybe[0] is None:
        return maybe[1]
    uid = maybe[0]

    if not request.is_json:
        return jsonify({"message": "application/json expected"}), 400
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"message": "JSON object expected"}), 400
    oid = payload.get("other_user_id")
    if not isinstance(oid, int) and not (isinstance(oid, str) and oid.strip().isdigit()):
        return jsonify({"message": "other_user_id must be an integer"}), 400
    other = int(oid)

    thr, err = get_or_create_thread(uid, other)
    if thr is None:
        if err == "self":
            return jsonify({"message": "Cannot open a thread with yourself"}), 400
        if err == "peer_not_found":
            return jsonify({"message": "Other user not found"}), 404
        return jsonify({"message": "Could not open thread"}), 400

    return jsonify({"thread_id": thr.id})


@bp.get("/thread/<int:thread_id>/poll")
def thread_poll(thread_id: int):
    """
    Incremental fetch for long-polling / periodic refresh.

    Query ``after_id`` (non-negative int, default ``0``): return messages with id &gt; ``after_id``.
    Response includes ``latest_id`` and thread-wide ``unread_for_me`` for the caller.
    """
    maybe = _require_user()
    if maybe[0] is None:
        return maybe[1]
    uid = maybe[0]

    raw = (request.args.get("after_id") or "0").strip()
    if not raw.isdigit():
        return jsonify({"message": "after_id must be a non-negative integer"}), 400
    after_id = int(raw)

    payload, err = thread_poll_payload(thread_id, uid, after_id)
    if err or payload is None:
        return jsonify({"message": "Thread not found"}), 404
    return jsonify(payload)


@bp.get("/thread/<int:thread_id>")
def thread_detail(thread_id: int):
    maybe = _require_user()
    if maybe[0] is None:
        return maybe[1]
    uid = maybe[0]

    t = thread_for_user(thread_id, uid)
    if t is None:
        return jsonify({"message": "Thread not found"}), 404

    messages, err = thread_messages_for_api(thread_id, uid)
    if err:
        return jsonify({"message": "Thread not found"}), 404

    other_id = other_participant_id(t, uid)
    other = db.session.get(User, other_id)
    me = db.session.get(User, uid)
    return jsonify(
        {
            "thread_id": t.id,
            "you": {
                "id": uid,
                "username": me.username if me else None,
                "email": me.email if me else None,
            },
            "other": (
                {"id": other.id, "username": other.username, "email": other.email}
                if other
                else {"id": other_id, "username": None, "email": None}
            ),
            "messages": messages,
        }
    )


@bp.post("/thread/<int:thread_id>/messages")
def post_message(thread_id: int):
    """Append a text message; body from JSON ``{ \"body\": \"...\" }``."""
    maybe = _require_user()
    if maybe[0] is None:
        return maybe[1]
    uid = maybe[0]

    if not request.is_json:
        return jsonify({"message": "application/json expected"}), 400
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"message": "JSON object expected"}), 400
    body = payload.get("body", "")
    if body is None:
        body = ""
    if not isinstance(body, str):
        return jsonify({"message": "body must be a string"}), 400

    msg, err = append_message(thread_id, uid, body)
    if msg is None:
        if err == "not_found":
            return jsonify({"message": "Thread not found"}), 404
        if err == "empty_body":
            return jsonify({"message": "body must not be empty"}), 400
        if err == "body_too_long":
            return jsonify(
                {"message": f"body exceeds maximum length ({MAX_MESSAGE_BODY_LEN} characters)"}
            ), 400
        return jsonify({"message": "Could not send message"}), 400

    return jsonify(
        {
            "ok": True,
            "message": {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "body": msg.body,
                "created_at": msg.created_at.isoformat(timespec="seconds") if msg.created_at else None,
                "read": True,
            },
        }
    )


@bp.post("/thread/<int:thread_id>/read")
def mark_read(thread_id: int):
    maybe = _require_user()
    if maybe[0] is None:
        return maybe[1]
    uid = maybe[0]

    n, err = mark_thread_read(thread_id, uid)
    if err:
        return jsonify({"message": "Thread not found"}), 404
    return jsonify({"ok": True, "thread_id": thread_id, "marked": n})


@bp.get("/_ping")
def messages_ping():
    return jsonify({"module": "messages", "q": request.args.get("q", "")})


@bp.post("/")
def post_stub():
    return (
        jsonify({"ok": False, "detail": "use /messages/thread/open, /poll, or /messages/thread/<id>/messages"}),
        400,
    )
