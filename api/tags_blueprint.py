# =============================================================================
# GET /api/tags — tag cloud / filter metadata for discover (JSON)
# =============================================================================
# Contract (v1, coursework):
#   200  application/json; charset=utf-8
#   { "tags": [ { "slug", "label", "post_count" } ], "meta": { "total_distinct": N } }
#
# - Only tags that appear on **at least one** post are listed (empty DB → tags: []).
# - Counts are **deduplicated per post** (a post with the same tag twice is impossible
#   with the M2M table; a post with two tags adds 1 to each tag's count).
# - Future: optional ?min_count=, ?q= prefix search — not implemented in this PR.
# =============================================================================
from __future__ import annotations

import time
from flask import Blueprint, jsonify, request

from api.tags_models import db, tag_payload_rows

bp = Blueprint("tags_api", __name__, url_prefix="/api")


@bp.get("/tags")
def list_tags_for_discover():
    """
    Public endpoint used by the discover page jQuery autocomplete / filter chips.
    No authentication required: tag names and counts are not sensitive.
    """
    # Early exit hints for ETag / caching in a later PR
    _ = request.args.get("t")  # reserved cache buster, ignored in v1
    _t0 = time.perf_counter()

    rows = tag_payload_rows()
    out = [
        {
            "slug": r["slug"],
            "label": r["label"],
            "post_count": int(r["cnt"]),
        }
        for r in rows
    ]
    body = {
        "tags": out,
        "meta": {
            "total_distinct": len(out),
            "ms": None,  # filled in dev only; avoid leaking perf in prod if needed
        },
    }
    if request.environ.get("FLASK_DEBUG") == "1":
        body["meta"]["ms"] = round((time.perf_counter() - _t0) * 1000, 3)

    resp = jsonify(body)
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp, 200
