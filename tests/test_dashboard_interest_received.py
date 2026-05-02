# =============================================================================
# Tests — GET /api/dashboard/interest-received + interest_received_rows helper
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager

from api.app_factory import create_app
from api.dashboard_interest_received import interest_received_rows
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
    u = User(id=n, email=f"u{n}@student.uwa.edu.au", username=f"user{n}")
    sess.add(u)
    sess.flush()
    return u


def _cat(sess, slug: str) -> Category:
    c = sess.scalar(select(Category).where(Category.slug == slug))
    assert c is not None
    return c


def _post(sess, owner: User, *, slug: str, title: str) -> Post:
    cid = int(_cat(sess, slug).id)
    p = Post(title=title, owner_id=owner.id, status="open", category_id=cid)
    sess.add(p)
    sess.flush()
    return p


class TestInterestReceivedApi(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_unauthenticated_401(self) -> None:
        r = self.client.get("/api/dashboard/interest-received")
        self.assertEqual(r.status_code, 401)

    def test_empty_when_no_interest_on_my_posts(self) -> None:
        with _session(self.app) as s:
            _user(s, 1)
        r = self.client.get("/api/dashboard/interest-received", headers={"X-User-Id": "1"})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertEqual(data["items"], [])
        self.assertEqual(data["meta"]["count"], 0)

    def test_shows_peer_who_interested_on_owner_listing(self) -> None:
        with _session(self.app) as s:
            owner = _user(s, 1)
            peer = _user(s, 2)
            p = _post(s, owner, slug="coding", title="Teach guitar")
            s.add(Interest(sender_id=peer.id, post_id=p.id))
            s.flush()

        r = self.client.get("/api/dashboard/interest-received", headers={"X-User-Id": "1"})
        self.assertEqual(r.status_code, 200)
        items = json.loads(r.get_data(as_text=True))["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["post"]["title"], "Teach guitar")
        self.assertEqual(items[0]["sender"]["id"], 2)
        self.assertIn("u2@", items[0]["sender"]["email"])

    def test_does_not_list_interest_i_sent_on_someone_elses_post(self) -> None:
        with _session(self.app) as s:
            alice = _user(s, 1)
            bob = _user(s, 2)
            bobs = _post(s, bob, slug="music", title="Piano intro")
            s.add(Interest(sender_id=alice.id, post_id=bobs.id))

        r = self.client.get("/api/dashboard/interest-received", headers={"X-User-Id": "1"})
        self.assertEqual(json.loads(r.get_data(as_text=True))["items"], [])

    def test_limit_query_clamped(self) -> None:
        with _session(self.app) as s:
            owner = _user(s, 1)
            peer = _user(s, 9)
            for i in range(3):
                p = _post(s, owner, slug="sports", title=f"Coach {i}")
                s.add(Interest(sender_id=peer.id, post_id=p.id))

        r = self.client.get("/api/dashboard/interest-received?limit=2", headers={"X-User-Id": "1"})
        data = json.loads(r.get_data(as_text=True))
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["meta"]["limit"], 2)


class TestInterestReceivedHelper(unittest.TestCase):
    def test_helper_matches_api_shape(self) -> None:
        app = create_app(testing=True)
        with _session(app) as s:
            o = _user(s, 44)
            q = _user(s, 55)
            p = _post(s, o, slug="communication", title="Debate club")
            s.add(Interest(sender_id=q.id, post_id=p.id))

        with app.app_context():
            rows = interest_received_rows(44, limit=10)
        self.assertEqual(len(rows), 1)
        self.assertIn("interest_id", rows[0])
        self.assertIn("post", rows[0])


if __name__ == "__main__":
    unittest.main()
