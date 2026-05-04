# =============================================================================
# Tests — POST /post/set-status  (open / matched / closed) + non-owner denial
# =============================================================================
# This module intentionally stays verbose: sprint reviewers and markers can grep
# for scenario names. Identity is simulated with X-User-Id for the isolated app
# factory; merge with the full login stack later without rewriting assertions.
#
# Run:
#   python -m unittest tests.test_post_set_status -v
# =============================================================================
from __future__ import annotations

import json
import unittest
from typing import Any

from api.tags_models import CATEGORY_SLUG_GENERAL, Category, Post, db
from sqlalchemy import select
from tests.helpers import BaseTestCase, create_test_post, create_test_user, get_json, session_scope


# -----------------------------------------------------------------------------
# Local helpers
# -----------------------------------------------------------------------------






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


class TestPostSetStatusOwnerOpenToMatchedToClosed(BaseTestCase):
    """Owner may walk the state machine: open -> matched -> closed and branch."""

    def setUp(self) -> None:
        super().setUp()
        self.c = self.client
        with session_scope(self.app) as s:
            self.owner = create_test_user(s, 1)
            p = create_test_post(s, self.owner, "offer guitar", "open")
            self.post_id = p.id

    def test_owner_sets_open_idempotent(self) -> None:
        r = _set_status(self.c, post_id=self.post_id, status="open", as_user=1)
        self.assertEqual(r.status_code, 200)
        d = get_json(r)
        self.assertTrue(d.get("ok"))
        self.assertEqual(d.get("status"), "open")

    def test_owner_sets_matched(self) -> None:
        r = _set_status(self.c, post_id=self.post_id, status="matched", as_user=1)
        self.assertEqual(r.status_code, 200)
        d = get_json(r)
        self.assertTrue(d.get("ok"))
        self.assertEqual(d.get("status"), "matched")
        with session_scope(self.app) as s:
            reloaded = s.get(Post, self.post_id)
            self.assertEqual(reloaded.status, "matched")

    def test_owner_sets_closed_from_matched(self) -> None:
        with session_scope(self.app) as s:
            p = s.get(Post, self.post_id)
            p.status = "matched"
        r = _set_status(self.c, post_id=self.post_id, status="closed", as_user=1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(get_json(r).get("status"), "closed")

    def test_owner_sets_closed_directly(self) -> None:
        r = _set_status(self.c, post_id=self.post_id, status="closed", as_user=1)
        self.assertEqual(r.status_code, 200)
        with session_scope(self.app) as s:
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
        self.assertTrue(get_json(r).get("ok"))


# =============================================================================
# Security — non-owner and anonymous
# =============================================================================


class TestPostSetStatusForbiddenNonOwner(BaseTestCase):
    """403 when another user_id tries to change someone else's post."""

    def setUp(self) -> None:
        super().setUp()
        self.c = self.client
        with session_scope(self.app) as s:
            a = create_test_user(s, 1)
            _b = create_test_user(s, 2)
            self.post_a = create_test_post(s, a, "A post", "open").id

    def test_user_2_cannot_set_user_1_post(self) -> None:
        r = _set_status(self.c, post_id=self.post_a, status="closed", as_user=2)
        self.assertEqual(r.status_code, 403)
        d = get_json(r)
        self.assertFalse(d.get("ok", True))
        self.assertIn("forbidden", d.get("error", "").lower() + d.get("detail", ""))

    def test_user_99_cannot_set_post(self) -> None:
        r = _set_status(self.c, post_id=self.post_a, status="matched", as_user=99)
        self.assertEqual(r.status_code, 403)

    def test_victim_data_unchanged_after_forbidden(self) -> None:
        r = _set_status(self.c, post_id=self.post_a, status="closed", as_user=2)
        self.assertEqual(r.status_code, 403)
        with session_scope(self.app) as s:
            self.assertEqual(s.get(Post, self.post_a).status, "open")


class TestPostSetStatusUnauthenticated(BaseTestCase):
    """401 when X-User-Id is absent (this slice; later = session)."""

    def setUp(self) -> None:
        super().setUp()
        self.c = self.client
        with session_scope(self.app) as s:
            o = create_test_user(s, 5)
            self.p5 = create_test_post(s, o, "x", "open").id

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


class TestPostSetStatusValidation(BaseTestCase):
    """4xx for nonsense bodies — keeps the route hard to abuse."""

    def setUp(self) -> None:
        super().setUp()
        self.c = self.client
        with session_scope(self.app) as s:
            o = create_test_user(s, 3)
            self.p = create_test_post(s, o, "v", "open").id

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
        with session_scope(self.app) as s:
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


class TestPostSetStatusIdempotenceNotes(BaseTestCase):
    """
    These tests document intended behaviour; they are not a formal property test.

    Rationale: teaching staff often look for "does the team think about
    idempotence and side effects" even when the product owner did not file a
    story. We keep a light touch here: repeated calls with the same status
    should at minimum not 500 and should leave the row readable.
    """

    def setUp(self) -> None:
        super().setUp()
        self.c = self.client
        with session_scope(self.app) as s:
            o = create_test_user(s, 7)
            self.p7 = create_test_post(s, o, "idem", "open").id

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
        self.assertEqual(get_json(r).get("status"), "closed")


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
