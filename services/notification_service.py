# =============================================================================
# Notification creation — single module for inbox rows (interest, @mentions, …)
# =============================================================================
from __future__ import annotations

import re
from typing import Final

from sqlalchemy import func, select

from api.tags_models import Notification, Post, User, db

NOTIF_TYPE_INTEREST: Final = "interest"
NOTIF_TYPE_MENTION: Final = "mention"

_MENTION_RE = re.compile(r"@(\w+)")


def notify_listing_owner_new_interest(*, sender_id: int, post: Post) -> Notification | None:
    """
    Queue a notification for the listing owner that ``sender_id`` expressed interest.

    Does not commit the session. Returns ``None`` when no row is created.
    """
    owner_id = post.owner_id
    if owner_id is None or owner_id == sender_id:
        return None

    n = Notification(
        user_id=int(owner_id),
        actor_id=int(sender_id),
        post_id=int(post.id),
        comment_id=None,
        notif_type=NOTIF_TYPE_INTEREST,
        read=False,
    )
    db.session.add(n)
    return n


def create_mention_notifications_from_text(
    *,
    actor_id: int,
    post_id: int,
    text: str,
    comment_id: int | None = None,
) -> list[Notification]:
    """
    Parse ``@username`` tokens in ``text`` and enqueue ``mention`` notifications.

    Skips the actor and unknown handles. Dedupes recipients. Does not commit.
    """
    handles = {m.lower() for m in _MENTION_RE.findall(text or "") if m}
    if not handles:
        return []

    stmt = select(User).where(func.lower(User.username).in_(handles), User.username.is_not(None))
    candidates = db.session.scalars(stmt).unique().all()

    out: list[Notification] = []
    seen_receiver: set[int] = set()
    for recv in candidates:
        if recv.id == actor_id or recv.id in seen_receiver:
            continue
        seen_receiver.add(int(recv.id))
        n = Notification(
            user_id=int(recv.id),
            actor_id=int(actor_id),
            post_id=int(post_id),
            comment_id=comment_id,
            notif_type=NOTIF_TYPE_MENTION,
            read=False,
        )
        db.session.add(n)
        out.append(n)
    return out
