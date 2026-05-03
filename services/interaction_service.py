# =============================================================================
# Interest expression — persists Interest row and notifies via notification_service
# =============================================================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.tags_models import Interest, Post, db
from services.notification_service import notify_listing_owner_new_interest


def record_interest(sender_id: int, post_id: int) -> tuple[bool, str]:
    """
    Create an ``Interest`` row and notify the listing owner using the central service.

    Returns ``(True, \"ok\")`` or ``(False, reason)`` without partial commits on failure.
    """
    post = db.session.get(Post, post_id)
    if post is None:
        return False, "not_found"
    if post.owner_id is None:
        return False, "no_owner"
    if int(post.owner_id) == int(sender_id):
        return False, "self_interest"

    dup = db.session.scalar(
        select(Interest.id).where(Interest.sender_id == sender_id, Interest.post_id == post_id)
    )
    if dup is not None:
        return False, "duplicate"

    db.session.add(Interest(sender_id=int(sender_id), post_id=int(post_id)))
    notify_listing_owner_new_interest(sender_id=int(sender_id), post=post)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False, "duplicate"

    return True, "ok"
