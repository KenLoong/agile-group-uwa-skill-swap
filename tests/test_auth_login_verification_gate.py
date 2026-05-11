# =============================================================================
# Tests — login verification gate
# =============================================================================
from __future__ import annotations

import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from api.tags_models import User, db
from auth.constants import ENV_EMAIL_VERIFY_REQUIRED_FOR_LOGIN


class TestAuthLoginVerificationGate(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def _create_user(
        self,
        *,
        email: str = "login@student.uwa.edu.au",
        username: str = "login",
        password: str = "password123",
        confirmed: bool = False,
    ) -> int:
        with self.app.app_context():
            user = User(
                email=email,
                username=username,
                password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
                email_confirmed=confirmed,
            )
            db.session.add(user)
            db.session.commit()
            return int(user.id)

    def _login(self, email: str, password: str):
        return self.client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

    def test_verified_user_can_login_when_gate_enabled(self) -> None:
        user_id = self._create_user(confirmed=True)
        self.app.config[ENV_EMAIL_VERIFY_REQUIRED_FOR_LOGIN] = True

        r = self._login("login@student.uwa.edu.au", "password123")

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("_user_id"), str(user_id))

    def test_unverified_user_blocked_when_gate_enabled(self) -> None:
        self._create_user(confirmed=False)
        self.app.config[ENV_EMAIL_VERIFY_REQUIRED_FOR_LOGIN] = True

        r = self._login("login@student.uwa.edu.au", "password123")

        self.assertEqual(r.status_code, 403)

        body = r.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["status"], "verification_required")

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("_user_id"))

    def test_unverified_user_can_login_when_gate_disabled(self) -> None:
        user_id = self._create_user(confirmed=False)
        self.app.config[ENV_EMAIL_VERIFY_REQUIRED_FOR_LOGIN] = False

        r = self._login("login@student.uwa.edu.au", "password123")

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])
        self.assertFalse(r.get_json()["email_confirmed"])

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("_user_id"), str(user_id))

    def test_wrong_password_rejected(self) -> None:
        self._create_user(confirmed=True)
        self.app.config[ENV_EMAIL_VERIFY_REQUIRED_FOR_LOGIN] = True

        r = self._login("login@student.uwa.edu.au", "wrong-password")

        self.assertEqual(r.status_code, 401)
        self.assertFalse(r.get_json()["ok"])

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("_user_id"))

    def test_missing_login_fields_rejected(self) -> None:
        r = self.client.post("/auth/login", json={})

        self.assertEqual(r.status_code, 400)

        body = r.get_json()
        self.assertFalse(body["ok"])
        self.assertIn("email", body["errors"])
        self.assertIn("password", body["errors"])


if __name__ == "__main__":
    unittest.main()