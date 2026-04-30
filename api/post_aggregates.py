# =============================================================================
# Post aggregate query helpers
# =============================================================================
# These helpers keep count/tag/category aggregation out of templates and stubs.
# List/detail routes can ask for already-shaped payloads instead of triggering
# repeated per-post relationship loads or N+1 counts.
#
# Returned dicts deliberately include coarse category slices and counters so
# future discover/dashboard JSON can evolve without rewriting raw SQL joins.
# =============================================================================
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from api.tags_models import Category, Post, Tag, db, post_tags


def _post_base_select():
    """Shared grouped select: one Post row joined to Category with tag rollup."""
    return (
        select(
            Post.id.label("id"),
            Post.title.label("title"),
            Post.status.label("status"),
            Post.owner_id.label("owner_id"),
            Post.description.label("description"),
            Post.timestamp.label("timestamp"),
            Post.image_filename.label("image_filename"),
            Post.comment_count.label("comment_count"),
            Post.like_count.label("like_count"),
            Category.slug.label("category_slug"),
            Category.label.label("category_label"),
            func.count(Tag.id).label("tag_count"),
        )
        .select_from(Post)
        .join(Category, Post.category_id == Category.id)
        .outerjoin(post_tags, Post.id == post_tags.c.post_id)
        .outerjoin(Tag, Tag.id == post_tags.c.tag_id)
        .group_by(
            Post.id,
            Post.title,
            Post.status,
            Post.owner_id,
            Post.description,
            Post.timestamp,
            Post.image_filename,
            Post.comment_count,
            Post.like_count,
            Category.id,
            Category.slug,
            Category.label,
        )
    )


def _timestamp_safe_iso(value: datetime | None) -> str | None:
    """JSON-serialise naive UTC-ish datetimes emitted by utcnow defaults."""
    if value is None:
        return None
    iso_fn = getattr(value, "isoformat", None)
    if callable(iso_fn):
        return str(iso_fn())
    return None


def _tag_rows_for_post_ids(post_ids: list[int]) -> dict[int, list[dict[str, str]]]:
    """Return tag slug/label pairs for many posts in one grouped query."""
    if not post_ids:
        return {}

    stmt = (
        select(post_tags.c.post_id, Tag.slug, Tag.label)
        .join(Tag, Tag.id == post_tags.c.tag_id)
        .where(post_tags.c.post_id.in_(post_ids))
        .order_by(post_tags.c.post_id.asc(), Tag.label.asc(), Tag.slug.asc())
    )

    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in db.session.execute(stmt).mappings():
        grouped[int(row["post_id"])].append(
            {
                "slug": str(row["slug"]),
                "label": str(row["label"]),
            }
        )

    return dict(grouped)


def _shape_post(
    row: dict[str, Any],
    tags_by_post: dict[int, list[dict[str, str]]],
) -> dict[str, Any]:
    post_id = int(row["id"])
    slug = row.get("category_slug")
    cat_label = row.get("category_label")
    return {
        "id": post_id,
        "title": row["title"],
        "description": row.get("description") or "",
        "status": row["status"],
        "owner_id": row["owner_id"],
        "timestamp_iso": _timestamp_safe_iso(row.get("timestamp")),
        "image_filename": row.get("image_filename"),
        "comment_count": int(row["comment_count"] or 0),
        "like_count": int(row["like_count"] or 0),
        "category": {
            "slug": slug or "",
            "label": cat_label or "",
        },
        "tag_count": int(row["tag_count"] or 0),
        "tags": tags_by_post.get(post_id, []),
    }


def post_list_payload(*, limit: int = 50) -> list[dict[str, Any]]:
    """Return ordering-stable list payloads with aggregates for each post."""
    stmt = _post_base_select().order_by(Post.id.asc()).limit(limit)
    rows = [dict(row) for row in db.session.execute(stmt).mappings().all()]

    post_ids = [int(row["id"]) for row in rows]
    tags_by_post = _tag_rows_for_post_ids(post_ids)

    return [_shape_post(row, tags_by_post) for row in rows]


def post_detail_payload(post_id: int) -> dict[str, Any] | None:
    """Return aggregate payload including category slice, or ``None`` if missing."""
    stmt = _post_base_select().where(Post.id == post_id)
    row = db.session.execute(stmt).mappings().first()

    if row is None:
        return None

    row_dict = dict(row)
    tags_by_post = _tag_rows_for_post_ids([int(row_dict["id"])])

    return _shape_post(row_dict, tags_by_post)
