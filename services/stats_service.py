# =============================================================================
# Public + dashboard aggregate stats (counts, buckets, charts)
# =============================================================================
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Final

from sqlalchemy import func, select

from api.tags_models import Category, Interest, Post, Tag, User, db

_TOP_USERS_LIMIT: Final[int] = 10


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _normalize_day_key(day_val: object) -> str | None:
    if day_val is None:
        return None
    if isinstance(day_val, date):
        return day_val.isoformat()
    s = str(day_val).strip()
    return s[:10] if len(s) >= 10 else s


def _zero_fill_daily_counts(
    *,
    start: date,
    end: date,
    buckets: dict[str, int],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cur = start
    while cur <= end:
        k = cur.isoformat()
        out.append({"date": k, "count": int(buckets.get(k, 0))})
        cur += timedelta(days=1)
    return out


def _last_30_day_window(end_inclusive: date) -> tuple[date, date]:
    return end_inclusive - timedelta(days=29), end_inclusive


def daily_new_posts_trend_30(end_day: date | None = None) -> list[dict[str, Any]]:
    """Thirty UTC calendar dates inclusive; ``count`` = posts created on that UTC date."""
    end_d = end_day or _utc_today()
    start, incl_end = _last_30_day_window(end_d)

    grouped = db.session.execute(
        select(func.date(Post.timestamp), func.count(Post.id)).group_by(func.date(Post.timestamp))
    ).all()
    buckets: dict[str, int] = {}
    for dval, cnt in grouped:
        k = _normalize_day_key(dval)
        if k:
            buckets[k] = int(cnt or 0)

    return _zero_fill_daily_counts(start=start, end=incl_end, buckets=buckets)


def stats_public_payload(end_day: date | None = None) -> dict[str, Any]:
    """Shape matches ``docs/API_CONTRACTS.md`` § ``GET /api/stats``."""
    n_posts = int(db.session.scalar(select(func.count(Post.id))) or 0)
    n_users = int(db.session.scalar(select(func.count(User.id))) or 0)
    n_tags = int(db.session.scalar(select(func.count(Tag.id))) or 0)
    comments_sum = int(db.session.scalar(select(func.coalesce(func.sum(Post.comment_count), 0))) or 0)

    cat_rows = db.session.execute(
        select(Category.label, func.count(Post.id).label("cnt"))
        .select_from(Post)
        .join(Category, Post.category_id == Category.id)
        .group_by(Category.id, Category.label)
        .order_by(Category.label.asc(), Category.id.asc())
    ).all()

    trend_30 = daily_new_posts_trend_30(end_day)

    top_rows = db.session.execute(
        select(User.id, User.username, func.count(Post.id), func.coalesce(func.sum(Post.like_count), 0))
        .select_from(User)
        .outerjoin(Post, Post.owner_id == User.id)
        .group_by(User.id, User.username)
        .order_by(func.count(Post.id).desc(), func.coalesce(func.sum(Post.like_count), 0).desc())
        .limit(_TOP_USERS_LIMIT)
    ).all()

    top_users: list[dict[str, Any]] = []
    for uid, username, pc, tl in top_rows:
        disp = username if username else f"user-{uid}"
        top_users.append(
            {
                "username": disp,
                "post_count": int(pc or 0),
                "total_likes": int(tl or 0),
            }
        )

    return {
        "totals": {
            "posts": n_posts,
            "users": n_users,
            "comments": comments_sum,
            "tags": n_tags,
        },
        "category_counts": [{"label": str(lab), "count": int(cnt)} for lab, cnt in cat_rows],
        "trend_30": trend_30,
        "top_users": top_users,
    }


def dashboard_charts_payload(user_id: int, end_day: date | None = None) -> dict[str, Any]:
    """
    Logged-in poster mix + rolling 30-day activity.

    ``daily_activity.interests`` counts ``Interest`` rows on this user's listings per UTC date.
    ``daily_activity.likes`` is ``0``: there is no per-day like ledger; only ``Post.like_count``.
    """
    uid = int(user_id)
    end_d = end_day or _utc_today()
    start, incl_end = _last_30_day_window(end_d)

    cat_rows = db.session.execute(
        select(Category.label, func.count(Post.id).label("cnt"))
        .select_from(Post)
        .join(Category, Post.category_id == Category.id)
        .where(Post.owner_id == uid)
        .group_by(Category.id, Category.label)
        .order_by(Category.label.asc(), Category.id.asc())
    ).all()

    day_expr = func.date(Interest.timestamp)
    ire = db.session.execute(
        select(day_expr, func.count(Interest.id))
        .select_from(Interest)
        .join(Post, Interest.post_id == Post.id)
        .where(Post.owner_id == uid)
        .group_by(day_expr)
    ).all()
    ib: dict[str, int] = {}
    for dv, cnt in ire:
        k = _normalize_day_key(dv)
        if k:
            ib[k] = int(cnt or 0)

    daily_activity: list[dict[str, Any]] = []
    cur = start
    while cur <= incl_end:
        k = cur.isoformat()
        daily_activity.append(
            {
                "date": k,
                "likes": 0,
                "interests": int(ib.get(k, 0)),
            }
        )
        cur += timedelta(days=1)

    return {
        "category_distribution": [{"label": str(lab), "count": int(c)} for lab, c in cat_rows],
        "daily_activity": daily_activity,
    }
