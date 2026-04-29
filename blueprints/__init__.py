# =============================================================================
# URL blueprints — split to reduce merge conflicts and clarify module ownership
# =============================================================================
# auth:    session / email / UWA account flows
# posts:   skill listings, set-status, CRUD
# api:     JSON endpoints shared by discover and mobile clients
# messages:  private threads and notifications (stub in early sprints)
# =============================================================================
from __future__ import annotations

__all__ = [
    "auth",
    "posts",
    "api",
    "messages",
]
