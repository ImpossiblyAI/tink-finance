"""
Custom exceptions for the Tink Finance client.
"""


class TinkAPIError(Exception):
    """Base exception for Tink API errors."""
    pass


class TinkAuthenticationError(TinkAPIError):
    """Exception raised when authentication fails."""
    pass


class TinkCallbackError(TinkAPIError):
    """Exception raised when callback parsing fails."""
    pass


class TinkRateLimitError(TinkAPIError):
    """Exception raised when rate limit is exceeded."""
    pass


class TinkValidationError(TinkAPIError):
    """Exception raised when request validation fails."""
    pass 