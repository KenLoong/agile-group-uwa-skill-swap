# =============================================================================
# Dashboard wanted categories — GET/POST /api/dashboard/wanted (+ /dashboard gate)
# =============================================================================
# Covers authentication (X-User-Id, Flask-Login session), validation errors,
# persistence of add/remove/replace, duplicate id handling, unknown category
# ids stripped, and isolation between users.
#
# Run:
#   PYTHONPATH=. python -m unittest tests.test_dashboard_wanted -v
# =============================================================================
from __future__ import annotations

import json
import unittest

from api.tags_models import Category, User, db
from tests.helpers import BaseTestCase, session_scope as _session_scope


# Removed local _session_scope in favor of the shared helper from tests.helpers


def _hdr_uid(n: int) -> dict[str, str]:
    return {"X-User-Id": str(n)}


class TestDashboardWantedAuthentication(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

    def test_get_wanted_401_without_identity(self) -> None:
        r = self.client.get("/api/dashboard/wanted")
        self.assertEqual(r.status_code, 401)
        self.assertIn("message", json.loads(r.get_data(as_text=True)))

    def test_post_wanted_401_without_identity(self) -> None:
        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": []}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_get_wanted_404_when_user_missing(self) -> None:
        r = self.client.get("/api/dashboard/wanted", headers=_hdr_uid(404))
        self.assertEqual(r.status_code, 404)

    def test_post_wanted_404_when_user_missing(self) -> None:
        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": []}),
            content_type="application/json",
            headers=_hdr_uid(999),
        )
        self.assertEqual(r.status_code, 404)

    def test_dashboard_html_redirects_when_not_logged_in(self) -> None:
        r = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("Location", "")
        self.assertIn("/auth/login", loc)


class TestDashboardWantedValidation(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        with _session_scope(self.app) as s:
            s.add(User(id=1, email="a@student.uwa.edu.au"))

    def test_post_requires_json_content_type(self) -> None:
        r = self.client.post(
            "/api/dashboard/wanted",
            data="not-json",
            content_type="text/plain",
            headers=_hdr_uid(1),
        )
        self.assertEqual(r.status_code, 400)

    def test_post_rejects_non_object_json(self) -> None:
        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps([1, 2]),
            content_type="application/json",
            headers=_hdr_uid(1),
        )
        self.assertEqual(r.status_code, 400)

    def test_post_category_ids_must_be_list(self) -> None:
        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": "1"}),
            content_type="application/json",
            headers=_hdr_uid(1),
        )
        self.assertEqual(r.status_code, 400)

    def test_post_category_ids_must_be_integral_elements(self) -> None:
        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [1, "x"]}),
            content_type="application/json",
            headers=_hdr_uid(1),
        )
        self.assertEqual(r.status_code, 400)


class TestDashboardWantedPersistence(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        with _session_scope(self.app) as s:
            s.add(User(id=1, email="a@student.uwa.edu.au"))
            s.add(User(id=2, email="b@student.uwa.edu.au"))

    def _cat_ids(self, *slugs: str) -> list[int]:
        out: list[int] = []
        with self.app.app_context():
            for slug in slugs:
                c = Category.query.filter_by(slug=slug).first()
                assert c is not None
                out.append(c.id)
        return out

    def test_get_returns_categories_and_empty_wanted(self) -> None:
        r = self.client.get("/api/dashboard/wanted", headers=_hdr_uid(1))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data(as_text=True))
        self.assertIn("categories", data)
        self.assertIn("wanted_ids", data)
        self.assertEqual(data["wanted_ids"], [])
        self.assertGreaterEqual(len(data["categories"]), 1)
        for row in data["categories"]:
            self.assertEqual(set(row.keys()), {"id", "slug", "label"})

    def test_add_then_remove_via_replace(self) -> None:
        c1, c2 = self._cat_ids("coding", "music")
        h = _hdr_uid(1)

        r1 = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [c1, c2]}),
            content_type="application/json",
            headers=h,
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(json.loads(r1.get_data(as_text=True))["count"], 2)

        j2 = json.loads(self.client.get("/api/dashboard/wanted", headers=h).get_data(as_text=True))
        self.assertEqual(set(j2["wanted_ids"]), {c1, c2})

        # Remove one category (replacement semantics)
        r3 = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [c1]}),
            content_type="application/json",
            headers=h,
        )
        self.assertEqual(r3.status_code, 200)
        j3 = json.loads(self.client.get("/api/dashboard/wanted", headers=h).get_data(as_text=True))
        self.assertEqual(j3["wanted_ids"], [c1])

        # Clear all
        r4 = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": []}),
            content_type="application/json",
            headers=h,
        )
        self.assertEqual(r4.status_code, 200)
        j4 = json.loads(self.client.get("/api/dashboard/wanted", headers=h).get_data(as_text=True))
        self.assertEqual(j4["wanted_ids"], [])

    def test_duplicate_ids_in_request_deduplicate_cleanly(self) -> None:
        c1, *_ = self._cat_ids("coding")
        h = _hdr_uid(1)
        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [c1, c1, c1]}),
            content_type="application/json",
            headers=h,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.get_data(as_text=True))["count"], 1)

    def test_string_numeric_ids_accepted(self) -> None:
        c1, *_ = self._cat_ids("languages")
        h = _hdr_uid(1)
        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [str(c1)]}),
            content_type="application/json",
            headers=h,
        )
        self.assertEqual(r.status_code, 200)
        j = json.loads(self.client.get("/api/dashboard/wanted", headers=h).get_data(as_text=True))
        self.assertIn(c1, j["wanted_ids"])

    def test_unknown_category_ids_are_ignored_without_error(self) -> None:
        c1, *_ = self._cat_ids("coding")
        h = _hdr_uid(1)
        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [c1, 999_999]}),
            content_type="application/json",
            headers=h,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.get_data(as_text=True))["count"], 1)

    def test_users_have_independent_wanted_sets(self) -> None:
        c1, c2 = self._cat_ids("coding", "music")
        self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [c1]}),
            content_type="application/json",
            headers=_hdr_uid(1),
        )
        self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [c2]}),
            content_type="application/json",
            headers=_hdr_uid(2),
        )
        j1 = json.loads(
            self.client.get("/api/dashboard/wanted", headers=_hdr_uid(1)).get_data(as_text=True)
        )
        j2 = json.loads(
            self.client.get("/api/dashboard/wanted", headers=_hdr_uid(2)).get_data(as_text=True)
        )
        self.assertEqual(j1["wanted_ids"], [c1])
        self.assertEqual(j2["wanted_ids"], [c2])


class TestDashboardWantedFlaskLoginSession(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        with _session_scope(self.app) as s:
            s.add(User(id=7, email="seven@student.uwa.edu.au"))

    def _first_category_id(self, slug: str) -> int:
        with self.app.app_context():
            c = Category.query.filter_by(slug=slug).first()
            assert c is not None
            return c.id

    def test_post_works_after_test_login_without_x_user_header(self) -> None:
        c1 = self._first_category_id("sports")
        login = self.client.post("/auth/test-login", json={"user_id": 7})
        self.assertEqual(login.status_code, 200)

        r = self.client.post(
            "/api/dashboard/wanted",
            data=json.dumps({"category_ids": [c1]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        j = json.loads(self.client.get("/api/dashboard/wanted").get_data(as_text=True))
        self.assertIn(c1, j["wanted_ids"])


if __name__ == "__main__":
    unittest.main()
