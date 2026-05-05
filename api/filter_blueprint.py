# =============================================================================
# GET /api/filter  — Discover page JSON (category, tag, search, sort, pagination)
# =============================================================================
# Mirrors docs/API_CONTRACTS.md and demo-for-agile-develop behaviour. Owned by
# Posts & Discovery; registered alongside other /api/* blueprints.
#
# Discover sort ORDER BY tuples live in ``api.discover_ordering``.
# Search alias precedence + pagination clamping live in ``api.filter_params``.
# =============================================================================
from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request, url_for
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from api.filter_params import normalized_search_expression, paginate_filter_results
from api.discover_ordering import apply_discover_sort
from api.tags_models import Category, Post, Tag, db

bp = Blueprint("discover_filter", __name__, url_prefix="/api")

_PER_PAGE_DEFAULT = 9

_SORT_ALLOWED = frozenset({"newest", "popular", "likes"})


def _normalize_sort(raw: object) -> str:
    if isinstance(raw, str) and raw.strip().lower() in _SORT_ALLOWED:
        return raw.strip().lower()
    return "newest"


def _normalize_page(raw: object) -> int:
    default = 1
    try:
        p = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return p if p >= 1 else default


def _snippet(description: str, max_len: int = 120) -> str:
    if not description:
        return ""
    collapsed = " ".join(description.replace("\r", "").split())
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 1] + "…"


def _author_handle(owner: Any) -> tuple[str, str]:
    if owner is None:
        return "", ""
    username = str(getattr(owner, "username", "") or "")
    if username:
        return username, f"/user/{username}"
    return "", ""


def post_to_discover_card(post: Post) -> dict[str, Any]:
    """Single card object for `/api/filter` response body."""
    author, profile = _author_handle(post.owner)

    ts = post.timestamp
    stamp = ts.strftime("%Y-%m-%d") if isinstance(ts, datetime) else ""

    tags = sorted(
        post.tags,
        key=lambda t: (str(t.label).lower(), str(t.slug)),
    )

    img = (
        url_for("static", filename=f"uploads/posts/{post.image_filename}")
        if post.image_filename
        else None
    )
    alt = None
    if post.image_filename:
        raw = (getattr(post, "image_alt", None) or "").strip()
        alt = raw or None

    return {
        "id": int(post.id),
        "title": post.title or "",
        "category_slug": post.category.slug if post.category else "",
        "category_label": post.category.label if post.category else "",
        "author": author,
        "author_profile": profile,
        "snippet": _snippet(post.description),
        "timestamp": stamp,
        "comment_count": int(post.comment_count or 0),
        "like_count": int(post.like_count or 0),
        "status": str(post.status or "open"),
        "tags": [{"slug": str(t.slug), "label": str(t.label)} for t in tags],
        "image_url": img,
        "image_alt": alt,
    }


def discover_filter_query(
    *,
    category_slug_raw: str | None,
    tag_slug_raw: str | None,
    search_query_raw: str | None,
    sort: str,
):
    """Return unscored queryset (Flask-SQLAlchemy) with filters applied."""
    q = Post.query

    cat_param = (category_slug_raw or "all").strip().lower()
    if cat_param and cat_param != "all":
        cat = Category.query.filter_by(slug=cat_param).first()
        if cat is None:
            return Post.query.filter(Post.id == -1), True  # empty sentinel
        q = q.filter(Post.category_id == cat.id)

    tag_param = (tag_slug_raw or "").strip().lower()
    if tag_param:
        q = q.filter(Post.tags.any(Tag.slug == tag_param))

    q_text = (search_query_raw or "").strip()
    if q_text:
        like = f"%{q_text}%"
        q = q.filter(or_(Post.title.ilike(like), Post.description.ilike(like)))

    q = apply_discover_sort(q, sort)

    return q.options(
        joinedload(Post.category),
        joinedload(Post.owner),
        joinedload(Post.tags),
    ), False


@bp.get("/filter")
def filter_posts():
    sort = _normalize_sort(request.args.get("sort"))
    page = _normalize_page(request.args.get("page"))
    category_slug = request.args.get("category", "all") or "all"
    tag_slug = request.args.get("tag", "") or ""
    query_txt = normalized_search_expression(request)

    base, empty_miss = discover_filter_query(
        category_slug_raw=category_slug,
        tag_slug_raw=tag_slug,
        search_query_raw=query_txt,
        sort=sort,
    )

    if empty_miss:
        payload = {
            "posts": [],
            "page": 1,
            "pages": 0,
            "total": 0,
            "has_next": False,
            "has_prev": False,
        }
        resp = jsonify(payload)
        resp.headers["Cache-Control"] = "public, max-age=15"
        return resp, 200

    pag = paginate_filter_results(base, page=page, per_page=_PER_PAGE_DEFAULT)
    rows = pag.items

    out = jsonify(
        {
            "posts": [post_to_discover_card(p) for p in rows],
            "page": pag.page,
            "pages": pag.pages,
            "total": int(pag.total or 0),
            "has_next": pag.has_next,
            "has_prev": pag.has_prev,
        }
    )
    out.headers["Cache-Control"] = "public, max-age=15"
    return out, 200
