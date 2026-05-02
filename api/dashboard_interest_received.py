# =============================================================================
# Dashboard — interest received (people who signalled interest on your listings)
# =============================================================================
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from api.tags_models import Category, Interest, Post, User, db

DEFAULT_INTEREST_RECEIVED_LIMIT = 50
_MAX_INTEREST_RECEIVED_LIMIT = 100


def clamp_interest_received_limit(raw: object | None) -> int:
    if raw is None:
        return DEFAULT_INTEREST_RECEIVED_LIMIT
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_INTEREST_RECEIVED_LIMIT
    return max(1, min(n, _MAX_INTEREST_RECEIVED_LIMIT))


def _ts_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    fn = getattr(value, "isoformat", None)
    if callable(fn):
        return str(fn())
    return str(value)


def interest_received_rows(owner_user_id: int, *, limit: int = DEFAULT_INTEREST_RECEIVED_LIMIT) -> list[dict[str, Any]]:
    """
    Summarise ``Interest`` rows where the linked post is owned by ``owner_user_id``.

    Ordered newest first (then interest id for ties). Each item is JSON-friendly.
    """
    lim = clamp_interest_received_limit(limit)

    stmt = (
        select(Interest, Post, Category, User)
        .join(Post, Interest.post_id == Post.id)
        .join(Category, Post.category_id == Category.id)
        .join(User, Interest.sender_id == User.id)
        .where(Post.owner_id == owner_user_id)
        .order_by(Interest.timestamp.desc(), Interest.id.desc())
        .limit(lim)
    )

    out: list[dict[str, Any]] = []
    for intr, post, cat, sender in db.session.execute(stmt).all():
        out.append(
            {
                "interest_id": int(intr.id),
                "at": _ts_iso(intr.timestamp),
                "post": {"id": int(post.id), "title": str(post.title)},
                "category": {"slug": str(cat.slug), "label": str(cat.label)},
                "sender": {
                    "id": int(sender.id),
                    "email": str(sender.email),
                    "username": sender.username,
                },
            }
        )
    return out
