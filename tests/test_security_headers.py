# =============================================================================
# Tests — browser security response headers
# =============================================================================
from __future__ import annotations

import unittest

from app import create_app
from security.headers import (
    DEFAULT_CONTENT_TYPE_OPTIONS,
    DEFAULT_FRAME_OPTIONS,
    DEFAULT_PERMISSIONS_POLICY,
    DEFAULT_REFERRER_POLICY,
    ENV_SECURITY_HSTS_ENABLED,
    SECURITY_HEADER_CONTENT_TYPE_OPTIONS,
    SECURITY_HEADER_CSP,
    SECURITY_HEADER_FRAME_OPTIONS,
    SECURITY_HEADER_HSTS,
    SECURITY_HEADER_PERMISSIONS_POLICY,
    SECURITY_HEADER_REFERRER_POLICY,
    build_content_security_policy,
)


class TestSecurityHeaders(unittest.TestCase):
    def test_root_response_includes_standard_security_headers(self) -> None:
        app = create_app(testing=True)
        client = app.test_client()

        r = client.get("/")

        self.assertEqual(r.status_code, 200)
        self.assertIn(SECURITY_HEADER_CSP, r.headers)
        self.assertEqual(
            r.headers[SECURITY_HEADER_CONTENT_TYPE_OPTIONS],
            DEFAULT_CONTENT_TYPE_OPTIONS,
        )
        self.assertEqual(r.headers[SECURITY_HEADER_FRAME_OPTIONS], DEFAULT_FRAME_OPTIONS)
        self.assertEqual(
            r.headers[SECURITY_HEADER_REFERRER_POLICY],
            DEFAULT_REFERRER_POLICY,
        )
        self.assertEqual(
            r.headers[SECURITY_HEADER_PERMISSIONS_POLICY],
            DEFAULT_PERMISSIONS_POLICY,
        )

    def test_csp_allows_current_template_cdn_sources(self) -> None:
        csp = build_content_security_policy()

        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("form-action 'self'", csp)
        self.assertIn("https://cdn.jsdelivr.net", csp)
        self.assertIn("https://code.jquery.com", csp)

    def test_hsts_disabled_by_default_for_local_testing(self) -> None:
        app = create_app(testing=True)
        client = app.test_client()

        r = client.get("/")

        self.assertNotIn(SECURITY_HEADER_HSTS, r.headers)

    def test_hsts_can_be_enabled_by_app_config(self) -> None:
        app = create_app(
            testing=True,
            test_config={
                ENV_SECURITY_HSTS_ENABLED: True,
            },
        )
        client = app.test_client()

        r = client.get("/")

        self.assertIn(SECURITY_HEADER_HSTS, r.headers)
        self.assertIn("max-age=", r.headers[SECURITY_HEADER_HSTS])


if __name__ == "__main__":
    unittest.main()