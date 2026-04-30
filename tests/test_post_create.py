# =============================================================================
# Tests — create post (GET form + POST persist + tags), Flask-Login session
# =============================================================================
from __future__ import annotations

import json
import re
import unittest
from html import unescape

from api.app_factory import create_app
from api.tags_models import CATEGORY_SLUG_GENERAL, Category, Post, User, db
from sqlalchemy import select


class TestPostCreate(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_guest_redirected_from_create(self) -> None:
        r = self.client.get("/posts/create", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        loc = unescape(r.headers.get("Location", ""))
        self.assertIn("/auth/login", loc)

    def test_create_post_logged_in_persists_tags(self) -> None:
        uid = self._seed_user_login()
        with self.app.app_context():
            cid = db.session.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None

        csrf = self._csrf_token()
        r_post = self.client.post(
            "/posts/create",
            data={
                "csrf_token": csrf,
                "title": " Peer tutoring calculus ",
                "category_id": str(int(cid)),
                "description": "Second-year calculus help Thursdays.",
                "tags": " calculus, calculus , MATH ",
                "submit": "Publish skill post",
            },
            follow_redirects=False,
        )
        self.assertEqual(r_post.status_code, 302)
        rv = self.client.get("/posts/create")
        body = rv.get_data(as_text=True)
        self.assertRegex(body, r"Published post #\d+", msg="Expected success flash")

        with self.app.app_context():
            p = db.session.scalar(
                select(Post).where(Post.owner_id == uid, Post.title == "Peer tutoring calculus")
            )
            self.assertIsNotNone(p)
            assert p is not None
            self.assertEqual(p.category_id, int(cid))
            self.assertEqual(p.status, "open")
            slug_rows = sorted(t.slug for t in p.tags)
            self.assertEqual(slug_rows, ["calculus", "math"])

    def test_empty_title_shows_validation(self) -> None:
        self._seed_user_login()
        with self.app.app_context():
            cid = db.session.scalar(select(Category.id).where(Category.slug == CATEGORY_SLUG_GENERAL))
            assert cid is not None

        csrf = self._csrf_token()
        r = self.client.post(
            "/posts/create",
            data={
                "csrf_token": csrf,
                "title": "",
                "category_id": str(int(cid)),
                "description": "Something here.",
                "tags": "",
                "submit": "Publish skill post",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Give your post a short title", r.get_data())

    def _csrf_token(self) -> str:
        r = self.client.get("/posts/create")
        self.assertEqual(r.status_code, 200)
        txt = r.get_data(as_text=True)
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', txt)
        if m is None:
            m = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', txt)
        self.assertIsNotNone(m)
        assert m is not None
        return m.group(1)

    def _seed_user_login(self) -> int:
        with self.app.app_context():
            u = User(id=42, email="student@student.uwa.edu.au")
            db.session.add(u)
            db.session.commit()
            uid = int(u.id)
        rl = self.client.post("/auth/test-login", json={"user_id": uid})
        self.assertTrue(json.loads(rl.get_data(as_text=True)).get("ok"))
        return uid


if __name__ == "__main__":
    unittest.main()
