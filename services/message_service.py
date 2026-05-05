# =============================================================================
# Private message threads — get/open thread, send, inbox, mark read
# =============================================================================
from __future__ import annotations

from typing import Any, Final

from sqlalchemy import func, or_, select, update

from api.tags_models import MessageThread, ThreadMessage, User, db

MAX_MESSAGE_BODY_LEN: Final[int] = 4000


def ordered_participant_pair(a: int, b: int) -> tuple[int, int] | None:
    """Return (low, high) user ids, or ``None`` when both ids are the same."""
    x, y = int(a), int(b)
    if x == y:
        return None
    return (x, y) if x < y else (y, x)


def get_or_create_thread(user_id: int, other_user_id: int) -> tuple[MessageThread | None, str | None]:
    """
    Return an existing thread between the two users or create one.

    ``(thread, None)`` on success; ``(None, error_code)`` on failure
    (``self``, ``peer_not_found``).
    """
    pair = ordered_participant_pair(user_id, other_user_id)
    if pair is None:
        return None, "self"
    low, high = pair
    peer = int(other_user_id)
    if db.session.get(User, peer) is None:
        return None, "peer_not_found"

    t = db.session.scalar(
        select(MessageThread).where(
            MessageThread.participant_low_id == low,
            MessageThread.participant_high_id == high,
        )
    )
    if t is not None:
        return t, None

    t = MessageThread(participant_low_id=low, participant_high_id=high)
    db.session.add(t)
    db.session.commit()
    return t, None


def thread_for_user(thread_id: int, user_id: int) -> MessageThread | None:
    """Thread row when ``user_id`` is a participant; else ``None``."""
    uid = int(user_id)
    tid = int(thread_id)
    return db.session.scalar(
        select(MessageThread).where(
            MessageThread.id == tid,
            or_(
                MessageThread.participant_low_id == uid,
                MessageThread.participant_high_id == uid,
            ),
        )
    )


def other_participant_id(thread: MessageThread, user_id: int) -> int:
    uid = int(user_id)
    if thread.participant_low_id == uid:
        return int(thread.participant_high_id)
    return int(thread.participant_low_id)


def append_message(thread_id: int, sender_id: int, body: str) -> tuple[ThreadMessage | None, str | None]:
    """Validate body, append row. Returns ``(msg, None)`` or ``(None, code)``."""
    t = thread_for_user(thread_id, sender_id)
    if t is None:
        return None, "not_found"
    raw = (body or "").strip()
    if not raw:
        return None, "empty_body"
    if len(raw) > MAX_MESSAGE_BODY_LEN:
        return None, "body_too_long"

    msg = ThreadMessage(thread_id=int(t.id), sender_id=int(sender_id), body=raw, recipient_read=False)
    db.session.add(msg)
    db.session.commit()
    return msg, None


def mark_thread_read(thread_id: int, reader_id: int) -> tuple[int, str | None]:
    """Mark all messages addressed to ``reader_id`` in this thread as read. ``(count, err)``."""
    t = thread_for_user(thread_id, reader_id)
    if t is None:
        return 0, "not_found"
    rid = int(reader_id)
    stmt = (
        update(ThreadMessage)
        .where(
            ThreadMessage.thread_id == t.id,
            ThreadMessage.sender_id != rid,
            ThreadMessage.recipient_read.is_(False),
        )
        .values(recipient_read=True)
    )
    res = db.session.execute(stmt)
    db.session.commit()
    return int(res.rowcount or 0), None


def message_read_for_viewer(msg: ThreadMessage, viewer_id: int) -> bool:
    """Whether ``viewer_id`` has no pending unread flag for this row."""
    vid = int(viewer_id)
    if int(msg.sender_id) == vid:
        return True
    return bool(msg.recipient_read)


def thread_messages_for_api(thread_id: int, viewer_id: int) -> tuple[list[dict[str, Any]], str | None]:
    t = thread_for_user(thread_id, viewer_id)
    if t is None:
        return [], "not_found"
    rows = (
        db.session.scalars(
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == t.id)
            .order_by(ThreadMessage.created_at.asc(), ThreadMessage.id.asc())
        )
        .all()
    )
    out: list[dict[str, Any]] = []
    for m in rows:
        out.append(
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "body": m.body,
                "created_at": m.created_at.isoformat(timespec="seconds") if m.created_at else None,
                "read": message_read_for_viewer(m, viewer_id),
            }
        )
    return out, None


def _user_brief(u: User | None) -> dict[str, Any] | None:
    if u is None:
        return None
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
    }


def inbox_for_user(user_id: int) -> list[dict[str, Any]]:
    """One entry per thread for this user: peer, preview, unread, last activity."""
    uid = int(user_id)
    threads = db.session.scalars(
        select(MessageThread).where(
            or_(
                MessageThread.participant_low_id == uid,
                MessageThread.participant_high_id == uid,
            )
        )
    ).all()

    items: list[dict[str, Any]] = []
    for th in threads:
        other_id = other_participant_id(th, uid)
        other = db.session.get(User, other_id)
        last = db.session.scalar(
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == th.id)
            .order_by(ThreadMessage.created_at.desc(), ThreadMessage.id.desc())
            .limit(1)
        )
        unread = int(
            db.session.scalar(
                select(func.count(ThreadMessage.id)).where(
                    ThreadMessage.thread_id == th.id,
                    ThreadMessage.sender_id != uid,
                    ThreadMessage.recipient_read.is_(False),
                )
            )
            or 0
        )
        preview = ""
        last_at: str | None = None
        if last is not None:
            preview = last.body if len(last.body) <= 140 else last.body[:137] + "..."
            last_at = last.created_at.isoformat(timespec="seconds") if last.created_at else None

        items.append(
            {
                "thread_id": th.id,
                "other": _user_brief(other),
                "last_message_at": last_at,
                "preview": preview,
                "unread_for_me": unread,
            }
        )

    items.sort(key=lambda x: (x["last_message_at"] or "", x["thread_id"]), reverse=True)
    return items


def unread_in_thread_for_user(thread_id: int, viewer_id: int) -> int | None:
    """Count messages in ``thread_id`` addressed to ``viewer_id`` that are unread. ``None`` if not a member."""
    t = thread_for_user(thread_id, viewer_id)
    if t is None:
        return None
    uid = int(viewer_id)
    n = db.session.scalar(
        select(func.count(ThreadMessage.id)).where(
            ThreadMessage.thread_id == t.id,
            ThreadMessage.sender_id != uid,
            ThreadMessage.recipient_read.is_(False),
        )
    )
    return int(n or 0)


def thread_poll_payload(thread_id: int, viewer_id: int, after_id: int) -> tuple[dict[str, Any] | None, str | None]:
    """
    Incremental poll: messages with primary key strictly greater than ``after_id``.

    Returns a JSON-serialisable dict with ``messages``, ``latest_id``, and
    ``unread_for_me`` (thread-wide unread count for the viewer).
    """
    t = thread_for_user(thread_id, viewer_id)
    if t is None:
        return None, "not_found"

    rows = (
        db.session.scalars(
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == t.id, ThreadMessage.id > int(after_id))
            .order_by(ThreadMessage.created_at.asc(), ThreadMessage.id.asc())
        )
        .all()
    )
    msg_out: list[dict[str, Any]] = []
    for m in rows:
        msg_out.append(
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "body": m.body,
                "created_at": m.created_at.isoformat(timespec="seconds") if m.created_at else None,
                "read": message_read_for_viewer(m, viewer_id),
            }
        )

    latest = db.session.scalar(
        select(ThreadMessage.id)
        .where(ThreadMessage.thread_id == t.id)
        .order_by(ThreadMessage.id.desc())
        .limit(1)
    )

    unread = unread_in_thread_for_user(int(t.id), int(viewer_id))
    if unread is None:
        return None, "not_found"

    return (
        {
            "thread_id": t.id,
            "after_id": int(after_id),
            "messages": msg_out,
            "latest_id": int(latest) if latest is not None else None,
            "unread_for_me": unread,
        },
        None,
    )
