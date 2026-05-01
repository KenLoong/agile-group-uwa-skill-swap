# =============================================================================
# Tests — registration to email-verification flow
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


class TestAuthRegistrationVerificationFlow(unittest.TestCase):
    def setUp(self) -> None:
        reset_default_verification_store()
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        reset_default_verification_store()

    def test_register_creates_unverified_user_and_sends_verification(self) -> None:
        r = self.client.post(
            "/auth/register",
            json={
                "display_name": "Alice",
                "email": "alice@student.uwa.edu.au",
                "password": "password123",
                "confirm_password": "password123",
            },
        )

        self.assertEqual(r.status_code, 201)
        data = r.get_json()

        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "verification_pending")

        with self.app.app_context():
            user = db.session.get(User, data["user_id"])
            self.assertIsNotNone(user)
            self.assertFalse(user.email_confirmed)
            self.assertTrue(user.password_hash)
            self.assertNotEqual(user.password_hash, "password123")

    def test_register_rejects_non_student_email(self) -> None:
        r = self.client.post(
            "/auth/register",
            json={
                "display_name": "Bob",
                "email": "bob@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )

        self.assertEqual(r.status_code, 400)
        body = r.get_json()

        self.assertFalse(body["ok"])
        self.assertIn("email", body["errors"])

    def test_register_rejects_duplicate_email(self) -> None:
        payload = {
            "display_name": "Carol",
            "email": "carol@student.uwa.edu.au",
            "password": "password123",
            "confirm_password": "password123",
        }

        first = self.client.post("/auth/register", json=payload)
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            "/auth/register",
            json={**payload, "display_name": "Carol2"},
        )
        self.assertEqual(second.status_code, 409)

    def test_verify_query_marks_user_confirmed(self) -> None:
        with self.app.app_context():
            user = User(
                email="verify@student.uwa.edu.au",
                username="verify",
                password_hash="hash",
                email_confirmed=False,
            )
            db.session.add(user)
            db.session.commit()

            raw = default_service.issue_for_new_user(user)
            signed = _sign_payload(user.id, raw)
            user_id = user.id

        r = self.client.get(f"/auth/verify?token={quote(signed, safe='')}")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])

        with self.app.app_context():
            refreshed = db.session.get(User, user_id)
            self.assertTrue(refreshed.email_confirmed)

    def test_verify_rejects_missing_token(self) -> None:
        r = self.client.get("/auth/verify")

        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.get_json()["ok"])


if __name__ == "__main__":
    unittest.main()