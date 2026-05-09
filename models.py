from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ------------------------------------------------------------------
# Association tables
# ------------------------------------------------------------------

post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id',  db.Integer, db.ForeignKey('tag.id'),  primary_key=True),
)

user_wanted_categories = db.Table(
    'user_wanted_categories',
    db.Column('user_id',     db.Integer, db.ForeignKey('user.id'),     primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True),
)


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

class Category(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    slug       = db.Column(db.String(40), unique=True, nullable=False)
    label      = db.Column(db.String(80), nullable=False)
    sort_order = db.Column(db.Integer, default=0)

    posts = db.relationship('Post', back_populates='category', lazy=True)


class Tag(db.Model):
    """Free-form tag added to a post (e.g. 'python', 'cits1401', 'beginner')."""
    id    = db.Column(db.Integer, primary_key=True)
    slug  = db.Column(db.String(50), unique=True, nullable=False)   # lowercase, url-safe
    label = db.Column(db.String(80), nullable=False)                 # display text (preserves original case)

    posts = db.relationship('Post', secondary=post_tags, back_populates='tags', lazy=True)


class Interest(db.Model):
    """Express interest in a post (sender + post + timestamp)."""
    id        = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id   = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class PostLike(db.Model):
    """Per-user like on a post (one like per user per post)."""
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id   = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='uq_post_like_user_post'),)


class Bookmark(db.Model):
    """Saved post / read-later for the current user."""
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id   = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='uq_bookmark_user_post'),)


class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    avatar_filename = db.Column(db.String(120), nullable=True)

    posts           = db.relationship('Post',     back_populates='author', lazy=True)
    interests_sent  = db.relationship('Interest', backref='sender',        lazy=True)
    saved_bookmarks = db.relationship('Bookmark', backref='user',          lazy=True, cascade='all, delete-orphan')
    post_likes      = db.relationship('PostLike', backref='user',          lazy=True, cascade='all, delete-orphan')
    wanted_categories = db.relationship('Category', secondary=user_wanted_categories, lazy=True)


class Post(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    title          = db.Column(db.String(100), nullable=False)
    description    = db.Column(db.Text,        nullable=False)
    timestamp      = db.Column(db.DateTime,    default=datetime.utcnow)
    user_id        = db.Column(db.Integer,     db.ForeignKey('user.id'),       nullable=False)
    category_id    = db.Column(db.Integer,     db.ForeignKey('category.id'),   nullable=False)
    image_filename = db.Column(db.String(120), nullable=True)
    comment_count  = db.Column(db.Integer,     nullable=False, default=0)
    like_count     = db.Column(db.Integer,     nullable=False, default=0)
    # Post lifecycle status: open | matched | closed
    status         = db.Column(db.String(20),  nullable=False, default='open')

    author          = db.relationship('User',     back_populates='posts')
    category        = db.relationship('Category', back_populates='posts')
    comments        = db.relationship('Comment',  backref='post',     lazy=True, cascade='all, delete-orphan')
    interested_users = db.relationship('Interest', backref='post_ref', lazy=True)
    bookmarks       = db.relationship('Bookmark', backref='post',     lazy=True, cascade='all, delete-orphan')
    likes           = db.relationship('PostLike', backref='post',     lazy=True, cascade='all, delete-orphan')
    tags            = db.relationship('Tag',      secondary=post_tags, back_populates='posts', lazy=True)


class Comment(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    content   = db.Column(db.Text,    nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id   = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    user = db.relationship('User', backref='comments')


class Message(db.Model):
    """Private direct message between two users."""
    id           = db.Column(db.Integer,  primary_key=True)
    sender_id    = db.Column(db.Integer,  db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer,  db.ForeignKey('user.id'), nullable=False)
    content      = db.Column(db.Text,     nullable=False)
    read         = db.Column(db.Boolean,  nullable=False, default=False)
    timestamp    = db.Column(db.DateTime, default=datetime.utcnow)

    sender    = db.relationship('User', foreign_keys=[sender_id],    backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')


class Notification(db.Model):
    """@mention notification delivered to a user."""
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)   # recipient
    actor_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)   # author of comment
    post_id    = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    notif_type = db.Column(db.String(20), nullable=False, default='mention')
    read       = db.Column(db.Boolean,  nullable=False, default=False)
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)
    # Avatar is intentionally not stored here — access it via notification.actor.avatar_filename
    # so that it always reflects the actor's current profile picture.

    recipient = db.relationship('User',    foreign_keys=[user_id], backref='notifications')
    actor     = db.relationship('User',    foreign_keys=[actor_id])
    post      = db.relationship('Post',    foreign_keys=[post_id])
    comment   = db.relationship('Comment', foreign_keys=[comment_id])
