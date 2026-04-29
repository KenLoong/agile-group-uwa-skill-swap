# =============================================================================
# Post, Category, Tag, and association baseline (aligned with project draft repo)
# =============================================================================
from __future__ import annotations

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select

db = SQLAlchemy()

# Valid Post.status values (POST /post/set-status)
POST_STATUS_OPEN = "open"
POST_STATUS_MATCHED = "matched"
POST_STATUS_CLOSED = "closed"
POST_STATUS_VALUES = frozenset(
    {POST_STATUS_OPEN, POST_STATUS_MATCHED, POST_STATUS_CLOSED}
)

post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("post.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    label = db.Column(db.String(80), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    posts = db.relationship("Post", back_populates="category", lazy=True)


class Tag(db.Model):
    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(80), nullable=False)

    posts = db.relationship("Post", secondary=post_tags, back_populates="tags")


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), default="u@uwa")

    posts_owned = db.relationship(
        "Post", back_populates="owner", foreign_keys="Post.owner_id"
    )


class Post(db.Model):
    """Skill listing: FK to Category (required); optional owner FK for lifecycle APIs."""

    __tablename__ = "post"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)

    category = db.relationship("Category", back_populates="posts")
    tags = db.relationship("Tag", secondary=post_tags, back_populates="posts")
    owner = db.relationship("User", back_populates="posts_owned", foreign_keys=[owner_id])
    status = db.Column(db.String(20), default=POST_STATUS_OPEN, nullable=False)


def ensure_default_taxonomy() -> None:
    """Ensure at least one category exists so new Post rows can satisfy category_id FK."""
    n = db.session.scalar(select(func.count(Category.id)))
    if n:
        return
    db.session.add(Category(slug="general", label="General", sort_order=0))
    db.session.commit()


def tag_payload_rows():
    """
    One SQL shape for the JSON the discover page expects.

    Returns rows: (slug, label, post_count) ordered by label ASC for stable tests.
    Tags with zero posts are omitted (INNER join semantics).
    """
    stmt = (
        select(Tag.slug, Tag.label, func.count(Post.id).label("cnt"))
        .join(Post, Tag.posts)
        .group_by(Tag.id, Tag.slug, Tag.label)
        .order_by(Tag.label.asc(), Tag.slug.asc())
    )
    return db.session.execute(stmt).mappings().all()
