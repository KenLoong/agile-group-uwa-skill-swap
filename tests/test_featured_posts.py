# =============================================================================
# Tests — featured homepage pins + GET /api/featured-posts
# =============================================================================
from __future__ import annotations

import json
import re
import unittest
from datetime import datetime

from api.app_factory import create_app
from api.tags_models import Category, Post, User, db
from sqlalchemy import select


class TestFeaturedPosts(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_api_empty_when_no_pins(self) -> None:
        r = self.client.get("/api/featured-posts")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertEqual(data, {"posts": []})

    def test_order_open_only_and_pin_sequence(self) -> None:
        with self.app.app_context():
            ux = User(id=500, email="f@student.uwa.edu.au", username="feat")
            db.session.add(ux)
            cid = db.session.scalar(select(Category.id).where(Category.slug == "coding"))
            assert cid is not None
            ts = datetime(2026, 12, 1, 12, 0, 0)
            p_second = Post(
                title="Second pin",
                description="Beta",
                category_id=int(cid),
                owner_id=500,
                status="open",
                featured_pin_order=2,
                timestamp=ts,
            )
            p_first = Post(
                title="First pin",
                description="Alpha",
                category_id=int(cid),
                owner_id=500,
                status="open",
                featured_pin_order=1,
                timestamp=ts,
            )
            p_closed = Post(
                title="Closed but pinned number",
                description="Ignored",
                category_id=int(cid),
                owner_id=500,
                status="closed",
                featured_pin_order=0,
                timestamp=ts,
            )
            db.session.add_all([p_second, p_first, p_closed])
            db.session.commit()

        r = self.client.get("/api/featured-posts")
        data = json.loads(r.get_data(as_text=True))
        titles = [p["title"] for p in data["posts"]]
        self.assertEqual(titles, ["First pin", "Second pin"])
        self.assertEqual(data["posts"][0]["featured_pin_order"], 1)
        self.assertIn("category_slug", data["posts"][0])

    def test_homepage_renders_featured_cards(self) -> None:
        with self.app.app_context():
            ux = User(id=501, email="h@student.uwa.edu.au", username="homeu")
            db.session.add(ux)
            cid = db.session.scalar(select(Category.id).where(Category.slug == "music"))
            assert cid is not None
            ts = datetime(2026, 12, 2, 9, 0, 0)
            db.session.add(
                Post(
                    title="Demo guitar slot",
                    description="Starter chords",
                    category_id=int(cid),
                    owner_id=501,
                    status="open",
                    featured_pin_order=5,
                    timestamp=ts,
                )
            )
            db.session.commit()

        rv = self.client.get("/")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("Featured listings", html)
        self.assertIn("Demo guitar slot", html)
        self.assertRegex(html, r"Pin\s+5")
        self.assertIsNotNone(re.search(r'href="/posts/\d+"', html))


if __name__ == "__main__":
    unittest.main()
