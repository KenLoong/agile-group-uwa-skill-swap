# =============================================================================
# String and lookup helpers for categories and tags (no Flask request context).
# =============================================================================
from __future__ import annotations

import re

# Mirrors draft-repo conventions: lowercase slug, hyphens between words.

_SLUG_SAFE = re.compile(r"[^a-z0-9_-]+")


def normalize_tag_slug(raw: str, *, max_len: int = 50) -> str:
    """
    Produce a URL-safe slug for tags: lowercase, collapse whitespace to hyphens,
    strip unsupported characters (alphanumeric, underscore, hyphen only).
    """
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip().lower().replace("_", "-")
    s = re.sub(r"\s+", "-", s)
    s = _SLUG_SAFE.sub("", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:max_len] if max_len else s


def normalize_category_slug(raw: str, *, max_len: int = 40) -> str:
    """Same rules as tags but bounded for category.slug column width."""
    return normalize_tag_slug(raw, max_len=max_len)


def display_label_or_slug(label: str, slug: str) -> str:
    """Prefer human label when non-empty; otherwise fall back to slug."""
    if label and label.strip():
        return label.strip()
    return slug


def explain_post_status_choices() -> tuple[tuple[str, str], ...]:
    """
    (value, short description) for docs and admin UIs — keep in sync with
    docs/POST_LIFECYCLE.md.
    """
    return (
        ("open", "Listing is visible and accepting interest."),
        ("matched", "Owner linked with a partner; may limit new interest."),
        ("closed", "Listing is inactive."),
    )


def is_allowed_post_status(value: object) -> bool:
    from api.tags_models import POST_STATUS_VALUES

    return isinstance(value, str) and value.strip().lower() in POST_STATUS_VALUES
