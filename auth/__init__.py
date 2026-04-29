"""
Authentication-related packages for UWA Skill-Swap.

The `email_verification` sub-module is imported incrementally as the Flask
application grows; keeping it in a dedicated package avoids circular imports
once `app.py` wires models, forms, and blueprints together.
"""

from auth.email_verification import (
    EmailVerificationService,
    VerificationTokenRecord,
    default_service,
)

__all__ = [
    "EmailVerificationService",
    "VerificationTokenRecord",
    "default_service",
]
