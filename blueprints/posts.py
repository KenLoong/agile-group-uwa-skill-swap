# =============================================================================
# Blueprint: posts  — listings, create flow, lifecycle (set-status)
# =============================================================================
# Create-post honours Flask-Login; list/detail stubs stay JSON-first until HTML
# detail rendering ships in its own issue.
# =============================================================================
from __future__ import annotations

from flask import Blueprint, Flask, flash, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from api.post_aggregates import post_detail_payload, post_list_payload
from api.post_status import bp as post_status_slice
from api.tags_models import Category, POST_STATUS_OPEN, Post, Tag, db
from api.taxonomy_helpers import normalize_tag_slug
from post_forms import CreatePostForm

bp = Blueprint(
    "posts",
    __name__,
    url_prefix="/posts",
    template_folder="../templates",
)


def _category_choices() -> list[tuple[int, str]]:
    rows = Category.query.order_by(Category.sort_order, Category.id).all()
    return [(int(r.id), r.label) for r in rows]


def _sync_post_tags(post: Post, tags_raw: str | None) -> None:
    """Parse comma-separated tags; reuse Tag rows by slug; attach via post_tags."""
    if not tags_raw or not isinstance(tags_raw, str):
        return

    sess = db.session
    seen: set[str] = set()

    for raw in tags_raw.split(","):
        label = raw.strip()
        if not label:
            continue
        slug = normalize_tag_slug(label)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        display = label[:80]
        tag = sess.scalar(select(Tag).where(Tag.slug == slug))
        if tag is None:
            tag = Tag(slug=slug, label=display)
            sess.add(tag)
            sess.flush()
        if tag not in post.tags:
            post.tags.append(tag)


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_skill_post():
    form = CreatePostForm()
    form.category_id.choices = _category_choices()

    if not form.category_id.choices:
        flash("No categories configured yet.", "danger")
        return render_template("create_post.html", form=form)

    if form.validate_on_submit():
        cid_ok = Category.query.filter_by(id=int(form.category_id.data)).first()
        if cid_ok is None:
            flash("That category does not exist. Pick another.", "warning")
            return render_template("create_post.html", form=form)

        post = Post(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            category_id=int(form.category_id.data),
            owner_id=int(current_user.get_id()),
            status=POST_STATUS_OPEN,
        )
        db.session.add(post)
        db.session.flush()
        _sync_post_tags(post, form.tags.data)

        db.session.commit()
        flash(
            f'Published post #{post.id}. Open `/posts/{post.id}` for machine-readable JSON until the HTML '
            "detail page ships.",
            "success",
        )
        return redirect(url_for("posts.create_skill_post"))

    return render_template("create_post.html", form=form)


@bp.get("/")
def list_posts_stub():
    return jsonify(
        {
            "items": post_list_payload(),
            "module": "posts",
        }
    )


@bp.get("/<int:post_id>")
def get_post_stub(post_id: int):
    payload = post_detail_payload(post_id)

    if payload is None:
        return jsonify({"message": "Post not found"}), 404

    return jsonify(payload)


def register_posts_blueprints(app: Flask) -> None:
    """
    Register HTML/JSON `posts` blueprint plus the post_status slice
    (`POST /post/set-status`).
    """
    app.register_blueprint(bp)
    app.register_blueprint(post_status_slice)
