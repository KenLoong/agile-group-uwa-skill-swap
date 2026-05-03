# =============================================================================
# GET /api/filter — normalise request arguments (search text, pagination window)
# =============================================================================
# Clearing the discover search field in the UI must reliably drop the previous
# text filter without stale alternate query keys widening or narrowing counts
# relative to rendered cards. When the filtered set shrinks (e.g. user clears the
# search box while staying on category + a high ``page``), the server must clamp
# to a valid window so totals, pagination flags, and ``posts`` stay aligned.
# =============================================================================
from __future__ import annotations

from typing import Any


def normalized_search_expression(req: Any) -> str:
    """
    Return trimmed text matched against Post title/description.

    Precedence avoids stale keyword arguments when callers send both canonical
    ``query`` (possibly empty meaning “clear search”) and legacy ``q``/``search``.

    * If ``query`` appears at all (even blank), ``query`` wins after ``strip()`` —
      so ``?category=coding&q=bugs&query=`` applies **no** text filter despite ``q``.
    * Else the first populated value among ``q``, ``search`` is used.

    Behaviour is unchanged for callers that only pass ``query=…`` without other keys.
    """
    q_arg = getattr(req, "args", None)
    if q_arg is None:
        return ""

    if "query" in q_arg:
        return _strip_or_empty(q_arg.get("query"))

    for fallback in ("q", "search"):
        if fallback in q_arg:
            return _strip_or_empty(q_arg.get(fallback))

    return ""


def _strip_or_empty(raw: Any) -> str:
    return str(raw).strip() if raw is not None else ""


def paginate_filter_results(base_query: Any, *, page: int, per_page: int) -> Any:
    """
    Run Flask-SQLAlchemy pagination with ``error_out=False`` and clamp impossible
    page indices so payloads stay internally consistent:

    * If ``total == 0``, response page is normalised via a second fetch at ``page=1``.
    * If the client requests ``page`` greater than ``pages`` but rows exist,
      repeat pagination at ``page=pages`` so ``posts`` is non-empty whenever the filter
      has matches.

    Returns the final :class:`~flask_sqlalchemy.pagination.QueryPagination` object.
    """
    pag = base_query.paginate(page=page, per_page=per_page, error_out=False)
    total = int(pag.total or 0)

    if total <= 0 and pag.page != 1:
        return base_query.paginate(page=1, per_page=per_page, error_out=False)

    pages = pag.pages
    if pages and pag.page > pages:
        return base_query.paginate(page=pages, per_page=per_page, error_out=False)

    return pag


__all__ = ["normalized_search_expression", "paginate_filter_results"]
