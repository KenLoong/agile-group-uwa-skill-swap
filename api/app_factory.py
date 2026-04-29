# =============================================================================
# Test factory — delegates to root app.create_app (blueprint-refactored)
# =============================================================================
# Tests and legacy imports use `api.app_factory.create_app`. The canonical
# implementation now lives in `app.py` after splitting routes into
# `blueprints/{auth,posts,api,messages}` to reduce merge conflicts.
# =============================================================================
from __future__ import annotations

from app import create_app as _create_app
from flask import Flask


def create_app(testing: bool = True) -> Flask:
    return _create_app(testing=testing)
