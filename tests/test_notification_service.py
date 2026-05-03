# =============================================================================
# Tests — notification service + interest route wiring
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager

from api.app_factory import create_app
from api.tags_models import Category, Interest, Notification, Post, User, db
from services import notification_service
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


class TestNotificationServiceInterest(unittest.TestCase):
    def test_queues_interest_notification_for_owner(self) -> None:
        app = create_app(testing=True)
        with _session(app) as s:
            owner = User(id=1, email="o@uwa.edu.au", username="owner1")
            peer = User(id=2, email="p@uwa.edu.au", username="peer1")
            s.add_all([owner, peer])
            p = Post(
                title="t",
                description="d",
                owner_id=owner.id,
                category_id=_cat_id(s, "coding"),
            )
            s.add(p)
            s.flush()
            n = notification_service.notify_listing_owner_new_interest(sender_id=peer.id, post=p)
            self.assertIsNotNone(n)
            self.assertEqual(n.user_id, owner.id)
            self.assertEqual(n.actor_id, peer.id)
            self.assertEqual(n.notif_type, notification_service.NOTIF_TYPE_INTEREST)
            s.commit()

        with app.app_context():
            self.assertEqual(db.session.scalar(select(func.count(Notification.id))), 1)

    def test_skips_notification_when_owner_is_sender(self) -> None:
        app = create_app(testing=True)
        with _session(app) as s:
            u = User(id=3, email="solo@uwa.edu.au", username="solo")
            s.add(u)
            p = Post(
                title="mine",
                description="d",
                owner_id=u.id,
                category_id=_cat_id(s, "music"),
            )
            s.add(p)
            s.flush()
            n = notification_service.notify_listing_owner_new_interest(sender_id=u.id, post=p)
            self.assertIsNone(n)


class TestNotificationServiceMentions(unittest.TestCase):
    def test_mention_parse_creates_rows(self) -> None:
        app = create_app(testing=True)
        with _session(app) as s:
            alice = User(id=10, email="a@uwa.edu.au", username="alice")
            bob = User(id=11, email="b@uwa.edu.au", username="Bob")
            carol = User(id=12, email="c@uwa.edu.au", username="carol")
            s.add_all([alice, bob, carol])
            pid = Post(
                title="post",
                description="d",
                owner_id=carol.id,
                category_id=_cat_id(s, "sports"),
            )
            s.add(pid)
            s.flush()
            post_id = int(pid.id)
            created = notification_service.create_mention_notifications_from_text(
                actor_id=alice.id,
                post_id=post_id,
                text="Hey @Bob and @carol check this",
            )
            self.assertEqual(len(created), 2)
            s.commit()

        with app.app_context():
            self.assertEqual(
                int(db.session.scalar(select(func.count(Notification.id)))),
                2,
            )


class TestInteractionRoute(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_post_interest_creates_interest_and_notification(self) -> None:
        with _session(self.app) as s:
            owner = User(id=20, email="ow@uwa.edu.au", username="ow20")
            peer = User(id=21, email="pe@uwa.edu.au", username="pe21")
            s.add_all([owner, peer])
            p = Post(
                title="offer",
                description="d",
                owner_id=owner.id,
                category_id=_cat_id(s, "coding"),
            )
            s.add(p)
            s.flush()
            pid = int(p.id)

        r = self.client.post(f"/interest/{pid}", headers={"X-User-Id": "21"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(json.loads(r.get_data(as_text=True)).get("ok"))

        with self.app.app_context():
            self.assertIsNotNone(db.session.scalar(select(Interest.id)))
            n = db.session.scalar(select(Notification).where(Notification.user_id == 20))
            self.assertIsNotNone(n)
            self.assertEqual(n.notif_type, notification_service.NOTIF_TYPE_INTEREST)

    def test_duplicate_interest_409(self) -> None:
        with _session(self.app) as s:
            owner = User(id=30, email="a30@uwa.edu.au")
            peer = User(id=31, email="b31@uwa.edu.au")
            s.add_all([owner, peer])
            p = Post(
                title="x",
                description="d",
                owner_id=owner.id,
                category_id=_cat_id(s, "general"),
            )
            s.add(p)
            s.flush()
            pid = int(p.id)

        h = {"X-User-Id": "31"}
        self.assertEqual(self.client.post(f"/interest/{pid}", headers=h).status_code, 200)
        r2 = self.client.post(f"/interest/{pid}", headers=h)
        self.assertEqual(r2.status_code, 409)


if __name__ == "__main__":
    unittest.main()
