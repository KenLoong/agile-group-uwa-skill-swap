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