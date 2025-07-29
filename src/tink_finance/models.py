"""
Pydantic models for Tink Finance API requests and responses.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Set, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator, ValidationInfo


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Token creation timestamp")
    
    @field_validator('scope')
    def parse_scope(cls, v: str) -> str:
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
        return self.expires_at - datetime.now(timezone.utc)
    
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


class PeriodSettings(BaseModel):
    """Model for user period settings."""
    
    mode: str = Field(..., description="Period mode")
    adjustedPeriodDay: int = Field(..., description="Adjusted period day")


class UserProfile(BaseModel):
    """Model for user profile information."""
    
    currency: str = Field(..., description="User's currency")
    locale: str = Field(..., description="User's locale")
    market: str = Field(..., description="User's market")
    notificationSettings: NotificationSettings = Field(..., description="User notification settings")
    periodAdjustedDay: Optional[int] = Field(None, description="Period adjusted day")
    periodMode: Optional[str] = Field(None, description="Period mode")
    timeZone: str = Field(..., description="User's timezone")
    periodSettings: PeriodSettings = Field(..., description="User period settings")


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
    
    @field_validator('created', mode='before')
    def convert_created_timestamp(cls, v: Union[int, str]) -> str:
        """Convert integer timestamp to string if needed."""
        if isinstance(v, int):
            # Convert milliseconds to seconds and then to datetime string
            dt = datetime.fromtimestamp(v / 1000, tz=timezone.utc)
            return dt.isoformat()
        return v


class CreateUserRequest(BaseModel):
    """Model for user creation request."""
    
    market: str = Field(..., description="Market code (e.g., 'SE')")
    locale: str = Field(..., description="Locale code (e.g., 'sv_SE')")
    external_user_id: Optional[str] = Field(None, description="External user ID")


class CreateUserResponse(BaseModel):
    """Model for user creation response."""
    
    user_id: str = Field(..., description="Created user ID")


class AuthorizationGrantRequest(BaseModel):
    """Request model for authorization grant."""
    user_id: Optional[str] = Field(None, description="User ID (cannot be used with external_user_id)")
    external_user_id: Optional[str] = Field(None, description="External user ID (cannot be used with user_id)")
    scope: str = Field(..., description="Scope of access")
    
    @field_validator('user_id', 'external_user_id')
    def validate_user_identifier(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if info.field_name == 'user_id' and v is not None:
            # Check if external_user_id is also set
            if hasattr(info.data, 'external_user_id') and info.data.external_user_id is not None:
                raise ValueError("Cannot specify both user_id and external_user_id")
        elif info.field_name == 'external_user_id' and v is not None:
            # Check if user_id is also set
            if hasattr(info.data, 'user_id') and info.data.user_id is not None:
                raise ValueError("Cannot specify both user_id and external_user_id")
        return v
    
    @field_validator('scope')
    def validate_scope(cls, v: str) -> str:
        if not v:
            raise ValueError("Scope cannot be empty")
        return v


class AuthorizationGrantResponse(BaseModel):
    """Model for authorization grant response."""
    
    code: str = Field(..., description="User authorization code")


class UserTokenRequest(BaseModel):
    """Model for user token request."""
    
    client_id: str = Field(..., description="Tink client ID")
    client_secret: str = Field(..., description="Tink client secret")
    grant_type: str = Field(default="authorization_code", description="OAuth grant type")
    code: str = Field(..., description="User authorization code")


class AuthorizationCodeTokenRequest(BaseModel):
    """Model for authorization code token request (one-time use)."""
    
    client_id: str = Field(..., description="Tink client ID")
    client_secret: str = Field(..., description="Tink client secret")
    grant_type: str = Field(default="authorization_code", description="OAuth grant type")
    code: str = Field(..., description="Authorization code from Tink Link")


# Tink Callback Models
class TinkCallbackSuccess(BaseModel):
    """Model for successful Tink callback response."""
    
    code: str = Field(..., description="Authorization code for getting user token")
    credentials_id: str = Field(..., description="Identifier of the created credentials")
    state: Optional[str] = Field(None, description="State parameter if provided in request")


class TinkCallbackError(BaseModel):
    """Model for Tink callback error response."""
    
    error: str = Field(..., description="Error status/category")
    error_reason: str = Field(..., description="Specific cause of the error")
    message: str = Field(..., description="Localized user-facing error message")
    tracking_id: str = Field(..., description="Tink's internal identifier for this error")
    credentials: Optional[str] = Field(None, description="Credentials ID if credentials were created")
    error_type: Optional[str] = Field(None, description="Authentication error type (if error=AUTHENTICATION_ERROR)")
    provider_name: Optional[str] = Field(None, description="Selected bank connection name")
    payment_request_id: Optional[str] = Field(None, description="Payment request ID if using Payment Initiation")
    state: Optional[str] = Field(None, description="State parameter if provided in request")


class TinkCallbackResult(BaseModel):
    """Union type for Tink callback results."""
    
    success: Optional[TinkCallbackSuccess] = Field(None, description="Success response")
    error: Optional[TinkCallbackError] = Field(None, description="Error response")
    is_success: bool = Field(..., description="Whether the callback was successful")
    is_user_cancelled: bool = Field(..., description="Whether the user cancelled the flow")
    
    @classmethod
    def from_success(cls, success: TinkCallbackSuccess) -> 'TinkCallbackResult':
        """Create a success result."""
        return cls(
            success=success,
            error=None,
            is_success=True,
            is_user_cancelled=False
        )
    
    @classmethod
    def from_error(cls, error: TinkCallbackError) -> 'TinkCallbackResult':
        """Create an error result."""
        return cls(
            success=None,
            error=error,
            is_success=False,
            is_user_cancelled=error.error == "USER_CANCELLED"
        )


# Updated models to match actual Tink API response structure
class AmountValue(BaseModel):
    """Model for amount value structure."""
    
    unscaledValue: str = Field(..., description="Unscaled value as string")
    scale: str = Field(..., description="Scale as string")


class Amount(BaseModel):
    """Model for amount structure."""
    
    value: AmountValue = Field(..., description="Amount value")
    currencyCode: str = Field(..., description="Currency code")


class Descriptions(BaseModel):
    """Model for transaction descriptions."""
    
    original: str = Field(..., description="Original description")
    display: str = Field(..., description="Display description")


class Dates(BaseModel):
    """Model for transaction dates."""
    
    booked: str = Field(..., description="Booked date")


class Identifiers(BaseModel):
    """Model for transaction identifiers."""
    
    providerTransactionId: str = Field(..., description="Provider transaction ID")


class Types(BaseModel):
    """Model for transaction types."""
    
    type: str = Field(..., description="Transaction type")


class Transaction(BaseModel):
    """Model for a single transaction matching actual Tink API response."""
    
    id: str = Field(..., description="Transaction ID")
    accountId: str = Field(..., description="Account ID")
    amount: Amount = Field(..., description="Transaction amount")
    descriptions: Descriptions = Field(..., description="Transaction descriptions")
    dates: Dates = Field(..., description="Transaction dates")
    identifiers: Identifiers = Field(..., description="Transaction identifiers")
    types: Types = Field(..., description="Transaction types")
    status: str = Field(..., description="Transaction status")
    providerMutability: str = Field(..., description="Provider mutability")


class TransactionsResponse(BaseModel):
    """Model for transactions response."""
    
    transactions: List[Transaction] = Field(..., description="List of transactions")
    nextPageToken: Optional[str] = Field(None, description="Token for next page")


class Account(BaseModel):
    """Model for a single account matching actual Tink API response."""
    
    id: str = Field(..., description="Account ID")
    name: str = Field(..., description="Account name")
    type: str = Field(..., description="Account type")
    balances: Dict[str, Any] = Field(..., description="Account balances")
    identifiers: Dict[str, Any] = Field(..., description="Account identifiers")
    dates: Dict[str, str] = Field(..., description="Account dates")
    financialInstitutionId: str = Field(..., description="Financial institution ID")
    customerSegment: str = Field(..., description="Customer segment")


class AccountsResponse(BaseModel):
    """Model for accounts response."""
    
    accounts: List[Account] = Field(..., description="List of accounts")
    totalCount: Optional[int] = Field(None, description="Total number of accounts")
    nextPageToken: Optional[str] = Field(None, description="Token for next page") 