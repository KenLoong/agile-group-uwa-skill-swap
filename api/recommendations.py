# =============================================================================
# Dashboard recommendations — wanted categories → open posts from other users
# =============================================================================
from __future__ import annotations

from sqlalchemy import select

from api.post_aggregates import post_detail_payload
from api.tags_models import POST_STATUS_OPEN, Interest, Post, User, db

DEFAULT_RECOMMENDATION_LIMIT = 12
_MAX_RECOMMENDATION_LIMIT = 100


def clamp_recommendation_limit(raw: object | None) -> int:
    """Normalise client ``limit`` query values to a safe inclusive range."""
    if raw is None:
        return DEFAULT_RECOMMENDATION_LIMIT
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_RECOMMENDATION_LIMIT
    return max(1, min(n, _MAX_RECOMMENDATION_LIMIT))


def recommended_post_payloads(user_id: int, *, limit: int = DEFAULT_RECOMMENDATION_LIMIT) -> list[dict]:
    """
    Shape the same listing/detail aggregate records as ``post_detail_payload``.

    Rules:
        * category must be one the viewer listed under ``wanted_categories``;
        * ``status`` must be ``open``;
        * exclude posts owned by the viewer;
        * exclude posts the viewer already stored under ``Interest``.
    """
    user = db.session.get(User, user_id)
    if user is None:
        return []

    wanted_ids = sorted({c.id for c in user.wanted_categories})
    if not wanted_ids:
        return []

    limit = clamp_recommendation_limit(limit)
    interested_subq = select(Interest.post_id).where(Interest.sender_id == user_id)

    stmt = (
        select(Post.id)
        .where(
            Post.category_id.in_(wanted_ids),
            Post.status == POST_STATUS_OPEN,
            Post.owner_id.is_not(None),
            Post.owner_id != user_id,
            ~Post.id.in_(interested_subq),
        )
        .order_by(Post.timestamp.desc(), Post.id.desc())
        .limit(limit)
    )
    ids = list(db.session.scalars(stmt))

    out: list[dict] = []
    for pid in ids:
        row = post_detail_payload(int(pid))
        if row is not None:
            out.append(row)
    return out
