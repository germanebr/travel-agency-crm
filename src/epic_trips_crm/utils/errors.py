class NotFoundError(Exception):
    """Raised when an expected DB record does not exist."""


class ConflictError(Exception):
    """Raised when an operation violates a uniqueness or business constraint."""
