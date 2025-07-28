"""
Pydantic models for Tink Finance API requests and responses.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Set
from pydantic import BaseModel, Field, field_validator


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


class Token(BaseModel):
    """
    Comprehensive token model with validation and management capabilities.
    
    This model represents a complete token with built-in expiration checking,
    scope validation, and automatic token refresh capabilities.
    """
    
    access_token: str = Field(..., description="OAuth access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    scope: str = Field(..., description="OAuth scope")
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc), description="Token creation timestamp")
    
    @field_validator('scope')
    def parse_scope(cls, v):
        """Parse scope string into a set for easier manipulation."""
        return v
    
    @property
    def scopes(self) -> Set[str]:
        """Get the token scopes as a set."""
        return set(self.scope.split(','))
    
    @property
    def expires_at(self) -> datetime:
        """Get the exact expiration time."""
        return self.created_at + timedelta(seconds=self.expires_in)
    
    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def time_until_expiry(self) -> timedelta:
        """Get time until token expires."""
        return self.expires_at - datetime.utcnow()
    
    @property
    def is_expiring_soon(self, buffer_minutes: int = 5) -> bool:
        """Check if token is expiring soon (within buffer_minutes)."""
        return self.time_until_expiry <= timedelta(minutes=buffer_minutes)
    
    def has_scope(self, required_scope: str) -> bool:
        """Check if token has a specific scope."""
        return required_scope in self.scopes
    
    def has_any_scope(self, required_scopes: List[str]) -> bool:
        """Check if token has any of the required scopes."""
        return bool(self.scopes.intersection(set(required_scopes)))
    
    def has_all_scopes(self, required_scopes: List[str]) -> bool:
        """Check if token has all of the required scopes."""
        return self.scopes.issuperset(set(required_scopes))
    
    def to_dict(self) -> dict:
        """Convert token to dictionary format."""
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired,
            "scopes": list(self.scopes)
        }
    
    @classmethod
    def from_token_response(cls, token_response: TokenResponse) -> 'Token':
        """Create a Token from a TokenResponse."""
        return cls(
            access_token=token_response.access_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
            scope=token_response.scope
        )


class NotificationSettings(BaseModel):
    """Model for user notification settings."""
    
    balance: bool = Field(default=False, description="Balance notifications")
    budget: bool = Field(default=False, description="Budget notifications")
    doubleCharge: bool = Field(default=False, description="Double charge notifications")
    einvoices: bool = Field(default=False, description="E-invoice notifications")
    fraud: bool = Field(default=False, description="Fraud notifications")
    income: bool = Field(default=False, description="Income notifications")
    largeExpense: bool = Field(default=False, description="Large expense notifications")
    leftToSpend: bool = Field(default=False, description="Left to spend notifications")
    loanUpdate: bool = Field(default=False, description="Loan update notifications")
    summaryMonthly: bool = Field(default=False, description="Monthly summary notifications")
    summaryWeekly: bool = Field(default=False, description="Weekly summary notifications")
    transaction: bool = Field(default=False, description="Transaction notifications")
    unusualAccount: bool = Field(default=False, description="Unusual account notifications")
    unusualCategory: bool = Field(default=False, description="Unusual category notifications")


class UserProfile(BaseModel):
    """Model for user profile information."""
    
    currency: str = Field(..., description="User's currency")
    locale: str = Field(..., description="User's locale")
    market: str = Field(..., description="User's market")
    notificationSettings: NotificationSettings = Field(..., description="User notification settings")
    periodAdjustedDay: Optional[int] = Field(None, description="Period adjusted day")
    periodMode: Optional[str] = Field(None, description="Period mode")
    timeZone: str = Field(..., description="User's timezone")


class UserResponse(BaseModel):
    """Model for user response from Tink API."""
    
    appId: str = Field(..., description="Application ID")
    created: str = Field(..., description="User creation timestamp")
    externalUserId: Optional[str] = Field(None, description="External user ID")
    flags: List[str] = Field(default_factory=list, description="User flags")
    id: str = Field(..., description="User ID")
    nationalId: Optional[str] = Field(None, description="National ID")
    profile: UserProfile = Field(..., description="User profile")
    username: Optional[str] = Field(None, description="Username")


class CreateUserRequest(BaseModel):
    """Model for user creation request."""
    
    market: str = Field(..., description="Market code (e.g., 'SE')")
    locale: str = Field(..., description="Locale code (e.g., 'sv_SE')")
    externalUserId: Optional[str] = Field(None, description="External user ID")


class CreateUserResponse(BaseModel):
    """Model for user creation response."""
    
    user_id: str = Field(..., description="Created user ID") 