# =============================================================================
# Blueprint: dashboard  — logged-in dashboard shell + wanted-category UI
# =============================================================================
from __future__ import annotations

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from api.tags_models import Category, User, db

bp = Blueprint("dashboard_page", __name__)


@bp.get("/dashboard")
@login_required
def dashboard():
    all_cats = Category.query.order_by(Category.sort_order, Category.id).all()
    uid = int(current_user.get_id())
    user = db.session.get(User, uid)
    if user is None:
        abort(404)
    wanted_ids = {c.id for c in user.wanted_categories}
    return render_template(
        "dashboard.html",
        all_cats=all_cats,
        wanted_ids=wanted_ids,
        save_url="/api/dashboard/wanted",
    )
