# =============================================================================
# Tests — HTML post detail (tags + lifecycle badge + JSON sibling route)
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager

from api.app_factory import create_app
from api.tags_models import CATEGORY_SLUG_GENERAL, Category, Post, Tag, User, db
from sqlalchemy import select


@contextmanager
def _sess(app):
    with app.app_context():
        try:
            yield db.session
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            raise


class TestPostDetailHtml(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_html_404_placeholder(self) -> None:
        r = self.client.get("/posts/999999")
        self.assertEqual(r.status_code, 404)
        body = r.get_data(as_text=True)
        self.assertIn("Post not found", body)

    def test_html_renders_lifecycle_and_tag_pills(self) -> None:
        with _sess(self.app) as s:
            u = User(id=7, email="author@student.uwa.edu.au", username="alice_demo")
            s.add(u)
            py = Tag(slug="python", label="Python")
            s.add(py)
            s.flush()

            cid = s.scalar(select(Category.id).where(Category.slug == CATEGORY_SLUG_GENERAL))
            assert cid is not None

            post = Post(
                title="Debug session offer",
                description="Pair on COMP labs.\nSecond line.",
                category_id=int(cid),
                owner_id=7,
                status="matched",
                like_count=2,
                comment_count=1,
            )
            post.tags.append(py)
            s.add(post)
            s.flush()
            pid = post.id

        rv = self.client.get(f"/posts/{pid}")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("Debug session offer", html)
        self.assertIn("Pair on COMP labs.", html)
        self.assertIn("Second line.", html)
        self.assertIn("alice_demo", html)
        self.assertIn("Matched", html)
        self.assertIn('class="badge rounded-pill text-bg-light border tag-pill', html)
        self.assertIn("Python", html)
        self.assertIn("General", html)  # category label from seed
        self.assertIn(">2</strong> likes", html)
        self.assertIn(f"/posts/{pid}/json", html)

    def test_html_cover_prefers_custom_alt_over_title(self) -> None:
        with _sess(self.app) as s:
            u = User(id=17, email="pic@student.uwa.edu.au", username="pics")
            s.add(u)
            cid = s.scalar(select(Category.id).where(Category.slug == CATEGORY_SLUG_GENERAL))
            assert cid is not None
            post = Post(
                title="Workshop teaser",
                description="Join us.",
                category_id=int(cid),
                owner_id=17,
                image_filename="board.png",
                image_alt="Whiteboard explaining recursion",
                status="open",
            )
            s.add(post)
            s.flush()
            pid = post.id

        rv = self.client.get(f"/posts/{pid}")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn('alt="Whiteboard explaining recursion"', html)
        self.assertIn("uploads/posts/board.png", html)
    def test_json_detail_route_unchanged_shape(self) -> None:
        with _sess(self.app) as s:
            u = User(id=8, email="x@student.uwa.edu.au")
            s.add(u)
            cid = s.scalar(select(Category.id).where(Category.slug == "music"))
            assert cid is not None
            p = Post(
                title="Guitar",
                description="Acoustic",
                category_id=int(cid),
                owner_id=8,
                status="closed",
            )
            s.add(p)
            s.flush()
            pid = p.id

        r = self.client.get(f"/posts/{pid}/json")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertEqual(data["title"], "Guitar")
        self.assertEqual(data["status"], "closed")
        self.assertEqual(data["category"]["slug"], "music")
        self.assertIsNone(data.get("image_alt"))


if __name__ == "__main__":
    unittest.main()
