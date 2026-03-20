"""Custom exceptions for ticktickmd."""


class TickTickError(Exception):
    """Base exception for ticktickmd errors."""
    pass


class AuthError(TickTickError):
    """Authentication-related errors."""
    pass


class TokenExpiredError(AuthError):
    """Token has expired and cannot be refreshed."""
    pass


class APIError(TickTickError):
    """API request error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API error {status_code}: {message}")
