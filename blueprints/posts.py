# =============================================================================
# Blueprint: posts — create flow, HTML + JSON detail, lifecycle (set-status)
# =============================================================================
from __future__ import annotations

import os
from flask import (
    Blueprint,
    Flask,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    url_for,
)
from werkzeug.datastructures import FileStorage

from api.post_cover_upload import DEFAULT_MAX_BYTES, save_post_cover_image
from flask_login import current_user, login_required
from sqlalchemy import select

from api.post_aggregates import post_detail_payload, post_list_payload
from api.post_status import bp as post_status_slice
from api.tags_models import (
    POST_STATUS_CLOSED,
    POST_STATUS_MATCHED,
    POST_STATUS_OPEN,
    Category,
    Post,
    Tag,
    User,
    db,
)
from api.taxonomy_helpers import normalize_tag_slug
from post_forms import CreatePostForm

bp = Blueprint(
    "posts",
    __name__,
    url_prefix="/posts",
    template_folder="../templates",
)

_LIFECYCLE_BADGE_META: dict[str, tuple[str, str]] = {
    POST_STATUS_OPEN: ("text-bg-success", "Open"),
    POST_STATUS_MATCHED: ("text-bg-info", "Matched"),
    POST_STATUS_CLOSED: ("text-bg-secondary", "Closed"),
}


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


def _author_display(owner: User | None) -> str:
    if owner is None:
        return "Anonymous"
    if owner.username and str(owner.username).strip():
        return str(owner.username).strip()
    em = owner.email or ""
    if em and "@" in em:
        return em.split("@", 1)[0]
    return f"Member #{owner.id}"


def _lifecycle_bootstrap_pair(status: str | None) -> tuple[str, str]:
    raw = status or POST_STATUS_OPEN
    st = raw.strip().lower()
    if st in _LIFECYCLE_BADGE_META:
        return _LIFECYCLE_BADGE_META[st]
    pretty = raw.strip().title() if isinstance(raw, str) and raw.strip() else st.title()
    return ("text-bg-warning", pretty[:28])


def _post_detail_surface(post_id: int) -> dict | None:
    """ORM snapshot packaged for ``post_detail.html``."""
    post = db.session.get(Post, post_id)
    if post is None:
        return None

    cat = post.category
    tags = sorted(post.tags, key=lambda t: (str(t.label).lower(), str(t.slug).lower()))

    badge_class, badge_label = _lifecycle_bootstrap_pair(post.status)
    ts = post.timestamp
    posted_at_human = ts.strftime("%d %b %Y · %H:%M UTC") if ts is not None else None

    return {
        "post": post,
        "category": cat,
        "tags": tags,
        "author_label": _author_display(post.owner),
        "badge_class": badge_class,
        "badge_label": badge_label,
        "posted_at_human": posted_at_human,
    }


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

        post_obj = Post(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            category_id=int(form.category_id.data),
            owner_id=int(current_user.get_id()),
            status=POST_STATUS_OPEN,
            image_filename=None,
            image_alt=None,
        )
        fs = form.cover_image.data
        has_cover = isinstance(fs, FileStorage) and bool(fs.filename)
        alt_stripped = (form.image_alt.data or "").strip()
        if alt_stripped and not has_cover:
            flash("Add a cover image before entering image description text.", "warning")
            return render_template("create_post.html", form=form)

        if has_cover:
            upload_dir = current_app.config.get("POST_COVER_UPLOAD_DIR")
            if not upload_dir:
                upload_dir = os.path.join(current_app.static_folder, "uploads", "posts")
            max_b = int(current_app.config.get("MAX_POST_IMAGE_BYTES", DEFAULT_MAX_BYTES))
            saved_fn, up_err = save_post_cover_image(fs.stream, upload_dir=upload_dir, max_bytes=max_b)
            if up_err:
                flash(up_err, "danger")
                return render_template("create_post.html", form=form)
            post_obj.image_filename = saved_fn
            post_obj.image_alt = alt_stripped[:200] if alt_stripped else None

        db.session.add(post_obj)
        db.session.flush()
        _sync_post_tags(post_obj, form.tags.data)

        db.session.commit()
        flash('Your listing is published. You can bookmark this page.', "success")
        return redirect(url_for("posts.post_detail_html", post_id=post_obj.id))

    return render_template("create_post.html", form=form)


@bp.get("/")
def list_posts_stub():
    return jsonify(
        {
            "items": post_list_payload(),
            "module": "posts",
        }
    )


@bp.get("/<int:post_id>/json")
def post_detail_json(post_id: int):
    """Aggregate-shaped JSON for AJAX, tests, and discover clients."""
    payload = post_detail_payload(post_id)
    if payload is None:
        return jsonify({"message": "Post not found"}), 404

    return jsonify(payload)


@bp.get("/<int:post_id>")
def post_detail_html(post_id: int):
    """Listing detail: category label, lifecycle badge, tag pills, prose body."""
    surface = _post_detail_surface(post_id)
    if surface is None:
        return render_template("post_not_found.html"), 404
    return render_template("post_detail.html", **surface)


def register_posts_blueprints(app: Flask) -> None:
    """Register posts blueprint plus ``POST /post/set-status`` slice."""
    app.register_blueprint(bp)
    app.register_blueprint(post_status_slice)
