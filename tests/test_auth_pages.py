# ===============================================================
# Tests — browser-facing auth pages
# ===============================================================
from __future__ import annotations

import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from api.tags_models import User, db
from auth.email_verification import reset_default_verification_store


class TestAuthPages(unittest.TestCase):
    def setUp(self) -> None:
        reset_default_verification_store()
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        reset_default_verification_store()

    def test_login_page_renders_template_not_stub(self) -> None:
        r = self.client.get("/auth/login?next=/posts/create")

        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)

        self.assertIn("Log in", html)
        self.assertIn('name="next" value="/posts/create"', html)
        self.assertNotIn("auth/login stub", html)

    def test_register_page_renders_template_not_stub(self) -> None:
        r = self.client.get("/auth/register")

        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)

        self.assertIn("Create an account", html)
        self.assertIn("@student.uwa.edu.au", html)
        self.assertNotIn("auth/register stub", html)

    def test_form_login_success_redirects_to_next(self) -> None:
        with self.app.app_context():
            user = User(
                email="browser@student.uwa.edu.au",
                username="browser",
                password_hash=generate_password_hash("password123"),
                email_confirmed=True,
            )
            db.session.add(user)
            db.session.commit()

        r = self.client.post(
            "/auth/login",
            data={
                "email": "browser@student.uwa.edu.au",
                "password": "password123",
                "next": "/posts/create",
            },
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )

        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["Location"], "/posts/create")

    def test_form_login_error_renders_html_message(self) -> None:
        r = self.client.post(
            "/auth/login",
            data={
                "email": "missing@student.uwa.edu.au",
                "password": "wrong",
            },
            headers={"Accept": "text/html"},
        )

        self.assertEqual(r.status_code, 401)
        html = r.get_data(as_text=True)

        self.assertIn("Invalid email or password.", html)
        self.assertIn("Log in", html)

    def test_form_register_success_shows_pending_message(self) -> None:
        r = self.client.post(
            "/auth/register",
            data={
                "display_name": "Checkpoint User",
                "email": "checkpoint@student.uwa.edu.au",
                "password": "password123",
                "confirm_password": "password123",
            },
            headers={"Accept": "text/html"},
        )

        self.assertEqual(r.status_code, 201)
        html = r.get_data(as_text=True)

        self.assertIn("Check your inbox", html)
        self.assertIn("checkpoint@student.uwa.edu.au", html)

        with self.app.app_context():
            user = User.query.filter_by(email="checkpoint@student.uwa.edu.au").first()
            self.assertIsNotNone(user)
            assert user is not None
            self.assertFalse(user.email_confirmed)


if __name__ == "__main__":
    unittest.main()