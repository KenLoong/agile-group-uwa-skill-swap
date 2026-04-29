"""Narrow exception types for the verification service (explicit handling in routes)."""


class VerificationError(Exception):
    """Base for all verification flow failures."""


class TokenInvalidError(VerificationError):
    """Token missing, wrong shape, or failed signature check."""


class TokenExpiredError(VerificationError):
    """Token was valid at issuance but TTL elapsed."""


class ResendThrottledError(VerificationError):
    """User must wait for cooldown before requesting another link."""


class UserAlreadyVerifiedError(VerificationError):
    """Idempotent no-op: account already has verified email."""


class MailDispatchError(VerificationError):
    """Downstream mailer (SMTP or queue) could not send the message."""
