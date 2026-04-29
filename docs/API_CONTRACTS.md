# API Contracts

This document defines the expected JSON API contracts used by the UWA Skill-Swap browser client.

The contracts are aligned with the current repository structure, including the Flask blueprint layout, the existing `/api/tags` documentation, the static page interactions, and the system architecture notes in the README.

The goal is to keep frontend behaviour, Flask route implementation, and future tests consistent as the project grows.

## Overview

| Endpoint | Method | Auth required | Main consumer | Purpose |
| --- | --- | --- | --- | --- |
| `/api/filter` | `GET` | No | Discover page JavaScript | Filter and paginate visible skill posts |
| `/api/tags` | `GET` | No | Discover page / tag UI | Return tag metadata and post counts |
| `/api/stats` | `GET` | No | Public stats page | Return platform-wide chart data |
| `/api/dashboard/charts` | `GET` | Yes | Dashboard chart tab | Return current user's personal chart data |

All endpoints return JSON. Error responses should also use JSON where the request was made as an API/AJAX request.

---

## Common response conventions

### Content type

Successful API responses should return:

```http
Content-Type: application/json
```

### Error shape

Where possible, API errors should use this shape:

```json
{
  "message": "Human-readable error message"
}
```

For validation-style errors, a future extension may use:

```json
{
  "message": "Validation failed",
  "errors": {
    "field_name": ["Specific field error"]
  }
}
```

### Common status codes

| Status | Meaning |
| --- | --- |
| `200` | Successful read |
| `400` | Invalid query parameter or malformed request |
| `401` | Login required for API request |
| `403` | Logged-in user is not allowed to access the resource |
| `404` | Endpoint or referenced resource does not exist |
| `500` | Unexpected server error |

---

# `GET /api/filter`

## Purpose

Returns filtered and paginated skill posts for the discover page.

This endpoint is consumed by the discover page AJAX script when a user changes category, tag, search text, sort order, or page number.

## Authentication

No login required.

## Query parameters

| Parameter | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `category` | string | No | `all` | Category slug. `all` means no category filter. |
| `tag` | string | No | empty string | Tag slug. Empty means no tag filter. |
| `query` | string | No | empty string | Search text matched against title and description. |
| `sort` | string | No | `newest` | Supported values: `newest`, `popular`, `likes`. Invalid values should fall back to `newest`. |
| `page` | integer | No | `1` | Page number for paginated results. |

## Example request

```http
GET /api/filter?category=coding&tag=python&query=flask&sort=newest&page=1
```

## Success response

```json
{
  "posts": [
    {
      "id": 12,
      "title": "Python Flask Help",
      "category_slug": "coding",
      "category_label": "Coding",
      "author": "alice",
      "author_profile": "/user/alice",
      "snippet": "I can help with Flask routes and SQLAlchemy models...",
      "timestamp": "2026-04-27",
      "comment_count": 2,
      "like_count": 5,
      "status": "open",
      "tags": [
        {
          "slug": "python",
          "label": "Python"
        },
        {
          "slug": "flask",
          "label": "Flask"
        }
      ],
      "image_url": "/static/uploads/posts/example.jpg"
    }
  ],
  "page": 1,
  "pages": 3,
  "has_next": true,
  "has_prev": false
}
```

## Field notes

| Field | Meaning |
| --- | --- |
| `posts` | Array of post card objects for the current page. |
| `id` | Numeric post identifier. |
| `title` | User-facing post title. |
| `category_slug` | Stable category identifier for filtering. |
| `category_label` | Human-readable category label. |
| `author` | Username of post owner. |
| `author_profile` | URL path for the author's profile page. |
| `snippet` | Plain-text shortened description for card display. |
| `timestamp` | Display date in `YYYY-MM-DD` format. |
| `comment_count` | Number of comments on the post. |
| `like_count` | Number of likes on the post. |
| `status` | Post lifecycle state, normally `open`, `matched`, or `closed`. |
| `tags` | Array of tag objects with `slug` and `label`. |
| `image_url` | Image path if a cover image exists; otherwise `null`. |
| `page` | Current page number. |
| `pages` | Total number of pages. |
| `has_next` | Whether another page is available. |
| `has_prev` | Whether a previous page is available. |

## Empty result

```json
{
  "posts": [],
  "page": 1,
  "pages": 0,
  "has_next": false,
  "has_prev": false
}
```

## Error behaviour

- Invalid `sort` should fall back to `newest`.
- Invalid or empty `category` should not crash the endpoint.
- Invalid `page` should be handled by pagination defaults where possible.
- Unexpected server errors should return a JSON `message` field.

## Implementation status

This endpoint belongs to the JSON API layer described by the repository's blueprint structure. It should be implemented under the API blueprint so that the discover page can request filtered post data without reloading the full page.

---

# `GET /api/tags`

## Purpose

Returns tags that appear on skill posts, with per-tag post counts.

This endpoint supports discover page tag filtering and future autocomplete/tag cloud UI.

## Authentication

No login required.

## Query parameters

Current v1 behaviour:

| Parameter | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| none | - | - | - | v1 returns in-use tags. |

Potential future parameters:

| Parameter | Type | Notes |
| --- | --- | --- |
| `q` | string | Future prefix/autocomplete search. |
| `min_count` | integer | Future tag cloud filtering. |

## Example request

```http
GET /api/tags
```

## Success response

```json
{
  "tags": [
    {
      "slug": "python",
      "label": "Python",
      "post_count": 3
    },
    {
      "slug": "music",
      "label": "Music",
      "post_count": 1
    }
  ],
  "meta": {
    "total_distinct": 2,
    "ms": null
  }
}
```

## Field notes

| Field | Meaning |
| --- | --- |
| `tags` | Array of tag metadata objects. |
| `slug` | URL-safe tag identifier. |
| `label` | Human-readable tag label. |
| `post_count` | Number of posts associated with the tag. |
| `meta.total_distinct` | Number of returned tag objects. |
| `meta.ms` | Optional timing/debug field. Not guaranteed for stable UI logic. |

## Empty result

```json
{
  "tags": [],
  "meta": {
    "total_distinct": 0,
    "ms": null
  }
}
```

## Error behaviour

- Unknown query parameters should be ignored in v1.
- Tags with zero post associations should not appear.
- The endpoint should not return `500` for an empty database.

## Implementation status

The repository already contains dedicated `/api/tags` notes in [`API_TAGS.md`](API_TAGS.md). This section summarizes the endpoint so that the tag contract is visible alongside the other AJAX-facing API routes.

---

# `GET /api/stats`

## Purpose

Returns platform-wide statistics used by the public stats page.

The frontend uses this payload to render KPI counters and charts.

## Authentication

No login required.

## Query parameters

None in v1.

## Example request

```http
GET /api/stats
```

## Success response

```json
{
  "totals": {
    "posts": 24,
    "users": 8,
    "comments": 19,
    "tags": 11
  },
  "category_counts": [
    {
      "label": "Coding",
      "count": 7
    },
    {
      "label": "Language",
      "count": 5
    }
  ],
  "trend_30": [
    {
      "date": "2026-03-29",
      "count": 0
    },
    {
      "date": "2026-03-30",
      "count": 2
    }
  ],
  "top_users": [
    {
      "username": "alice",
      "post_count": 4,
      "total_likes": 12
    }
  ]
}
```

## Field notes

| Field | Meaning |
| --- | --- |
| `totals.posts` | Total number of posts. |
| `totals.users` | Total number of users. |
| `totals.comments` | Total number of comments. |
| `totals.tags` | Total number of tags. |
| `category_counts` | Array of post counts grouped by category. |
| `category_counts[].label` | Human-readable category name. |
| `category_counts[].count` | Number of posts in the category. |
| `trend_30` | Array of daily new-post counts for the last 30 days. |
| `trend_30[].date` | Date string in `YYYY-MM-DD` format. |
| `trend_30[].count` | Number of posts created on that date. |
| `top_users` | Top users by post count and total likes. |
| `top_users[].username` | Username. |
| `top_users[].post_count` | Number of posts by that user. |
| `top_users[].total_likes` | Sum of likes across that user's posts. |

## Error behaviour

- Empty datasets should return zero counts and empty arrays where appropriate.
- Date ranges should still return 30 entries with zero-filled missing days.
- Unexpected server errors should return a JSON `message` field.

## Implementation status

This endpoint is part of the public statistics API contract. It should return stable JSON shapes for chart rendering, even when the database is empty.

---

# `GET /api/dashboard/charts`

## Purpose

Returns chart data for the logged-in user's personal dashboard.

The dashboard chart tab uses this endpoint to show the user's category distribution and recent engagement on their own posts.

## Authentication

Login required.

Unauthenticated users should be redirected to login for normal browser navigation, or return a JSON `401` response for API/AJAX requests depending on final auth handling.

## Query parameters

None in v1.

## Example request

```http
GET /api/dashboard/charts
```

## Success response

```json
{
  "category_distribution": [
    {
      "label": "Coding",
      "count": 3
    },
    {
      "label": "Music",
      "count": 1
    }
  ],
  "daily_activity": [
    {
      "date": "2026-03-29",
      "likes": 0,
      "interests": 0
    },
    {
      "date": "2026-03-30",
      "likes": 2,
      "interests": 1
    }
  ]
}
```

## Field notes

| Field | Meaning |
| --- | --- |
| `category_distribution` | Post counts grouped by category for the current user's own posts. |
| `category_distribution[].label` | Human-readable category name. |
| `category_distribution[].count` | Number of current-user posts in that category. |
| `daily_activity` | Daily likes and interest events on the current user's posts for the last 30 days. |
| `daily_activity[].date` | Date string in `YYYY-MM-DD` format. |
| `daily_activity[].likes` | Number of likes received on the user's posts on that day. |
| `daily_activity[].interests` | Number of interest events received on the user's posts on that day. |

## Empty result

A logged-in user with no posts should receive:

```json
{
  "category_distribution": [],
  "daily_activity": [
    {
      "date": "2026-03-29",
      "likes": 0,
      "interests": 0
    }
  ]
}
```

The real response should contain the full 30-day zero-filled `daily_activity` array.

## Error behaviour

| Scenario | Expected behaviour |
| --- | --- |
| Not logged in | `401` JSON response or login redirect, depending on final Flask-Login integration. |
| No posts | Return empty distribution and zero-filled activity. |
| No likes/interests | Return dates with `0` values. |
| Unexpected server error | Return JSON `message` field. |

## Implementation status

This endpoint is part of the authenticated dashboard API contract. It should return user-specific chart data for the currently logged-in user and should not expose other users' private dashboard information.

---

## Frontend consumers

| Endpoint | Frontend consumer |
| --- | --- |
| `/api/filter` | `static/js/discover.js` |
| `/api/tags` | Discover/tag UI and `docs/API_TAGS.md` scaffold |
| `/api/stats` | `static/js/stats.js` |
| `/api/dashboard/charts` | `static/js/dashboard_charts.js` |

---

## Notes for future implementation PRs

- If the final implementation changes a field name, update this document and the consuming JavaScript in the same PR.
- Prefer stable JSON object shapes over returning raw arrays, except where a legacy endpoint already requires an array.
- API endpoints should avoid returning raw HTML error pages to AJAX clients.
- Authentication-sensitive endpoints should clearly distinguish unauthenticated and unauthorized cases.