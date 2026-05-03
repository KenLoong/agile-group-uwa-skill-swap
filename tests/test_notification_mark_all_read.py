# =============================================================================
# Dashboard notifications — GET unread-count + POST mark-all-read
# =============================================================================
# Run:
#   PYTHONPATH=. python -m unittest tests.test_notification_mark_all_read -v
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager

from api.app_factory import create_app
from api.tags_models import Category, Notification, Post, User, db
from sqlalchemy import func, select


@contextmanager
def _session(app):
    with app.app_context():
        try:
            yield db.session
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            raise


def _cat_id(sess, slug: str) -> int:
    cid = sess.scalar(select(Category.id).where(Category.slug == slug))
    assert cid is not None
    return int(cid)


def _hdr_uid(n: int) -> dict[str, str]:
    return {"X-User-Id": str(n)}


class TestNotificationUnreadCountApi(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_unread_count_401_without_identity(self) -> None:
        r = self.client.get("/api/dashboard/notifications/unread-count")
        self.assertEqual(r.status_code, 401)

    def test_unread_count_404_when_user_missing(self) -> None:
        r = self.client.get("/api/dashboard/notifications/unread-count", headers=_hdr_uid(999_999))
        self.assertEqual(r.status_code, 404)

    def test_unread_count_matches_unread_rows(self) -> None:
        with _session(self.app) as s:
            u = User(id=50, email="n50@uwa.edu.au", username="n50")
            actor = User(id=51, email="a51@uwa.edu.au", username="a51")
            s.add_all([u, actor])
            p = Post(
                title="p",
                description="d",
                owner_id=u.id,
                category_id=_cat_id(s, "general"),
            )
            s.add(p)
            s.flush()
            pid = int(p.id)
            s.add_all(
                [
                    Notification(
                        user_id=u.id,
                        actor_id=actor.id,
                        post_id=pid,
                        notif_type="interest",
                        read=False,
                    ),
                    Notification(
                        user_id=u.id,
                        actor_id=actor.id,
                        post_id=pid,
                        notif_type="interest",
                        read=True,
                    ),
                ]
            )

        r = self.client.get("/api/dashboard/notifications/unread-count", headers=_hdr_uid(50))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.get_data(as_text=True))["unread_count"], 1)


class TestNotificationMarkAllReadApi(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_mark_all_401_without_identity(self) -> None:
        r = self.client.post("/api/dashboard/notifications/mark-all-read")
        self.assertEqual(r.status_code, 401)

    def test_mark_all_response_includes_zero_unread_count(self) -> None:
        with _session(self.app) as s:
            u = User(id=60, email="n60@uwa.edu.au", username="n60")
            actor = User(id=61, email="a61@uwa.edu.au", username="a61")
            s.add_all([u, actor])
            p = Post(
                title="p2",
                description="d",
                owner_id=u.id,
                category_id=_cat_id(s, "coding"),
            )
            s.add(p)
            s.flush()
            pid = int(p.id)
            s.add(
                Notification(
                    user_id=u.id,
                    actor_id=actor.id,
                    post_id=pid,
                    notif_type="interest",
                    read=False,
                )
            )

        r = self.client.post("/api/dashboard/notifications/mark-all-read", headers=_hdr_uid(60))
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.get_data(as_text=True))
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("marked"), 1)
        self.assertEqual(body.get("unread_count"), 0)

        r2 = self.client.get("/api/dashboard/notifications/unread-count", headers=_hdr_uid(60))
        self.assertEqual(json.loads(r2.get_data(as_text=True))["unread_count"], 0)

        with self.app.app_context():
            q = select(func.count(Notification.id)).where(
                Notification.user_id == 60,
                Notification.read.is_(False),
            )
            self.assertEqual(int(db.session.scalar(q) or 0), 0)

    def test_mark_all_idempotent_when_already_clear(self) -> None:
        with _session(self.app) as s:
            u = User(id=70, email="n70@uwa.edu.au", username="n70")
            s.add(u)

        r = self.client.post("/api/dashboard/notifications/mark-all-read", headers=_hdr_uid(70))
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.get_data(as_text=True))
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("marked"), 0)
        self.assertEqual(body.get("unread_count"), 0)


if __name__ == "__main__":
    unittest.main()
