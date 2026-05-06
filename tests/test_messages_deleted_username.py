# =============================================================================
# Messages — deleted participants + case-insensitive open-by-username
# =============================================================================
# Run:
#   PYTHONPATH=. python -m unittest tests.test_messages_deleted_username -v
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


def _sqlite_bypass_delete_user(app, uid: int) -> None:
    """Remove ``user`` row while leaving thread references (SQLite coursework DB)."""
    with app.app_context():
        engine = db.engine
        if engine.dialect.name != "sqlite":
            raise unittest.SkipTest("deleted-user bypass needs SQLite FK relaxed delete")
        conn = engine.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=OFF")
            cur.execute("DELETE FROM user WHERE id = ?", (int(uid),))
            cur.execute("PRAGMA foreign_keys=ON")
            conn.commit()
        finally:
            conn.close()


class TestOpenThreadByUsernameCI(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        with _session(self.app) as s:
            s.add(User(id=1, email="a@uwa.edu.au", username="CaSeUsEr"))
            s.add(User(id=2, email="b@uwa.edu.au", username="peer"))

    def test_open_via_other_username_case_insensitive(self) -> None:
        r = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_username": "CASEUSER"}),
            content_type="application/json",
            headers=_hdr(1),
        )
        self.assertEqual(r.status_code, 400)

        r2 = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_username": "PEER"}),
            content_type="application/json",
            headers=_hdr(1),
        )
        self.assertEqual(r2.status_code, 200)
        tid = json.loads(r2.get_data(as_text=True))["thread_id"]

        r3 = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_username": "CasEuSeR"}),
            content_type="application/json",
            headers=_hdr(2),
        )
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(json.loads(r3.get_data(as_text=True))["thread_id"], tid)

    def test_other_user_id_preempts_other_username(self) -> None:
        r = self.client.post(
            "/messages/thread/open",
            data=json.dumps({"other_user_id": 2, "other_username": "NobodyHere"}),
            content_type="application/json",
            headers=_hdr(1),
        )
        self.assertEqual(r.status_code, 200)


class TestPollWithDeletedParticipant(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        with _session(self.app) as s:
            s.add(User(id=10, email="s10@uwa.edu.au", username="stay"))
            s.add(User(id=11, email="gone@uwa.edu.au", username="goneuser"))

        tid = json.loads(
            self.client.post(
                "/messages/thread/open",
                data=json.dumps({"other_user_id": 11}),
                content_type="application/json",
                headers=_hdr(10),
            ).get_data(as_text=True)
        )["thread_id"]
        self.tid = int(tid)
        self.client.post(
            f"/messages/thread/{self.tid}/messages",
            data=json.dumps({"body": "from survivor"}),
            content_type="application/json",
            headers=_hdr(10),
        )
        self.client.post(
            f"/messages/thread/{self.tid}/messages",
            data=json.dumps({"body": "from leaving user"}),
            content_type="application/json",
            headers=_hdr(11),
        )

    def test_poll_peer_deleted_flags_and_returns_200(self) -> None:
        _sqlite_bypass_delete_user(self.app, 11)

        r = self.client.get(f"/messages/thread/{self.tid}/poll?after_id=0", headers=_hdr(10))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertTrue(data["peer"]["deleted"])
        self.assertEqual(data["peer"]["id"], 11)
        by_sender = {m["sender_id"]: m for m in data["messages"]}
        self.assertFalse(by_sender[10]["sender_deleted"])
        self.assertTrue(by_sender[11]["sender_deleted"])

    def test_inbox_marks_deleted_peer(self) -> None:
        _sqlite_bypass_delete_user(self.app, 11)
        inbox = json.loads(self.client.get("/messages/inbox", headers=_hdr(10)).get_data(as_text=True))
        row = next(x for x in inbox["items"] if x["thread_id"] == self.tid)
        self.assertTrue(row["other"]["deleted"])
        self.assertEqual(row["other"]["id"], 11)

    def test_thread_detail_graceful_for_deleted_you_is_rare_but_other(self) -> None:
        _sqlite_bypass_delete_user(self.app, 11)
        rg = json.loads(self.client.get(f"/messages/thread/{self.tid}", headers=_hdr(10)).get_data(as_text=True))
        self.assertTrue(rg["other"]["deleted"])
        self.assertFalse(rg["you"]["deleted"])
        msgs = rg["messages"]
        self.assertEqual(len(msgs), 2)
        self.assertTrue(any(m["sender_id"] == 11 and m["sender_deleted"] for m in msgs))


if __name__ == "__main__":
    unittest.main()
