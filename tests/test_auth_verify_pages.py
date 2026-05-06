# =============================================================================
# Tests — browser-facing email verification result pages
# =============================================================================
from __future__ import annotations

import unittest
from urllib.parse import quote

from app import create_app
from api.tags_models import User, db
from auth.email_verification import (
    _sign_payload,
    default_service,
    reset_default_verification_store,
)


class TestAuthVerifyResultPages(unittest.TestCase):
    def setUp(self) -> None:
        reset_default_verification_store()
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        reset_default_verification_store()

    def _html_get(self, path: str):
        return self.client.get(path, headers={"Accept": "text/html"})

    def test_missing_token_renders_html_error_page(self) -> None:
        r = self._html_get("/auth/verify")

        self.assertEqual(r.status_code, 400)
        text = r.get_data(as_text=True)

        self.assertIn("Verification token missing", text)
        self.assertIn("Verification token is required.", text)

    def test_invalid_token_renders_html_error_page(self) -> None:
        r = self._html_get("/auth/verify?token=not-a-valid-token")

        self.assertEqual(r.status_code, 400)
        text = r.get_data(as_text=True)

        self.assertIn("Verification link invalid", text)
        self.assertIn("invalid or has already been used", text)

    def test_successful_token_renders_html_success_page(self) -> None:
        with self.app.app_context():
            user = User(
                email="result@student.uwa.edu.au",
                username="result",
                password_hash="hash",
                email_confirmed=False,
            )
            db.session.add(user)
            db.session.commit()

            raw = default_service.issue_for_new_user(user)
            signed = _sign_payload(user.id, raw)
            user_id = user.id

        r = self._html_get(f"/auth/verify?token={quote(signed, safe='')}")

        self.assertEqual(r.status_code, 200)
        text = r.get_data(as_text=True)

        self.assertIn("Email verified", text)
        self.assertIn("has been confirmed", text)

        with self.app.app_context():
            refreshed = db.session.get(User, user_id)
            self.assertTrue(refreshed.email_confirmed)

    def test_json_response_still_supported_for_tests_and_api_clients(self) -> None:
        r = self.client.get("/auth/verify")

        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.content_type, "application/json")
        self.assertEqual(r.get_json()["status"], "missing")

    def test_malformed_token_with_non_numeric_user_id_returns_json_invalid(self) -> None:
        r = self.client.get(
            "/auth/verify?token=raw-token|not-a-number|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.content_type, "application/json")

        body = r.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["status"], "invalid")
        self.assertIn("invalid", body["message"])

    def test_malformed_token_with_non_numeric_user_id_renders_html_invalid(self) -> None:
        r = self._html_get(
            "/auth/verify?token=raw-token|not-a-number|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

        self.assertEqual(r.status_code, 400)

        text = r.get_data(as_text=True)
        self.assertIn("Verification link invalid", text)
        self.assertIn("invalid or has already been used", text)


if __name__ == "__main__":
    unittest.main()