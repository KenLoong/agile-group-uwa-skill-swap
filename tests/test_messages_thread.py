# =============================================================================
# Private message threads — open thread, send, inbox, mark read, GET thread
# =============================================================================
# Run:
#   PYTHONPATH=. python -m unittest tests.test_messages_thread -v
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager

from api.app_factory import create_app
from api.tags_models import User, db


@contextmanager
def _session(app):
    with app.app_context():
        try:
            yield db.session
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            raise


def _hdr(n: int) -> dict[str, str]:
    return {"X-User-Id": str(n)}


class TestMessagesAuthentication(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_inbox_401_without_identity(self) -> None:
        r = self.client.get("/messages/inbox")
        self.assertEqual(r.status_code, 401)

    def test_thread_get_401_without_identity(self) -> None:
        r = self.client.get("/messages/thread/1")
        self.assertEqual(r.status_code, 401)

    def test_open_thread_401_without_identity(self) -> None:
        r = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_user_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)


class TestMessagesThreadFlow(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        with _session(self.app) as s:
            s.add_all(
                [
                    User(id=1, email="a@uwa.edu.au", username="alice"),
                    User(id=2, email="b@uwa.edu.au", username="bob"),
                ]
            )

    def test_open_thread_idempotent_pair(self) -> None:
        h = _hdr(1)
        r1 = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_user_id": 2}),
            content_type="application/json",
            headers=h,
        )
        self.assertEqual(r1.status_code, 200)
        tid = json.loads(r1.get_data(as_text=True))["thread_id"]
        r2 = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_user_id": 2}),
            content_type="application/json",
            headers=h,
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(json.loads(r2.get_data(as_text=True))["thread_id"], tid)

    def test_open_thread_symmetric_from_either_user(self) -> None:
        ra = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_user_id": 2}),
            content_type="application/json",
            headers=_hdr(1),
        )
        rb = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_user_id": 1}),
            content_type="application/json",
            headers=_hdr(2),
        )
        self.assertEqual(json.loads(ra.get_data(as_text=True))["thread_id"], json.loads(rb.get_data(as_text=True))["thread_id"])

    def test_cannot_open_thread_with_self(self) -> None:
        r = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_user_id": 1}),
            content_type="application/json",
            headers=_hdr(1),
        )
        self.assertEqual(r.status_code, 400)

    def test_send_and_list_messages(self) -> None:
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 2}),
                content_type="application/json",
                headers=_hdr(1),
            ).get_data(as_text=True)
        )["thread_id"]

        rp = self.client.post(
            f"/messages/thread/{tid}/messages",
            data=json.dumps({"body": " Hello "}),
            content_type="application/json",
            headers=_hdr(1),
        )
        self.assertEqual(rp.status_code, 200)
        self.assertTrue(json.loads(rp.get_data(as_text=True))["ok"])

        rg = self.client.get(f"/messages/thread/{tid}", headers=_hdr(2))
        self.assertEqual(rg.status_code, 200)
        body = json.loads(rg.get_data(as_text=True))
        self.assertEqual(len(body["messages"]), 1)
        self.assertEqual(body["messages"][0]["body"], "Hello")
        self.assertFalse(body["messages"][0]["read"])

    def test_inbox_unread_and_mark_read(self) -> None:
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 2}),
                content_type="application/json",
                headers=_hdr(1),
            ).get_data(as_text=True)
        )["thread_id"]
        self.client.post(
            f"/messages/thread/{tid}/messages",
            data=json.dumps({"body": "ping"}),
            content_type="application/json",
            headers=_hdr(1),
        )

        inbox_b = json.loads(self.client.get("/messages/inbox", headers=_hdr(2)).get_data(as_text=True))
        self.assertEqual(inbox_b["unread"], 1)
        self.assertEqual(inbox_b["items"][0]["unread_for_me"], 1)

        mr = self.client.post(f"/messages/thread/{tid}/read", headers=_hdr(2))
        self.assertEqual(mr.status_code, 200)
        self.assertEqual(json.loads(mr.get_data(as_text=True))["marked"], 1)

        inbox_b2 = json.loads(self.client.get("/messages/inbox", headers=_hdr(2)).get_data(as_text=True))
        self.assertEqual(inbox_b2["unread"], 0)

    def test_non_member_cannot_view_thread(self) -> None:
        with _session(self.app) as s:
            s.add(User(id=99, email="z@uwa.edu.au", username="z"))

        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 2}),
                content_type="application/json",
                headers=_hdr(1),
            ).get_data(as_text=True)
        )["thread_id"]
        r = self.client.get(f"/messages/thread/{tid}", headers=_hdr(99))
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
