# =============================================================================
# Tests — post aggregate helpers for list/detail payloads
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager

from api.app_factory import create_app
from api.post_aggregates import post_detail_payload, post_list_payload
from api.tags_models import CATEGORY_SLUG_GENERAL, Category, Post, Tag, User, db
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


def _json(resp):
    return json.loads(resp.get_data(as_text=True))


def _user(session, user_id: int = 1) -> User:
    u = User(id=user_id, email=f"u{user_id}@student.uwa.edu.au")
    session.add(u)
    session.flush()
    return u


def _tag(session, slug: str, label: str) -> Tag:
    t = Tag(slug=slug, label=label)
    session.add(t)
    session.flush()
    return t


def _post(session, owner: User, title: str) -> Post:
    cid = session.scalar(select(Category.id).where(Category.slug == CATEGORY_SLUG_GENERAL))
    assert cid is not None
    p = Post(title=title, owner_id=owner.id, category_id=int(cid))
    session.add(p)
    session.flush()
    return p


class TestPostAggregateHelpers(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_post_list_payload_includes_tag_counts_and_labels(self) -> None:
        with _session(self.app) as s:
            owner = _user(s, 1)
            python = _tag(s, "python", "Python")
            flask = _tag(s, "flask", "Flask")

            p1 = _post(s, owner, "Flask help")
            _post(s, owner, "General study help")
            p1.tags.extend([python, flask])

        with self.app.app_context():
            payload = post_list_payload()

        by_title = {item["title"]: item for item in payload}

        self.assertEqual(by_title["Flask help"]["tag_count"], 2)
        self.assertEqual(
            [tag["label"] for tag in by_title["Flask help"]["tags"]],
            ["Flask", "Python"],
        )

        self.assertEqual(by_title["General study help"]["tag_count"], 0)
        self.assertEqual(by_title["General study help"]["tags"], [])

    def test_post_detail_payload_returns_none_for_missing_post(self) -> None:
        with self.app.app_context():
            self.assertIsNone(post_detail_payload(999))

    def test_posts_list_route_uses_aggregate_payload(self) -> None:
        with _session(self.app) as s:
            owner = _user(s, 2)
            music = _tag(s, "music", "Music")

            p = _post(s, owner, "Piano basics")
            p.tags.append(music)

        r = self.client.get("/posts/")
        self.assertEqual(r.status_code, 200)

        data = _json(r)
        self.assertEqual(data["module"], "posts")
        self.assertEqual(data["items"][0]["tag_count"], 1)
        self.assertEqual(data["items"][0]["tags"][0]["slug"], "music")

    def test_post_detail_route_returns_aggregate_payload(self) -> None:
        with _session(self.app) as s:
            owner = _user(s, 3)
            coding = _tag(s, "coding", "Coding")

            p = _post(s, owner, "Debugging help")
            p.tags.append(coding)
            post_id = p.id

        r = self.client.get(f"/posts/{post_id}/json")
        self.assertEqual(r.status_code, 200)

        data = _json(r)
        self.assertEqual(data["title"], "Debugging help")
        self.assertEqual(data["tag_count"], 1)
        self.assertEqual(data["tags"][0]["label"], "Coding")
        self.assertEqual(data["category"]["slug"], CATEGORY_SLUG_GENERAL)
        self.assertEqual(data["category"]["label"], "General")
        self.assertIn("timestamp_iso", data)
        self.assertIn("description", data)
        self.assertIn("comment_count", data)
        self.assertIn("like_count", data)

    def test_post_payload_includes_engagement_fields_and_category(self) -> None:
        with _session(self.app) as s:
            owner = _user(s, 4)
            p = _post(s, owner, "Counters")
            p.description = "Teach guitar after hours."
            p.comment_count = 2
            p.like_count = 7

        with self.app.app_context():
            rows = post_list_payload()

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["description"], "Teach guitar after hours.")
        self.assertEqual(row["comment_count"], 2)
        self.assertEqual(row["like_count"], 7)
        self.assertEqual(row["category"]["slug"], CATEGORY_SLUG_GENERAL)
        self.assertIsNotNone(row.get("timestamp_iso"))

    def test_post_detail_route_returns_404_for_missing_post(self) -> None:
        r = self.client.get("/posts/999/json")

        self.assertEqual(r.status_code, 404)
        self.assertEqual(_json(r)["message"], "Post not found")


if __name__ == "__main__":
    unittest.main()