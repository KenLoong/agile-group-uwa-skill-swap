# =============================================================================
# Featured (pinned) posts — homepage + GET /api/featured-posts
# =============================================================================
# Demo-day visibility: staff set ``Post.featured_pin_order`` (small int = higher
# on page). Only ``open`` posts are returned so closed/matched rows do not leak
# onto the marketing strip.
# =============================================================================
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import joinedload

from api.tags_models import POST_STATUS_OPEN, Post


def featured_open_posts_query(limit: int):
    """ORM query: eager loads for discover-card shaping; caller applies ``.all()``."""
    lim = max(1, min(int(limit), 50))
    return (
        Post.query.filter(
            Post.featured_pin_order.isnot(None),
            Post.status == POST_STATUS_OPEN,
        )
        .order_by(Post.featured_pin_order.asc(), Post.id.desc())
        .options(
            joinedload(Post.category),
            joinedload(Post.owner),
            joinedload(Post.tags),
        )
        .limit(lim)
    )


def featured_post_cards(limit: int) -> list[dict[str, Any]]:
    """Discover-shaped cards plus ``featured_pin_order`` for the featured JSON route."""
    from api.filter_blueprint import post_to_discover_card

    rows: list[dict[str, Any]] = []
    for p in featured_open_posts_query(limit).all():
        card = post_to_discover_card(p)
        order = getattr(p, "featured_pin_order", None)
        if order is not None:
            card["featured_pin_order"] = int(order)
        rows.append(card)
    return rows


__all__ = ["featured_open_posts_query", "featured_post_cards"]
