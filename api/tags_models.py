# =============================================================================
# Post, Category, Tag, and association baseline (aligned with project draft repo)
# =============================================================================
# Central place for discover/listing domain tables: category taxonomy, post
# rows (with lifecycle), free-form tags, post_tags M2M, dashboard wanted prefs.
# Application code treats this module as the single source of truth for column
# names and foreign keys ahead of Flask-Migrate history in later sprints.
# =============================================================================
from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select

db = SQLAlchemy()

user_wanted_categories = db.Table(
    "user_wanted_categories",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("category.id"), primary_key=True),
)

# Valid values for Post.status (POST /post/set-status)
POST_STATUS_OPEN = "open"
POST_STATUS_MATCHED = "matched"
POST_STATUS_CLOSED = "closed"
POST_STATUS_VALUES = frozenset(
    {POST_STATUS_OPEN, POST_STATUS_MATCHED, POST_STATUS_CLOSED}
)

# Fallback category slug used when nothing else exists (FK bootstrap).
CATEGORY_SLUG_GENERAL = "general"


# ---------------------------------------------------------------------------
# Association tables — post ⇄ tags
# ---------------------------------------------------------------------------
post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("post.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class Category(db.Model):
    """
    Skill taxonomy row: discover grouping and dashboard wanted-category picks.
    Posts must reference exactly one category.
    """

    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    label = db.Column(db.String(80), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    posts = db.relationship("Post", back_populates="category", lazy=True)

    def __repr__(self) -> str:
        return f"<Category {self.slug!r} id={self.id}>"


class Tag(db.Model):
    """
    Free-form keyword attached to posts (many-to-many via post_tags).

    slug — URL-stable; label — preserves display casing for UI chips.
    """

    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    label = db.Column(db.String(80), nullable=False)

    posts = db.relationship("Post", secondary=post_tags, back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag {self.slug!r} id={self.id}>"


class User(UserMixin, db.Model):
    """
    User row backing Flask-Login, post ownership, and dashboard wanted categories.

    Matches table name ``user`` (SQLite quotes reserved identifiers as needed).
    """

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), default="u@uwa")
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)

    posts_owned = db.relationship(
        "Post",
        back_populates="owner",
        foreign_keys="Post.owner_id",
    )
    wanted_categories = db.relationship(
        "Category",
        secondary=user_wanted_categories,
        lazy=True,
    )
    interests_sent = db.relationship(
        "Interest",
        foreign_keys="Interest.sender_id",
        lazy=True,
        back_populates="sender",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class Post(db.Model):
    """
    Skill swap listing owned by optional User, filed under mandatory Category.

    Includes optional engagement counters (denormalised) and lifecycle status
    for dashboard / discover views.
    """

    __tablename__ = "post"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)

    image_filename = db.Column(db.String(120), nullable=True)
    comment_count = db.Column(db.Integer, nullable=False, default=0)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), default=POST_STATUS_OPEN, nullable=False)

    category = db.relationship("Category", back_populates="posts")
    tags = db.relationship("Tag", secondary=post_tags, back_populates="posts", lazy=True)
    owner = db.relationship("User", back_populates="posts_owned", foreign_keys=[owner_id])
    interests_received = db.relationship(
        "Interest",
        foreign_keys="Interest.post_id",
        lazy=True,
        back_populates="post",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Post id={self.id} title={self.title[:32]!r} "
            f"status={self.status!r} category_id={self.category_id}>"
        )


class Interest(db.Model):
    """
    User expressed interest on another user's listing — used by recommendations
    to exclude duplicates and later for interest-received dashboard views.
    """

    __tablename__ = "interest"
    __table_args__ = (db.UniqueConstraint("sender_id", "post_id", name="uq_interest_sender_post"),)

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship("User", foreign_keys=[sender_id], back_populates="interests_sent")
    post = db.relationship("Post", foreign_keys=[post_id], back_populates="interests_received")


def ensure_default_taxonomy() -> None:
    """
    Insert only ``general`` when the category table is empty (tests / tooling).

    Application startup normally uses ``_seed_categories_if_empty()`` in ``app``
    instead, which also adds discover/dashboard defaults.
    """
    n = db.session.scalar(select(func.count(Category.id)))
    if n:
        return
    db.session.add(
        Category(
            slug=CATEGORY_SLUG_GENERAL,
            label="General",
            sort_order=0,
        )
    )
    db.session.commit()


def category_id_for_slug(slug: str) -> int | None:
    """Return primary key for slug or ``None`` if absent or malformed input."""
    if not slug or not isinstance(slug, str):
        return None
    normal = slug.strip().lower()
    if not normal:
        return None
    cid = db.session.scalar(select(Category.id).where(Category.slug == normal))
    return int(cid) if cid is not None else None


def tag_payload_rows():
    """
    One SQL shape for the JSON the discover page expects.

    Returns rows mapping keys: slug, label, cnt (post_count) ordered by label.
    Tags with zero linked posts are omitted (INNER join semantics).
    """
    stmt = (
        select(Tag.slug, Tag.label, func.count(Post.id).label("cnt"))
        .join(Post, Tag.posts)
        .group_by(Tag.id, Tag.slug, Tag.label)
        .order_by(Tag.label.asc(), Tag.slug.asc())
    )
    return db.session.execute(stmt).mappings().all()
