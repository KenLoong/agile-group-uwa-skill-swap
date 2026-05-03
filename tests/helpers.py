import json
import unittest
from contextlib import contextmanager
from typing import Any

from api.app_factory import create_app
from api.tags_models import CATEGORY_SLUG_GENERAL, Category, Post, User, db
from sqlalchemy import select


class BaseTestCase(unittest.TestCase):
    """
    Base class for all application tests.
    Sets up the Flask app in testing mode, creating a fresh in-memory SQLite
    database and applying the default category seeds for each test.
    """
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        # Expose app_context so tests don't have to repeatedly use with self.app.app_context():
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        db.session.remove()
        self.app_context.pop()


@contextmanager
def session_scope(app):
    """
    Context manager to easily scope database session operations.
    Automatically commits on success, and rollbacks on exception.
    """
    with app.app_context():
        try:
            yield db.session
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise


def create_test_user(sess, n: int = 1, email_confirmed: bool = True) -> User:
    """Helper to cleanly instantiate and persist a test user."""
    u = User(
        id=n,
        email=f"u{n}@student.uwa.edu.au",
        username=f"u{n}",
        password_hash="test_hash",
        email_confirmed=email_confirmed
    )
    sess.add(u)
    sess.flush()
    return u


def create_test_post(sess, owner: User, title: str = "skill", status: str = "open") -> Post:
    """Helper to cleanly instantiate and persist a test post under the general category."""
    cid = sess.scalar(select(Category.id).where(Category.slug == CATEGORY_SLUG_GENERAL))
    if not cid:
        c = Category(slug=CATEGORY_SLUG_GENERAL, label="General", sort_order=0)
        sess.add(c)
        sess.flush()
        cid = c.id
        
    p = Post(title=title, owner_id=owner.id, status=status, category_id=cid)
    sess.add(p)
    sess.flush()
    return p


def get_json(resp) -> dict[str, Any]:
    """Helper to parse JSON from a response object."""
    return json.loads(resp.get_data(as_text=True))
