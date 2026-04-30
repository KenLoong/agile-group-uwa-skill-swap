# =============================================================================
# Tests — SECRET_KEY configuration policy
# =============================================================================
from __future__ import annotations

import os
import unittest

from app import create_app
from auth.constants import TEST_SECRET_KEY
from auth.email_verification import _hash_token


class TestSecretKeyConfiguration(unittest.TestCase):
    def setUp(self) -> None:
        self._old_secret = os.environ.get("SECRET_KEY")
        os.environ.pop("SECRET_KEY", None)

    def tearDown(self) -> None:
        if self._old_secret is None:
            os.environ.pop("SECRET_KEY", None)
        else:
            os.environ["SECRET_KEY"] = self._old_secret

    def test_testing_app_uses_test_only_secret_when_missing(self) -> None:
        app = create_app(testing=True)

        self.assertTrue(app.config["TESTING"])
        self.assertEqual(app.config["SECRET_KEY"], TEST_SECRET_KEY)

    def test_runtime_app_requires_secret_key(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY must be set"):
            create_app(testing=False)

    def test_runtime_app_accepts_secret_key_from_environment(self) -> None:
        os.environ["SECRET_KEY"] = "local-test-secret-from-env"

        app = create_app(testing=False)

        self.assertEqual(app.config["SECRET_KEY"], "local-test-secret-from-env")

    def test_email_verification_hash_requires_secret_key(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY must be set"):
            _hash_token("raw-token")


if __name__ == "__main__":
    unittest.main()