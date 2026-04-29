# =============================================================================
# Minimal SQLAlchemy models for /api/tags tests (isolated from full app merge)
# =============================================================================
from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select

db = SQLAlchemy()

# Valid values for TPost.status (set via POST /post/set-status)
POST_STATUS_OPEN = "open"
POST_STATUS_MATCHED = "matched"
POST_STATUS_CLOSED = "closed"
POST_STATUS_VALUES = frozenset(
    {POST_STATUS_OPEN, POST_STATUS_MATCHED, POST_STATUS_CLOSED}
)

post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("t_post.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("t_tag.id"), primary_key=True),
)


class Tag(db.Model):
    __tablename__ = "t_tag"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(80), nullable=False)
    posts = db.relationship("TPost", secondary=post_tags, back_populates="tags")


class User(db.Model):
    """Lightweight user row for post ownership checks in API slice tests."""

    __tablename__ = "t_user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), default="u@uwa")
    posts_owned = db.relationship("TPost", back_populates="owner", foreign_keys="TPost.owner_id")


class TPost(db.Model):
    """Narrow post model for tag counting only; full Post merged later from draft repo."""

    __tablename__ = "t_post"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), default="t")
    owner_id = db.Column(db.Integer, db.ForeignKey("t_user.id"), nullable=True, index=True)
    status = db.Column(db.String(20), default=POST_STATUS_OPEN, nullable=False)
    tags = db.relationship("Tag", secondary=post_tags, back_populates="posts")
    owner = db.relationship("User", back_populates="posts_owned", foreign_keys=[owner_id])


def tag_payload_rows():
    """
    One SQL shape for the JSON the discover page expects.

    Returns rows: (slug, label, post_count) ordered by label ASC for stable tests.
    Tags with **zero** posts are omitted (INNER join).
    """
    stmt = (
        select(Tag.slug, Tag.label, func.count(TPost.id).label("cnt"))
        .join(TPost, Tag.posts)
        .group_by(Tag.id, Tag.slug, Tag.label)
        .order_by(Tag.label.asc(), Tag.slug.asc())
    )
    return db.session.execute(stmt).mappings().all()
