# =============================================================================
# GET/POST /api/dashboard/wanted  — persisted wanted-category list for dashboard
# =============================================================================
from __future__ import annotations

from flask import Blueprint, jsonify, request

from api.auth_identity import effective_user_id
from api.dashboard_interest_received import clamp_interest_received_limit, interest_received_rows
from api.recommendations import clamp_recommendation_limit, recommended_post_payloads
from api.tags_models import Category, User, db
from services.notification_service import count_unread_notifications, mark_all_notifications_read

bp = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")


@bp.get("/wanted")
def get_wanted():
    uid = effective_user_id()
    if uid is None:
        return jsonify({"message": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if user is None:
        return jsonify({"message": "User not found"}), 404

    cats = Category.query.order_by(Category.sort_order, Category.id).all()
    wanted_ids = sorted({c.id for c in user.wanted_categories})

    return jsonify(
        {
            "categories": [{"id": c.id, "slug": c.slug, "label": c.label} for c in cats],
            "wanted_ids": wanted_ids,
        }
    )


@bp.post("/wanted")
def save_wanted():
    """Replace the caller's wanted category set from JSON { \"category_ids\": [ ... ] }."""
    uid = effective_user_id()
    if uid is None:
        return jsonify({"message": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if user is None:
        return jsonify({"message": "User not found"}), 404

    if not request.is_json:
        return jsonify({"message": "application/json expected"}), 400

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"message": "JSON object expected"}), 400

    cat_ids_raw = payload.get("category_ids", [])
    if cat_ids_raw is None:
        cat_ids_raw = []
    if not isinstance(cat_ids_raw, list):
        return jsonify({"message": "category_ids must be a list"}), 400

    ids: list[int] = []
    for item in cat_ids_raw:
        if isinstance(item, int):
            ids.append(item)
        elif isinstance(item, str) and item.strip().isdigit():
            ids.append(int(item.strip()))
        else:
            return jsonify({"message": "category_ids must contain integers"}), 400

    uniq = sorted(set(ids))
    if not uniq:
        user.wanted_categories = []
    else:
        user.wanted_categories = Category.query.filter(Category.id.in_(uniq)).all()
    db.session.add(user)
    db.session.commit()

    return jsonify({"ok": True, "count": len(user.wanted_categories)})


@bp.get("/recommendations")
def get_recommendations():
    uid = effective_user_id()
    if uid is None:
        return jsonify({"message": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if user is None:
        return jsonify({"message": "User not found"}), 404

    lim = clamp_recommendation_limit(request.args.get("limit", type=int))
    posts = recommended_post_payloads(uid, limit=lim)

    return jsonify({"posts": posts, "meta": {"count": len(posts), "limit": lim}})


@bp.get("/interest-received")
def get_interest_received():
    """Summaries of users who expressed interest on posts owned by the caller."""
    uid = effective_user_id()
    if uid is None:
        return jsonify({"message": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if user is None:
        return jsonify({"message": "User not found"}), 404

    lim = clamp_interest_received_limit(request.args.get("limit", type=int))
    items = interest_received_rows(uid, limit=lim)

    return jsonify({"items": items, "meta": {"count": len(items), "limit": lim}})


@bp.get("/notifications/unread-count")
def notifications_unread_count():
    uid = effective_user_id()
    if uid is None:
        return jsonify({"message": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if user is None:
        return jsonify({"message": "User not found"}), 404

    n = count_unread_notifications(uid)
    return jsonify({"unread_count": n})


@bp.post("/notifications/mark-all-read")
def notifications_mark_all_read():
    """Mark all inbox notifications read; response includes fresh ``unread_count`` (0)."""
    uid = effective_user_id()
    if uid is None:
        return jsonify({"message": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if user is None:
        return jsonify({"message": "User not found"}), 404

    marked, unread_after = mark_all_notifications_read(uid)
    return jsonify({"ok": True, "marked": marked, "unread_count": unread_after})

