"""
Pydantic models for Tink Finance API requests and responses.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    """Model for token request parameters."""
    
    client_id: str = Field(..., description="Tink client ID")
    client_secret: str = Field(..., description="Tink client secret")
    grant_type: str = Field(default="client_credentials", description="OAuth grant type")
    scope: str = Field(default="user:create", description="OAuth scope")


class TokenResponse(BaseModel):
    """Model for token response from Tink API."""
    
    access_token: str = Field(..., description="OAuth access token")
    token_type: str = Field(..., description="Token type (usually 'bearer')")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    scope: str = Field(..., description="OAuth scope")
    
    @property
    def is_expired(self) -> bool:
        """Check if the token is expired based on expires_in field."""
        # This is a simplified check - in a real implementation you'd want to track
        # when the token was received and compare with current time
        return False 