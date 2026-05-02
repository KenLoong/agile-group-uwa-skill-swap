# =============================================================================
# Discover list ordering — deterministic ORDER BY for GET /api/filter
# =============================================================================
# Member 2 Issue #5 ("Stabilise most likes sort"): SQL does not guarantee a
# stable row order when ORDER BY only names non-unique expressions. Discover
# pagination then returns different card sequences on SQLite vs PostgreSQL, or
# between two identical requests, whenever denormalised counters or timestamps
# tie. This module centralises every sort branch with explicit final tie-break
# on Post.id (monotonic surrogate) so behaviour is predictable in tests and prod.
#
# Contract reference: docs/API_CONTRACTS.md § GET /api/filter → Sort semantics.
# =============================================================================
from __future__ import annotations

from typing import Any

from sqlalchemy import func

from api.tags_models import Interest, Post


# ---------------------------------------------------------------------------
# Public: apply the correct branch (call *after* filters, *before* eager loads)
# ---------------------------------------------------------------------------


def apply_discover_sort(query: Any, sort: str) -> Any:
    """
    Attach ORDER BY (and for ``popular`` only: join + GROUP BY) to a Post query.

    Parameters
    ----------
    query:
        Flask-SQLAlchemy ``Post.query``-style object with filters already applied.
    sort:
        Normalised mode: ``newest``, ``likes``, or ``popular``.

    Notes
    -----
    * ``newest`` — Chronological feed. Ties on identical ``timestamp`` resolve
      with ``id DESC`` so batch-created rows still order consistently.
    * ``likes`` — Primary key is denormalised ``like_count``. Tie chain:
      ``like_count DESC``, ``timestamp DESC``, ``id DESC``.
    * ``popular`` — Uses ``COUNT(interest rows)`` per post. After counting,
      ties use ``timestamp DESC`` then ``id DESC`` (same stability story).
    """
    key = (sort or "newest").strip().lower()

    if key == "likes":
        return query.order_by(*likes_order_columns())

    if key == "popular":
        return (
            query.outerjoin(Interest, Interest.post_id == Post.id)
            .group_by(Post.id)
            .order_by(*popular_order_columns())
        )

    return query.order_by(*newest_order_columns())


# ---------------------------------------------------------------------------
# Column tuples — each list is a total order modulo unique id as last key
# ---------------------------------------------------------------------------


def newest_order_columns():
    """``sort=newest``: most recent ``timestamp`` first; ties → larger ``id`` first."""
    return (Post.timestamp.desc(), Post.id.desc())


def likes_order_columns():
    """
    ``sort=likes``: highest ``like_count`` first.

    Secondary keys avoid undefined ordering when:
    * several posts share the same cached like total, or
    * timestamps collide (imports, naive datetimes).
    """
    return (Post.like_count.desc(), Post.timestamp.desc(), Post.id.desc())


def popular_order_columns():
    """
    ``ORDER BY`` fragment for the grouped ``popular`` query **after**
    ``outerjoin(Interest)`` and ``group_by(Post.id)``.

    The aggregate ``COUNT(Interest.id)`` is the popularity score; final keys
    match ``newest``-style freshness and id stability.
    """
    return (func.count(Interest.id).desc(), Post.timestamp.desc(), Post.id.desc())


def ordering_spec_human_readable() -> dict[str, list[str]]:
    """
    Stable description of tie-break chains (documentation / tooling).

    Intended for dashboards or codegen; not wired to HTTP responses today.
    """
    return {
        "newest": [
            "Post.timestamp descending",
            "Post.id descending (tie-break)",
        ],
        "likes": [
            "Post.like_count descending",
            "Post.timestamp descending",
            "Post.id descending (tie-break)",
        ],
        "popular": [
            "COUNT(Interest.id) per Post descending",
            "Post.timestamp descending",
            "Post.id descending (tie-break)",
        ],
    }


__all__ = [
    "apply_discover_sort",
    "likes_order_columns",
    "newest_order_columns",
    "ordering_spec_human_readable",
    "popular_order_columns",
]
