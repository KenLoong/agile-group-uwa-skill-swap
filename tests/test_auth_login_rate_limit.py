# =============================================================================
# Tests — login rate limiting
# =============================================================================
from __future__ import annotations

import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from api.tags_models import User, db
from security.rate_limit import (
    ENV_LOGIN_RATE_LIMIT_ENABLED,
    ENV_LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    ENV_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    reset_default_login_rate_limiter,
)


class TestAuthLoginRateLimit(unittest.TestCase):
    def setUp(self) -> None:
        reset_default_login_rate_limiter()
        self.app = create_app(
            testing=True,
            test_config={
                ENV_LOGIN_RATE_LIMIT_ENABLED: True,
                ENV_LOGIN_RATE_LIMIT_MAX_ATTEMPTS: 3,
                ENV_LOGIN_RATE_LIMIT_WINDOW_SECONDS: 600,
            },
        )
        self.client = self.app.test_client()
        self._create_user()

    def tearDown(self) -> None:
        reset_default_login_rate_limiter()

    def _create_user(
        self,
        *,
        email: str = "limited@student.uwa.edu.au",
        username: str = "limited",
        password: str = "password123",
        confirmed: bool = True,
    ) -> int:
        with self.app.app_context():
            user = User(
                email=email,
                username=username,
                password_hash=generate_password_hash(password),
                email_confirmed=confirmed,
            )
            db.session.add(user)
            db.session.commit()
            return int(user.id)

    def _login(
        self,
        *,
        email: str = "limited@student.uwa.edu.au",
        password: str = "wrong-password",
        remote_addr: str = "127.0.0.1",
    ):
        return self.client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
            environ_base={"REMOTE_ADDR": remote_addr},
        )

    def test_repeated_wrong_password_attempts_are_rate_limited(self) -> None:
        for _ in range(3):
            r = self._login()
            self.assertEqual(r.status_code, 401)

        limited = self._login()

        self.assertEqual(limited.status_code, 429)

        body = limited.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["status"], "rate_limited")
        self.assertIn("retry_after_seconds", body)

    def test_successful_login_resets_failed_attempt_counter(self) -> None:
        for _ in range(2):
            r = self._login()
            self.assertEqual(r.status_code, 401)

        success = self._login(password="password123")
        self.assertEqual(success.status_code, 200)
        self.assertTrue(success.get_json()["ok"])

        # After reset, this should be the first new failed attempt, not a limit.
        again = self._login()
        self.assertEqual(again.status_code, 401)

    def test_rate_limit_is_scoped_by_email(self) -> None:
        for _ in range(3):
            r = self._login(email="limited@student.uwa.edu.au")
            self.assertEqual(r.status_code, 401)

        other = self._login(email="someoneelse@student.uwa.edu.au")
        self.assertEqual(other.status_code, 401)

        blocked = self._login(email="limited@student.uwa.edu.au")
        self.assertEqual(blocked.status_code, 429)

    def test_rate_limit_is_scoped_by_remote_address(self) -> None:
        for _ in range(3):
            r = self._login(remote_addr="10.0.0.1")
            self.assertEqual(r.status_code, 401)

        other_ip = self._login(remote_addr="10.0.0.2")
        self.assertEqual(other_ip.status_code, 401)

        blocked = self._login(remote_addr="10.0.0.1")
        self.assertEqual(blocked.status_code, 429)

    def test_rate_limit_can_be_disabled_by_config(self) -> None:
        self.app.config[ENV_LOGIN_RATE_LIMIT_ENABLED] = False

        for _ in range(6):
            r = self._login()
            self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()