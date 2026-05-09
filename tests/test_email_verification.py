# =============================================================================
# Unit tests — email verification service (in-memory; no Flask test client yet)
# =============================================================================
import os
import time
import unittest
from dataclasses import dataclass

from auth.email_verification import (
    EmailVerificationService,
    _InMemoryTokenStore,
    _hash_token,
    _parse_signed_payload,
    _sign_payload,
)
from auth.exceptions import ResendThrottledError, TokenExpiredError, TokenInvalidError
from auth.mailer import DevConsoleMailer
from auth.constants import TEST_SECRET_KEY


@dataclass
class _U:
    id: int
    email: str
    email_confirmed: bool = False


class TestEmailVerificationService(unittest.TestCase):
    def setUp(self) -> None:
        self._old_secret = os.environ.get("SECRET_KEY")
        os.environ["SECRET_KEY"] = TEST_SECRET_KEY

        self.store = _InMemoryTokenStore()
        self.svc = EmailVerificationService(
            self.store,
            mailer=lambda: DevConsoleMailer(),
            token_ttl=120,
        )

    def tearDown(self) -> None:
        if self._old_secret is None:
            os.environ.pop("SECRET_KEY", None)
        else:
            os.environ["SECRET_KEY"] = self._old_secret

    def test_issue_sends_routes_token(self) -> None:
        u = _U(1, "a@student.uwa.edu.au")
        raw = self.svc.issue_for_new_user(u)
        self.assertTrue(len(raw) > 8)

    def test_consumed_cannot_reuse(self) -> None:
        u = _U(2, "b@student.uwa.edu.au")
        raw = self.svc.issue_for_new_user(u)
        signed = _sign_payload(u.id, raw)
        uid = self.svc.verify_and_consume(signed)
        self.assertEqual(uid, 2)
        with self.assertRaises(TokenInvalidError):
            self.svc.verify_and_consume(signed)

    def test_wrong_mac_rejected(self) -> None:
        u = _U(3, "c@student.uwa.edu.au")
        raw = self.svc.issue_for_new_user(u)
        bad = raw + "|" + str(u.id) + "|" + "0" * 32
        with self.assertRaises(TokenInvalidError):
            self.svc.verify_and_consume(bad)

    def test_immediate_resend_throttled(self) -> None:
        u = _U(4, "d@student.uwa.edu.au")
        self.svc.issue_for_new_user(u)
        with self.assertRaises(ResendThrottledError):
            self.svc.resend(u)

    def test_expired_token_rejected(self) -> None:
        u = _U(5, "e@student.uwa.edu.au")
        self.svc = EmailVerificationService(self.store, token_ttl=1)
        raw = self.svc.issue_for_new_user(u)
        signed = _sign_payload(u.id, raw)
        time.sleep(1.1)
        with self.assertRaises(TokenExpiredError):
            self.svc.verify_and_consume(signed)

    def test_hash_token_stable_shape(self) -> None:
        h = _hash_token("x")
        self.assertEqual(len(h), 64)

    def test_malformed_signed_payloads_do_not_raise_parser_errors(self) -> None:
        malformed_tokens = [
            "",
            "only-one-part",
            "raw|not-a-number|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "raw|-1|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "raw|1|short",
            "raw|1|not-hex-not-hex-not-hex-000000",
            "|1|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "raw||aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "raw|1|",
            "raw|1|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|extra",
        ]

        for token in malformed_tokens:
            with self.subTest(token=token):
                self.assertIsNone(_parse_signed_payload(token))

                with self.assertRaises(TokenInvalidError):
                    self.svc.verify_and_consume(token)


    def test_parse_signed_payload_accepts_valid_shape(self) -> None:
        token = "raw-token|42|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        parsed = _parse_signed_payload(token)

        self.assertEqual(parsed, ("raw-token", 42, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))


if __name__ == "__main__":
    unittest.main()
