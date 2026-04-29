# =============================================================================
# Post aggregate query helpers
# =============================================================================
# These helpers keep count/tag aggregation out of templates and route stubs.
# List/detail routes can ask for already-shaped payloads instead of triggering
# repeated per-post relationship loads or count queries.
# =============================================================================
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select

from api.tags_models import TPost, Tag, db, post_tags


def _post_base_select():
    """Shared aggregate select for post list/detail JSON payloads."""
    return (
        select(
            TPost.id.label("id"),
            TPost.title.label("title"),
            TPost.status.label("status"),
            TPost.owner_id.label("owner_id"),
            func.count(Tag.id).label("tag_count"),
        )
        .select_from(TPost)
        .outerjoin(post_tags, TPost.id == post_tags.c.post_id)
        .outerjoin(Tag, Tag.id == post_tags.c.tag_id)
        .group_by(TPost.id, TPost.title, TPost.status, TPost.owner_id)
    )


def _tag_rows_for_post_ids(post_ids: list[int]) -> dict[int, list[dict[str, str]]]:
    """Return tag labels for many posts in one query."""
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
    return {
        "id": post_id,
        "title": row["title"],
        "status": row["status"],
        "owner_id": row["owner_id"],
        "tag_count": int(row["tag_count"] or 0),
        "tags": tags_by_post.get(post_id, []),
    }


def post_list_payload(*, limit: int = 50) -> list[dict[str, Any]]:
    """Return list-ready post payloads with aggregate tag counts attached."""
    stmt = _post_base_select().order_by(TPost.id.asc()).limit(limit)
    rows = [dict(row) for row in db.session.execute(stmt).mappings().all()]

    post_ids = [int(row["id"]) for row in rows]
    tags_by_post = _tag_rows_for_post_ids(post_ids)

    return [_shape_post(row, tags_by_post) for row in rows]


def post_detail_payload(post_id: int) -> dict[str, Any] | None:
    """Return one post payload with aggregate counts, or None if missing."""
    stmt = _post_base_select().where(TPost.id == post_id)
    row = db.session.execute(stmt).mappings().first()

    if row is None:
        return None

    row_dict = dict(row)
    tags_by_post = _tag_rows_for_post_ids([int(row_dict["id"])])

    return _shape_post(row_dict, tags_by_post)