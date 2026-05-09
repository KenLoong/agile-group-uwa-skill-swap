"""Render stored Markdown to safe HTML (server-side)."""
import re
from html import unescape

import bleach
import markdown

# Conservative allowlist for user-generated rich text.
_MD_ALLOWED_TAGS = frozenset({
    'p', 'br', 'strong', 'em', 'b', 'i', 'u', 'h1', 'h2', 'h3', 'h4',
    'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'hr', 'a', 'del', 'ins',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
})
_MD_ALLOWED_ATTRS = {
    'a': ['href', 'title', 'rel'],
    'th': ['colspan', 'rowspan'],
    'td': ['colspan', 'rowspan'],
}


def render_post_markdown(raw: str | None) -> str:
    if not raw:
        return ''
    html = markdown.markdown(
        raw,
        extensions=['extra', 'nl2br'],
        output_format='html5',
    )
    return bleach.clean(
        html,
        tags=_MD_ALLOWED_TAGS,
        attributes=_MD_ALLOWED_ATTRS,
        strip=True,
    )


def markdown_plain_snippet(raw: str | None, max_len: int = 120) -> str:
    """Preview line for cards — strip markup to plain text."""
    if not raw:
        return ''
    html = markdown.markdown(raw, extensions=['extra', 'nl2br'], output_format='html5')
    text = re.sub(r'<[^>]+>', ' ', html)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + '…'
