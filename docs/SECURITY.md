# Security Configuration Notes

This document records security-related configuration expectations for the UWA Skill-Swap application.

## Secret key policy

`SECRET_KEY` is required for normal application runtime. It is used by Flask for session signing and by the email verification service for token signing and token hashing.

The application must not rely on a hard-coded development secret outside automated tests. If the app is started with `testing=False` and no `SECRET_KEY` is configured, app creation fails with a clear `RuntimeError`.

Automated unit tests may use the fixed `TEST_SECRET_KEY` constant from `auth.constants`. That value is only for isolated tests and must not be used for local development, demos, staging, or production-like runs.

## Local setup

Create a local `.env` file from `.env.example` and provide a long random value.

For macOS/Linux:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

For Windows PowerShell:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Paste the generated value into `.env`:

```text
SECRET_KEY=<generated-value>
```

Do not commit `.env`.

## Login rate limiting

`POST /auth/login` uses a small process-local rate limiter for failed login attempts.

The limiter tracks failed attempts by:

```text
client IP address + submitted email address
```

Only credential failures count as failed attempts. Missing form fields do not count, and a correct password that is blocked only because email verification is required does not count as a password failure.

The default configuration is:

```text
LOGIN_RATE_LIMIT_ENABLED=true
LOGIN_RATE_LIMIT_MAX_ATTEMPTS=5
LOGIN_RATE_LIMIT_WINDOW_SECONDS=600
```

When the limit is reached, the login route returns:

```json
{
  "ok": false,
  "status": "rate_limited",
  "message": "Too many failed login attempts. Please try again later.",
  "retry_after_seconds": 600
}
```

The current limiter is in-memory and process-local. This is appropriate for local coursework development and unit tests. A production multi-worker deployment should replace it with a shared store such as Redis or a database-backed counter.

Successful login clears the failed-attempt bucket for the same IP/email pair.

## Browser security headers

The Flask app applies standard browser security headers through `security/headers.py`.

Current response headers include:

| Header | Purpose |
| --- | --- |
| `Content-Security-Policy` | Restricts where scripts, styles, images, frames, and forms can load or submit. |
| `X-Content-Type-Options` | Uses `nosniff` to prevent MIME-type sniffing. |
| `X-Frame-Options` | Uses `DENY` to prevent clickjacking through frame embedding. |
| `Referrer-Policy` | Uses `strict-origin-when-cross-origin` to limit referrer leakage. |
| `Permissions-Policy` | Disables browser features the project does not need, such as camera, microphone, and geolocation. |

The current Content-Security-Policy is intentionally compatible with the repository's existing templates, which load Bootstrap from `cdn.jsdelivr.net` and jQuery from `code.jquery.com`.

The current CSP includes:

```text
default-src 'self'
base-uri 'self'
object-src 'none'
frame-ancestors 'none'
form-action 'self'
img-src 'self' data:
connect-src 'self'
font-src 'self' https://cdn.jsdelivr.net data:
style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'
script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com
```

`style-src` currently includes `'unsafe-inline'` because several templates still use small inline style blocks. A future hardening PR can remove inline styles or move them into static CSS files.

## HSTS policy

`Strict-Transport-Security` is disabled by default for local development because the app is normally run over plain HTTP at `127.0.0.1`.

To enable HSTS behind HTTPS, set:

```text
SECURITY_HSTS_ENABLED=true
```

Only enable this when the app is served over HTTPS. Do not enable HSTS for local HTTP-only demos.

## CSRF policy

Flask-WTF CSRF support is initialised through `security/csrf.py`.

The project uses the following standard AJAX headers:

```text
X-CSRFToken
X-CSRF-Token
```

Dynamic templates should expose the token through:

```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

Browser JavaScript should read this meta tag and send the token in the `X-CSRFToken` header for AJAX `POST` requests.

Current policy:

- FlaskForm submissions validate their own CSRF tokens through hidden form fields.
- AJAX routes should send `X-CSRFToken`.
- JSON CSRF errors should return a response with `error: "csrf_failed"` and a human-readable `message`.
- HTML/browser CSRF errors should show a readable security-check page.

`WTF_CSRF_CHECK_DEFAULT` is currently set to `False` in the central helper. This avoids accidentally breaking JSON API routes while they are still being finalised. Routes that require explicit CSRF enforcement can opt in as they are completed.

## Email verification tokens

Email verification token hashes and signatures use the configured application secret. This means:

- all workers must share the same `SECRET_KEY`;
- changing the secret invalidates outstanding verification links;
- raw tokens should not be logged;
- token tests should set an explicit test secret.

## Verification checks

Expected local checks:

```bash
python -m unittest tests.test_secret_key_config -v
python -m unittest tests.test_email_verification -v
```

Expected behaviour:

- test apps can be created without a real secret;
- runtime apps fail clearly when `SECRET_KEY` is missing;
- runtime apps accept `SECRET_KEY` from the environment;
- email verification token hashing fails clearly if no secret is configured.