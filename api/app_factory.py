# =============================================================================
# Test factory — delegates to root app.create_app (blueprint-refactored)
# =============================================================================
# Tests and legacy imports use `api.app_factory.create_app`. The canonical
# implementation now lives in `app.py` after splitting routes into
# `blueprints/{auth,posts,api,messages}` to reduce merge conflicts.
# =============================================================================
from __future__ import annotations

from typing import Any

from app import create_app as _create_app
from flask import Flask


def create_app(testing: bool = True, test_config: dict[str, Any] | None = None) -> Flask:
    return _create_app(testing=testing, test_config=test_config)
