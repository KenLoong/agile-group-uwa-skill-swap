# Email verification (post-registration)

This document describes the **UWA student email** confirmation flow for Skill-Swap.
Implementation lives in `auth/` and is wired into the Flask auth blueprint through `blueprints/auth.py`.

## Goals

- Prove that a registrant controls their `@student.uwa.edu.au` address before we show contact details or “interest” features.
- Let users **re-send** the email if the link expired (with rate limits).
- Keep **unverified** accounts from logging in when `REQUIRE_VERIFIED_EMAIL_TO_LOGIN=true` (enforced in the future `login` view).

## User journey

1. **Register** with display name, UWA email, and password.  
2. The server creates a `users` row with `email_confirmed = false` (or `email_verified_at = null`).  
3. `EmailVerificationService.issue_for_new_user()` is called, which:
   - stores a one-time token (hashed) with expiry,
   - sends email via the configured **mail backend** (console in dev, SMTP in prod).
4. The user opens the link: `/auth/verify?token=…`.
5. `verify_and_consume()` checks signature, hash, single-use, and TTL, then sets the user to verified.  
6. If they never receive mail: **resend** from the “pending verification” page (throttled).

## Browser-facing verification results

When a student opens a verification link from email, the browser receives a human-readable result page.

Supported outcomes:

| Status | Meaning |
| --- | --- |
| `verified` | The token was valid and the account email was confirmed. |
| `expired` | The token existed but exceeded the configured TTL. |
| `invalid` | The token was malformed, replayed, or failed signature validation. |
| `missing` | The request did not include a token. |
| `not_found` | The token was valid but the linked user row no longer exists. |

API-style clients and unit tests can still receive JSON responses. Browser requests that prefer `text/html` receive an HTML result page.

## Environment variables

| Variable | Meaning |
|----------|--------|
| `EMAIL_VERIFICATION_ENABLED` | `true` / `false` (feature flag). |
| `REQUIRE_VERIFIED_EMAIL_TO_LOGIN` | Block session creation until confirmed. |
| `PUBLIC_BASE_URL` | Base for links, e.g. `https://skill-swap.uwa…` in prod. |
| `EMAIL_FROM` | From header for all outbound mail. |
| `EMAIL_BACKEND` | `console` (dev) or `smtp`. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Used when `EMAIL_BACKEND=smtp`. |
| `SECRET_KEY` | Required outside tests. Used to sign and hash verification tokens; must match on all workers. |

## Security considerations (course-friendly checklist)

- **No secrets in the URL** except the signed, time-limited token.  
- **Single-use** tokens: consume on success.  
- **Resend throttling** to limit abuse to our mail relay and student inboxes.  
- **Log hygiene**: never log full tokens in production.  
- **UWA only**: registration already restricted to the student email domain.  

## Testing

```bash
python -m unittest tests.test_auth_verify_pages -v
python -m unittest tests.test_auth_registration -v
python -m unittest tests.test_email_verification -v
```

For an interactive smoke, run `python -m auth.email_verification` to print a dev-console email.

## Open items (next PRs)

- [ ] SQLAlchemy model for `EmailVerificationToken` if we need server restart survival.  
- [ ] Jinja2 templates for HTML mail instead of inline strings.  
- [ ] Queue (Redis / Celery) for SMTP retries.  
- [ ] Rate limit `POST /auth/resend` at the HTTP layer (Flask-Limiter).  

## FAQ

**Q. Why in-memory store in this PR?**  
A. So the team can show **working unit tests and structure** before the full DB merge, without blocking other parallel HTML work.

**Q. Is this production-ready?**  
A. No; it is a **scaffold** with explicit upgrade paths in comments and this doc.
