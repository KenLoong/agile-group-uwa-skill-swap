# =============================================================================
# GET /api/stats — platform-wide KPIs / charts JSON (see docs/API_CONTRACTS.md)
# =============================================================================
from __future__ import annotations

from flask import Blueprint, jsonify

from services.stats_service import stats_public_payload

bp = Blueprint("stats_public", __name__, url_prefix="/api")


@bp.get("/stats")
def public_stats():
    return jsonify(stats_public_payload())
