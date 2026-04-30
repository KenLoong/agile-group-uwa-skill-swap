# =============================================================================
# Email verification — configuration keys and defaults (scaffold)
# =============================================================================
#
# These names map 1:1 to environment variables documented in .env.example.
# Production will use real SMTP; local dev uses DevConsoleMailer (stdout only).
#
# -----------------------------------------------------------------------------

# Minimum hours before the same email can request another verification link
# (anti-abuse; set low in dev, higher in production).
EMAIL_VERIFY_RESEND_COOLDOWN_HOURS = 0.01  # ~36 seconds, for local demos only

# Default lifetime of a signed link once issued (in seconds)
EMAIL_VERIFY_TOKEN_TTL_SECONDS = 48 * 60 * 60  # 48h — adjust in env for coursework demo

# Query param / route segment names (keep stable; linked from outgoing mail templates)
EMAIL_VERIFY_URL_QUERY_TOKEN = "token"
EMAIL_VERIFY_URL_QUERY_USER = "uid"

# Flask application secret key. Runtime must provide this outside tests.
ENV_SECRET_KEY = "SECRET_KEY"

# Fixed value for isolated unit tests only. Do not use for local development,
# demos, staging, or production.
TEST_SECRET_KEY = "test-only-secret-key"

# Feature flags (string env, parsed in service)
ENV_EMAIL_VERIFY_ENABLED = "EMAIL_VERIFICATION_ENABLED"
ENV_EMAIL_VERIFY_REQUIRED_FOR_LOGIN = "REQUIRE_VERIFIED_EMAIL_TO_LOGIN"
ENV_SMTP_HOST = "SMTP_HOST"
ENV_SMTP_PORT = "SMTP_PORT"
ENV_SMTP_USER = "SMTP_USER"
ENV_SMTP_PASSWORD = "SMTP_PASSWORD"
ENV_EMAIL_FROM = "EMAIL_FROM"
ENV_BASE_URL = "PUBLIC_BASE_URL"

# ---------------------------------------------------------------------------
# Placeholder used in HTML mock pages; replace when Jinja base lands.
# ---------------------------------------------------------------------------
MOCK_VERIFICATION_LANDING = "verify-result.html"
MOCK_VERIFICATION_PENDING = "verify-pending.html"
