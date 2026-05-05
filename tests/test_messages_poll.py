# =============================================================================
# Message thread poll — incremental GET + read/unread + empty-thread cases
# =============================================================================
# Run:
#   PYTHONPATH=. python -m unittest tests.test_messages_poll -v
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


class TestMessagePollAuthAndValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        with _session(self.app) as s:
            s.add_all(
                [
                    User(id=1, email="p1@uwa.edu.au", username="poll1"),
                    User(id=2, email="p2@uwa.edu.au", username="poll2"),
                ]
            )

    def test_poll_401_without_identity(self) -> None:
        r = self.client.get("/messages/thread/1/poll")
        self.assertEqual(r.status_code, 401)

    def test_poll_bad_after_id_returns_400(self) -> None:
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 2}),
                content_type="application/json",
                headers=_hdr(1),
            ).get_data(as_text=True)
        )["thread_id"]
        r = self.client.get(f"/messages/thread/{tid}/poll?after_id=-1", headers=_hdr(1))
        self.assertEqual(r.status_code, 400)
        r2 = self.client.get(f"/messages/thread/{tid}/poll?after_id=abc", headers=_hdr(1))
        self.assertEqual(r2.status_code, 400)

    def test_poll_404_for_non_member(self) -> None:
        with _session(self.app) as s:
            s.add(User(id=99, email="x@uwa.edu.au", username="stranger"))
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 2}),
                content_type="application/json",
                headers=_hdr(1),
            ).get_data(as_text=True)
        )["thread_id"]
        r = self.client.get(f"/messages/thread/{tid}/poll", headers=_hdr(99))
        self.assertEqual(r.status_code, 404)


class TestMessagePollEmptyThread(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        with _session(self.app) as s:
            s.add_all(
                [
                    User(id=1, email="e1@uwa.edu.au", username="e1"),
                    User(id=2, email="e2@uwa.edu.au", username="e2"),
                ]
            )

    def test_poll_empty_thread_default_after_id_zero(self) -> None:
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 2}),
                content_type="application/json",
                headers=_hdr(1),
            ).get_data(as_text=True)
        )["thread_id"]
        r = self.client.get(f"/messages/thread/{tid}/poll", headers=_hdr(1))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertEqual(data["messages"], [])
        self.assertIsNone(data["latest_id"])
        self.assertEqual(data["unread_for_me"], 0)

    def test_poll_empty_thread_explicit_after_zero(self) -> None:
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 2}),
                content_type="application/json",
                headers=_hdr(1),
            ).get_data(as_text=True)
        )["thread_id"]
        r = self.client.get(f"/messages/thread/{tid}/poll?after_id=0", headers=_hdr(2))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertEqual(data["messages"], [])

    def test_poll_large_after_id_still_success_empty(self) -> None:
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
            data=json.dumps({"body": "only"}),
            content_type="application/json",
            headers=_hdr(1),
        )
        r = self.client.get(f"/messages/thread/{tid}/poll?after_id=999999", headers=_hdr(2))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertEqual(data["messages"], [])


class TestMessagePollReadUnreadIncremental(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        with _session(self.app) as s:
            s.add_all(
                [
                    User(id=10, email="u10@uwa.edu.au", username="u10"),
                    User(id=11, email="u11@uwa.edu.au", username="u11"),
                ]
            )

    def test_poll_returns_incremental_cursor(self) -> None:
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 11}),
                content_type="application/json",
                headers=_hdr(10),
            ).get_data(as_text=True)
        )["thread_id"]
        self.client.post(
            f"/messages/thread/{tid}/messages",
            data=json.dumps({"body": "first"}),
            content_type="application/json",
            headers=_hdr(10),
        )
        self.client.post(
            f"/messages/thread/{tid}/messages",
            data=json.dumps({"body": "second"}),
            content_type="application/json",
            headers=_hdr(11),
        )

        p0 = json.loads(
            self.client.get(f"/messages/thread/{tid}/poll?after_id=0", headers=_hdr(11)).get_data(as_text=True)
        )
        self.assertEqual(len(p0["messages"]), 2)
        self.assertEqual([m["body"] for m in p0["messages"]], ["first", "second"])
        mid = p0["messages"][0]["id"]

        p1 = json.loads(
            self.client.get(f"/messages/thread/{tid}/poll?after_id={mid}", headers=_hdr(11)).get_data(as_text=True)
        )
        self.assertEqual(len(p1["messages"]), 1)
        self.assertEqual(p1["messages"][0]["body"], "second")

    def test_poll_read_flag_for_recipient_and_unread_count(self) -> None:
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 11}),
                content_type="application/json",
                headers=_hdr(10),
            ).get_data(as_text=True)
        )["thread_id"]
        self.client.post(
            f"/messages/thread/{tid}/messages",
            data=json.dumps({"body": "hello poll"}),
            content_type="application/json",
            headers=_hdr(10),
        )

        poll_b = json.loads(self.client.get(f"/messages/thread/{tid}/poll", headers=_hdr(11)).get_data(as_text=True))
        self.assertEqual(len(poll_b["messages"]), 1)
        self.assertFalse(poll_b["messages"][0]["read"])
        self.assertEqual(poll_b["unread_for_me"], 1)

        self.client.post(f"/messages/thread/{tid}/read", headers=_hdr(11))

        poll_b2 = json.loads(
            self.client.get(f"/messages/thread/{tid}/poll?after_id=0", headers=_hdr(11)).get_data(as_text=True)
        )
        self.assertTrue(poll_b2["messages"][0]["read"])
        self.assertEqual(poll_b2["unread_for_me"], 0)

    def test_poll_no_new_rows_after_mark_read_but_unread_drops(self) -> None:
        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 11}),
                content_type="application/json",
                headers=_hdr(10),
            ).get_data(as_text=True)
        )["thread_id"]
        self.client.post(
            f"/messages/thread/{tid}/messages",
            data=json.dumps({"body": "ping"}),
            content_type="application/json",
            headers=_hdr(10),
        )
        first = json.loads(self.client.get(f"/messages/thread/{tid}/poll", headers=_hdr(11)).get_data(as_text=True))
        last_id = first["latest_id"]
        self.assertIsNotNone(last_id)

        self.client.post(f"/messages/thread/{tid}/read", headers=_hdr(11))

        tail = json.loads(
            self.client.get(f"/messages/thread/{tid}/poll?after_id={last_id}", headers=_hdr(11)).get_data(as_text=True)
        )
        self.assertEqual(tail["messages"], [])
        self.assertEqual(tail["unread_for_me"], 0)


if __name__ == "__main__":
    unittest.main()
