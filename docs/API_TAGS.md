# `GET /api/tags` — testing and contract notes

This document accompanies the unit-test PR for the **tag metadata** endpoint used by the discover page (autocomplete, filter chips, and future tag cloud). It is written for **markers and teammates** who run the suite without the full draft application merged yet.

## Purpose

- Return a **JSON list** of tags that appear on **at least one** skill post, with **per-tag post counts**.
- Support three **data states** covered by automated tests:
  1. **Empty** — no tag–post associations (including “orphan” `Tag` rows with no posts).
  2. **Single-tag** — one tag string in the ecosystem, possibly many posts sharing it.
  3. **Multi-tag** — several tags; some posts carry more than one tag; counts must reflect **per-post** increments.

## Response shape (v1)

```http
GET /api/tags HTTP/1.1
```

```json
{
  "tags": [
    { "slug": "python", "label": "Python", "post_count": 3 }
  ],
  "meta": {
    "total_distinct": 1,
    "ms": null
  }
}
```

- **`slug`**: URL-safe identifier (lowercase, stable).
- **`label`**: Human-facing string (may contain spaces and title case).
- **`post_count`**: Integer number of **distinct posts** linked to that tag (one post with two tags increments both tags by 1).
- **`meta.total_distinct`**: Length of `tags` for quick UI checks.
- **`meta.ms`**: Optional float, may be filled when `FLASK_DEBUG=1` for local profiling (not a stability guarantee).

## HTTP semantics

- **200** for all successful reads; **no** pagination in v1.
- **`Cache-Control: public, max-age=60`** — safe to cache lightly; bump or add ETag later.
- Unknown query parameters (e.g. `?t=timestamp`) must not cause **500**; they are ignored in v1.

## Implementation boundaries (this branch)

- Uses `Post`, `Category`, `Tag`, and `post_tags` defined in `api/tags_models.py` (canonical naming aligned with the team draft baseline).
- SQL uses an **INNER** join from tags to posts so unused tag definitions do not appear.

## Running tests

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. python -m unittest tests.test_api_tags -v
```

## Future work (not in this issue)

- Add optional fields (uploads, like counts, etc.) to `Post` as separate issues.
- Add `?q=` prefix search and `?min_count=2` for advanced discover UIs.
- Harden against duplicate slug inserts at the form layer; API assumes integrity.

## Traceability to coursework rubric

- Demonstrates **automated** verification of an **AJAX-facing** JSON contract.
- Separates **empty / edge / load-multiplicity** cases so CI failures are easier to interpret than one giant test.
