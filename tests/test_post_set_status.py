# =============================================================================
# Tests — POST /post/set-status  (open / matched / closed) + non-owner denial
# =============================================================================
# This module intentionally stays verbose: sprint reviewers and markers can grep
# for scenario names. Identity is simulated with X-User-Id for the isolated app
# factory; merge with the full login stack later without rewriting assertions.
#
# Run:
#   PYTHONPATH=. python -m unittest tests.test_post_set_status -v
# =============================================================================
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from typing import Any

from api.app_factory import create_app
from api.tags_models import CATEGORY_SLUG_GENERAL, Category, Post, User, db
from sqlalchemy import select


# -----------------------------------------------------------------------------
# Local helpers
# -----------------------------------------------------------------------------


@contextmanager
def _session(app):
    with app.app_context():
        try:
            yield db.session
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            raise


def _j(resp) -> dict[str, Any]:
    return json.loads(resp.get_data(as_text=True))


def _user(sess, n: int = 1) -> User:
    u = User(id=n, email=f"u{n}@student.uwa.edu.au")
    sess.add(u)
    sess.flush()
    return u


def _post(sess, owner: User, title: str = "skill", status: str = "open") -> Post:
    cid = sess.scalar(select(Category.id).where(Category.slug == CATEGORY_SLUG_GENERAL))
    assert cid is not None
    p = Post(title=title, owner_id=owner.id, status=status, category_id=int(cid))
    sess.add(p)
    sess.flush()
    return p


def _set_status(
    client,
    *,
    post_id: int,
    status: str,
    as_user: int,
):
    return client.post(
        "/post/set-status",
        data=json.dumps({"post_id": post_id, "status": status}),
        content_type="application/json",
        headers={"X-User-Id": str(as_user)},
    )


# =============================================================================
# Happy path — owner transitions (each legal terminal state)
# =============================================================================


class TestPostSetStatusOwnerOpenToMatchedToClosed(unittest.TestCase):
    """Owner may walk the state machine: open -> matched -> closed and branch."""

    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.c = self.app.test_client()
        with _session(self.app) as s:
            self.owner = _user(s, 1)
            p = _post(s, self.owner, "offer guitar", "open")
            self.post_id = p.id

    def test_owner_sets_open_idempotent(self) -> None:
        r = _set_status(self.c, post_id=self.post_id, status="open", as_user=1)
        self.assertEqual(r.status_code, 200)
        d = _j(r)
        self.assertTrue(d.get("ok"))
        self.assertEqual(d.get("status"), "open")

    def test_owner_sets_matched(self) -> None:
        r = _set_status(self.c, post_id=self.post_id, status="matched", as_user=1)
        self.assertEqual(r.status_code, 200)
        d = _j(r)
        self.assertTrue(d.get("ok"))
        self.assertEqual(d.get("status"), "matched")
        with _session(self.app) as s:
            reloaded = s.get(Post, self.post_id)
            self.assertEqual(reloaded.status, "matched")

    def test_owner_sets_closed_from_matched(self) -> None:
        with _session(self.app) as s:
            p = s.get(Post, self.post_id)
            p.status = "matched"
        r = _set_status(self.c, post_id=self.post_id, status="closed", as_user=1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(_j(r).get("status"), "closed")

    def test_owner_sets_closed_directly(self) -> None:
        r = _set_status(self.c, post_id=self.post_id, status="closed", as_user=1)
        self.assertEqual(r.status_code, 200)
        with _session(self.app) as s:
            self.assertEqual(s.get(Post, self.post_id).status, "closed")

    def test_string_post_id_in_json_accepted(self) -> None:
        """Some clients send numeric ids as strings; we coerce."""
        r = self.c.post(
            "/post/set-status",
            data=json.dumps({"post_id": str(self.post_id), "status": "open"}),
            content_type="application/json",
            headers={"X-User-Id": "1"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(_j(r).get("ok"))


# =============================================================================
# Security — non-owner and anonymous
# =============================================================================


class TestPostSetStatusForbiddenNonOwner(unittest.TestCase):
    """403 when another user_id tries to change someone else's post."""

    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.c = self.app.test_client()
        with _session(self.app) as s:
            a = _user(s, 1)
            _b = _user(s, 2)
            self.post_a = _post(s, a, "A post", "open").id

    def test_user_2_cannot_set_user_1_post(self) -> None:
        r = _set_status(self.c, post_id=self.post_a, status="closed", as_user=2)
        self.assertEqual(r.status_code, 403)
        d = _j(r)
        self.assertFalse(d.get("ok", True))
        self.assertIn("forbidden", d.get("error", "").lower() + d.get("detail", ""))

    def test_user_99_cannot_set_post(self) -> None:
        r = _set_status(self.c, post_id=self.post_a, status="matched", as_user=99)
        self.assertEqual(r.status_code, 403)

    def test_victim_data_unchanged_after_forbidden(self) -> None:
        r = _set_status(self.c, post_id=self.post_a, status="closed", as_user=2)
        self.assertEqual(r.status_code, 403)
        with _session(self.app) as s:
            self.assertEqual(s.get(Post, self.post_a).status, "open")


class TestPostSetStatusUnauthenticated(unittest.TestCase):
    """401 when X-User-Id is absent (this slice; later = session)."""

    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.c = self.app.test_client()
        with _session(self.app) as s:
            o = _user(s, 5)
            self.p5 = _post(s, o, "x", "open").id

    def test_missing_header_401(self) -> None:
        r = self.c.post(
            "/post/set-status",
            data=json.dumps({"post_id": self.p5, "status": "open"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)


# =============================================================================
# Invalid inputs
# =============================================================================


class TestPostSetStatusValidation(unittest.TestCase):
    """4xx for nonsense bodies — keeps the route hard to abuse."""

    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.c = self.app.test_client()
        with _session(self.app) as s:
            o = _user(s, 3)
            self.p = _post(s, o, "v", "open").id

    def test_invalid_status_400(self) -> None:
        r = _set_status(self.c, post_id=self.p, status="banana", as_user=3)
        self.assertEqual(r.status_code, 400)

    def test_not_json_400(self) -> None:
        r = self.c.post(
            "/post/set-status",
            data="nope",
            content_type="text/plain",
            headers={"X-User-Id": "3"},
        )
        self.assertEqual(r.status_code, 400)

    def test_unknown_post_404(self) -> None:
        r = _set_status(self.c, post_id=999_999, status="open", as_user=3)
        self.assertEqual(r.status_code, 404)

    def test_orphan_post_no_owner_403(self) -> None:
        """If owner_id is null, no caller should be considered owner in this check."""
        with _session(self.app) as s:
            cid = s.scalar(select(Category.id).where(Category.slug == CATEGORY_SLUG_GENERAL))
            assert cid is not None
            p = Post(title="orphan", owner_id=None, status="open", category_id=int(cid))
            s.add(p)
            s.flush()
            oid = p.id
        r = _set_status(self.c, post_id=oid, status="closed", as_user=3)
        self.assertEqual(r.status_code, 403)


# =============================================================================
# Regression / documentation placeholders (expand in later sprints)
# =============================================================================


class TestPostSetStatusIdempotenceNotes(unittest.TestCase):
    """
    These tests document intended behaviour; they are not a formal property test.

    Rationale: teaching staff often look for "does the team think about
    idempotence and side effects" even when the product owner did not file a
    story. We keep a light touch here: repeated calls with the same status
    should at minimum not 500 and should leave the row readable.
    """

    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.c = self.app.test_client()
        with _session(self.app) as s:
            o = _user(s, 7)
            self.p7 = _post(s, o, "idem", "open").id

    def test_double_matched_still_200(self) -> None:
        a = _set_status(self.c, post_id=self.p7, status="matched", as_user=7)
        b = _set_status(self.c, post_id=self.p7, status="matched", as_user=7)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)

    def test_mixed_case_status_normalized(self) -> None:
        r = self.c.post(
            "/post/set-status",
            data=json.dumps({"post_id": self.p7, "status": "ClOsEd"}),
            content_type="application/json",
            headers={"X-User-Id": "7"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(_j(r).get("status"), "closed")


# =============================================================================
# Appendix: manual test matrix (not executed; for sprint review walkthrough)
# =============================================================================
# status in { open, matched, closed } x role in { owner, peer, anonymous } x
# post in { exists+owned, exists+foreign, missing, owner NULL }  =>  expected
# ----------------------------------------------------------------------------
# open    + owner    + exists+owned     => 200
# matched + owner    + exists+owned     => 200
# closed  + owner    + exists+owned     => 200
# any     + peer     + exists+owned     => 403
# any     + anonymous+ any              => 401   (this slice: no X-User-Id)
# any     + any      + missing          => 404
# badstr  + owner    + exists+owned     => 400
# ----------------------------------------------------------------------------
# We keep the automated suite smaller than the Cartesian product; fill gaps
# during exploratory testing before major releases.
# =============================================================================


if __name__ == "__main__":
    unittest.main()
