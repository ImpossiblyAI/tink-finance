"""
Tink Finance Python Client

A Python client for the Tink Finance API that provides easy-to-use async methods
for interacting with Tink's financial services.
"""

from tink_finance.client import TinkClient
from tink_finance.models import (
    TokenResponse, 
    TokenRequest, 
    Token,
    CreateUserRequest,
    CreateUserResponse, 
    UserResponse,
    UserProfile,
    NotificationSettings,
    AuthorizationGrantRequest,
    AuthorizationGrantResponse,
    UserTokenRequest
)
from tink_finance.exceptions import TinkAPIError, TinkAuthenticationError, TinkRateLimitError, TinkValidationError

__version__ = "0.1.0"
__all__ = [
    "TinkClient", 
    "TokenResponse", 
    "TokenRequest",
    "Token",
    "CreateUserRequest",
    "CreateUserResponse", 
    "UserResponse",
    "UserProfile",
    "NotificationSettings",
    "AuthorizationGrantRequest",
    "AuthorizationGrantResponse",
    "UserTokenRequest",
    "TinkAPIError",
    "TinkAuthenticationError", 
    "TinkRateLimitError",
    "TinkValidationError"
] 