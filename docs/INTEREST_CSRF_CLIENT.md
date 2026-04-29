# Interest POST and CSRF — client-side feedback

This page explains how the **static mock** (pages under `pages/`) prepares for the production behaviour: when a user clicks **Express interest**, the browser sends `POST /interest/<post_id>` with a CSRF token. If the token is missing or invalid, the Flask stack often responds with a **JSON** error body. Students using the dashboard should see a **plain-language toast**, not a raw JSON blob.

## What was wrong in the old UX

- The network layer returned JSON (for example, `{"message": "The CSRF token is missing."}`).
- The client did not branch on `Content-Type: application/json` for user-facing copy.
- Screen-reader users had no `aria-live` update when the action failed.

## What this PR changes

- Adds `static/js/interest-csrf-client.js`, which:
  - reads CSRF from `<meta name="csrf-token">` (and optional cookies as a future fallback);
  - sends `X-CSRFToken` on interest POSTs;
  - maps 400/403 and JSON `message` fields into **short** strings;
  - shows **Bootstrap 5 toasts** and updates a **visually hidden** `aria-live` region.
- Adds `static/css/interest-feedback.css` for long-message wrapping and screen-reader text.
- Updates **Dashboard** and **Post detail** mockups with:
  - a help panel and **demo buttons** that simulate the 400 + JSON case without a server;
  - live-region placeholder elements.

## How to test without Flask

- Open `pages/dashboard.html` or `pages/post-detail.html` in a browser (via a static server if needed).
- Click **Simulate: CSRF missing (demo)** or **Trigger mock 400 (CSRF JSON)**.
- You should see a **toast** and the live region should receive a non-empty status string.

## How to test with Flask (later)

When the draft backend is merged:

- Ensure `base.html` (or the layout) outputs:

  - `<meta name="csrf-token" content="{{ csrf_token() }}">` or equivalent;
  - the same `POST` field name expected by `Flask-WTF` if you do not use header-only.

- Re-run the interest flow; missing token can be tested by **invalidating the meta** in devtools to confirm the toast.

## Out of scope

- Server-side error message rewording.
- i18n / translations.
- WebSocket or polling for “interest received”.

## Reviewer checklist

- Toasts are dismissible and do not trap focus.
- No raw server JSON is shown to non-developers in the main path.
- Live region updates on both success and failure for assistive technology.
