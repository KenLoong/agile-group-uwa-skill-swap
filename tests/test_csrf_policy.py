# =============================================================================
# Tests — CSRF policy and template exposure
# =============================================================================
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from api.app_factory import create_app
from api.tags_models import User, db
from security.csrf import (
    CSRF_AJAX_HEADER,
    CSRF_ALT_AJAX_HEADER,
    DEFAULT_CSRF_TIME_LIMIT_SECONDS,
)


class TestCsrfPolicyConfiguration(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def test_app_configures_standard_csrf_headers(self) -> None:
        headers = self.app.config["WTF_CSRF_HEADERS"]

        self.assertIn(CSRF_AJAX_HEADER, headers)
        self.assertIn(CSRF_ALT_AJAX_HEADER, headers)
        self.assertEqual(
            self.app.config["WTF_CSRF_TIME_LIMIT"],
            DEFAULT_CSRF_TIME_LIMIT_SECONDS,
        )

    def test_global_csrf_check_is_not_forced_for_all_json_routes(self) -> None:
        self.assertFalse(self.app.config["WTF_CSRF_CHECK_DEFAULT"])

    def test_create_post_template_exposes_hidden_field_and_meta_token(self) -> None:
        self._seed_user_login()

        r = self.client.get("/posts/create")
        self.assertEqual(r.status_code, 200)

        html = r.get_data(as_text=True)

        self.assertIn('name="csrf_token"', html)
        self.assertIn('name="csrf-token"', html)

        meta = re.search(r'<meta name="csrf-token" content="([^"]+)">', html)
        self.assertIsNotNone(meta)
        assert meta is not None
        self.assertTrue(meta.group(1))

    def test_dashboard_javascript_sends_standard_csrf_header(self) -> None:
        js = Path("static/js/dashboard.js").read_text(encoding="utf-8")

        self.assertIn('meta[name="csrf-token"]', js)
        self.assertIn("'X-CSRFToken'", js)

    def _seed_user_login(self) -> int:
        with self.app.app_context():
            u = User(id=123, email="csrf@student.uwa.edu.au")
            db.session.add(u)
            db.session.commit()
            uid = int(u.id)

        r = self.client.post("/auth/test-login", json={"user_id": uid})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(json.loads(r.get_data(as_text=True)).get("ok"))

        return uid


if __name__ == "__main__":
    unittest.main()