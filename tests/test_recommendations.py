# =============================================================================
# Tests — GET /api/dashboard/recommendations
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager

from api.app_factory import create_app
from api.tags_models import Category, Interest, Post, User, db
from sqlalchemy import select


@contextmanager
def _session(app):
    with app.app_context():
        try:
            yield db.session
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            raise


def _user(sess, n: int) -> User:
    u = User(id=n, email=f"u{n}@student.uwa.edu.au")
    sess.add(u)
    sess.flush()
    return u


def _cat(sess, slug: str) -> Category:
    c = sess.scalar(select(Category).where(Category.slug == slug))
    assert c is not None
    return c


def _post(sess, owner: User, *, slug: str, title: str, status: str = "open") -> Post:
    cid = int(_cat(sess, slug).id)
    p = Post(title=title, owner_id=owner.id, status=status, category_id=cid)
    sess.add(p)
    sess.flush()
    return p


def _j(resp):
    return json.loads(resp.get_data(as_text=True))


class TestRecommendationsApi(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_requires_identity(self) -> None:
        r = self.client.get("/api/dashboard/recommendations")
        self.assertEqual(r.status_code, 401)

    def test_respects_wanted_categories_and_excludes_own(self) -> None:
        with _session(self.app) as s:
            u1 = _user(s, 1)
            u2 = _user(s, 2)
            coding = _cat(s, "coding")
            u1.wanted_categories.append(coding)
            p_peer = _post(s, u2, slug="coding", title="Learn Python")
            _post(s, u1, slug="coding", title="My own tutoring offer")

        r = self.client.get("/api/dashboard/recommendations", headers={"X-User-Id": "1"})
        self.assertEqual(r.status_code, 200)
        body = _j(r)
        titles = {p["title"] for p in body["posts"]}
        self.assertIn("Learn Python", titles)
        self.assertNotIn("My own tutoring offer", titles)
        self.assertEqual(body["meta"]["count"], 1)

    def test_excludes_already_interested_posts(self) -> None:
        with _session(self.app) as s:
            u1 = _user(s, 1)
            u2 = _user(s, 2)
            coding = _cat(s, "coding")
            u1.wanted_categories.append(coding)
            p_peer = _post(s, u2, slug="coding", title="Excluded after interest")
            s.add(Interest(sender_id=u1.id, post_id=p_peer.id))
            s.flush()

        r = self.client.get("/api/dashboard/recommendations", headers={"X-User-Id": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(_j(r)["posts"], [])

    def test_skips_closed_status(self) -> None:
        with _session(self.app) as s:
            u1 = _user(s, 1)
            u2 = _user(s, 2)
            music = _cat(s, "music")
            u1.wanted_categories.append(music)
            _post(s, u2, slug="music", title="Closed slot", status="closed")

        r = self.client.get("/api/dashboard/recommendations", headers={"X-User-Id": "1"})
        self.assertEqual(_j(r)["posts"], [])


if __name__ == "__main__":
    unittest.main()
