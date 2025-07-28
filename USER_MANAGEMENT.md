# Tink Finance User Management

This document describes the user management functionality added to the Tink Finance Python client.

## Overview

The user management functionality allows you to:
- Create new users in Tink with automatic token management
- Retrieve user information (requires user tokens from OAuth flow)
- Delete users and their associated data (requires user tokens from OAuth flow)
- Benefit from automatic token caching and refresh

## Simplified API

The library now handles token management internally, making the API much simpler to use:

### Automatic Token Management

- **No manual token handling**: Tokens are automatically obtained and cached
- **Automatic refresh**: Expired tokens are automatically refreshed
- **Scope management**: Required scopes are handled internally
- **Retry logic**: Automatic retry on token expiration (401 errors)

### User Creation (Simplified)

```python
from tink_finance import TinkClient

client = TinkClient()

# Create users with automatic token management
user1 = await client.create_user(
    market="SE",
    locale="sv_SE",
    external_user_id="my_user_123"
)

user2 = await client.create_user(
    market="NO", 
    locale="nb_NO",
    external_user_id="my_user_456"
)

print(f"Created users: {user1.user_id}, {user2.user_id}")
```

**Benefits:**
- No token management required
- Automatic caching and reuse
- Proper scope handling
- Automatic retry on failures

## Authentication

The library handles two types of authentication:

1. **Client Authentication** (automatic): Used for user creation operations
2. **User Authentication** (OAuth flow): Required for user-specific operations

## API Methods

### Create User

Creates a new user in Tink with automatic token management.

```python
from tink_finance import TinkClient

client = TinkClient()

# Create user - token management is automatic
user_response = await client.create_user(
    market="SE",           # Market code (e.g., 'SE' for Sweden)
    locale="sv_SE",        # Locale code (e.g., 'sv_SE' for Swedish)
    external_user_id="my_user_123"  # Optional: Your own user ID
)

print(f"Created user: {user_response.user_id}")
```

**Parameters:**
- `market` (str): Market code (e.g., 'SE', 'NO', 'DK')
- `locale` (str): Locale code (e.g., 'sv_SE', 'en_US')
- `external_user_id` (Optional[str]): Your own user identifier

**Returns:** `CreateUserResponse` with the created user ID.

**Features:**
- Automatic token acquisition and caching
- Automatic retry on token expiration
- No manual token management required

### Get User

Retrieves information about the authenticated user.

```python
# Requires a user token with 'user:read' scope from OAuth flow
user_info = await client.get_user(user_token)

print(f"User ID: {user_info.id}")
print(f"External User ID: {user_info.externalUserId}")
print(f"Market: {user_info.profile.market}")
print(f"Locale: {user_info.profile.locale}")
print(f"Currency: {user_info.profile.currency}")
```

**Parameters:**
- `user_token` (Token): User token with 'user:read' scope (obtained through OAuth flow)

**Returns:** `UserResponse` with complete user information including:
- Basic user info (ID, creation date, external ID)
- Profile information (market, locale, currency, timezone)
- Notification settings
- User flags and metadata

### Delete User

Deletes the authenticated user and all associated data.

```python
# Requires a user token with 'user:delete' scope from OAuth flow
await client.delete_user(user_token)
print("User deleted successfully")
```

**Parameters:**
- `user_token` (Token): User token with 'user:delete' scope (obtained through OAuth flow)

**Returns:** None (raises exception on failure)

## Token Management

### Internal Token Caching

The library automatically manages client tokens:

```python
client = TinkClient()

# First operation - gets new token
user1 = await client.create_user(market="SE", locale="sv_SE")

# Second operation - reuses cached token
user2 = await client.create_user(market="NO", locale="nb_NO")

# Third operation - still reuses cached token
user3 = await client.create_user(market="DK", locale="da_DK")
```

### Automatic Retry Logic

The library handles token expiration automatically:

```python
# If a token expires during an operation, the library will:
# 1. Detect the 401 error
# 2. Clear the cached token
# 3. Get a new token automatically
# 4. Retry the operation
# 5. Return the result

user = await client.create_user(market="SE", locale="sv_SE")
# This works even if the cached token expires during the request
```

## Data Models

### CreateUserRequest

```python
class CreateUserRequest(BaseModel):
    market: str                    # Market code (e.g., 'SE')
    locale: str                    # Locale code (e.g., 'sv_SE')
    externalUserId: Optional[str]  # External user ID
```

### CreateUserResponse

```python
class CreateUserResponse(BaseModel):
    user_id: str                   # Created user ID
```

### UserResponse

```python
class UserResponse(BaseModel):
    appId: str                     # Application ID
    created: str                   # Creation timestamp
    externalUserId: Optional[str]  # External user ID
    flags: List[str]               # User flags
    id: str                        # Tink user ID
    nationalId: Optional[str]      # National ID
    profile: UserProfile           # User profile
    username: Optional[str]        # Username
```

### UserProfile

```python
class UserProfile(BaseModel):
    currency: str                  # User's currency
    locale: str                    # User's locale
    market: str                    # User's market
    notificationSettings: NotificationSettings  # Notification settings
    periodAdjustedDay: Optional[int]  # Period adjusted day
    periodMode: Optional[str]      # Period mode
    timeZone: str                  # User's timezone
```

### NotificationSettings

```python
class NotificationSettings(BaseModel):
    balance: bool                  # Balance notifications
    budget: bool                   # Budget notifications
    doubleCharge: bool             # Double charge notifications
    einvoices: bool                # E-invoice notifications
    fraud: bool                    # Fraud notifications
    income: bool                   # Income notifications
    largeExpense: bool             # Large expense notifications
    leftToSpend: bool              # Left to spend notifications
    loanUpdate: bool               # Loan update notifications
    summaryMonthly: bool           # Monthly summary notifications
    summaryWeekly: bool            # Weekly summary notifications
    transaction: bool              # Transaction notifications
    unusualAccount: bool           # Unusual account notifications
    unusualCategory: bool          # Unusual category notifications
```

## Error Handling

The client raises specific exceptions for different error scenarios:

```python
from tink_finance import TinkAPIError, TinkAuthenticationError

try:
    user_response = await client.create_user(market="SE", locale="sv_SE")
except TinkAuthenticationError as e:
    print(f"Authentication failed: {e}")
except TinkAPIError as e:
    print(f"API request failed: {e}")
```

## Complete Example

```python
import asyncio
from tink_finance import TinkClient

async def user_management_example():
    client = TinkClient()
    
    try:
        # Create multiple users with automatic token management
        users = []
        
        # First user - gets new token
        user1 = await client.create_user(
            market="SE",
            locale="sv_SE",
            external_user_id="example_user_1"
        )
        users.append(user1)
        
        # Second user - reuses cached token
        user2 = await client.create_user(
            market="NO",
            locale="nb_NO",
            external_user_id="example_user_2"
        )
        users.append(user2)
        
        # Third user - still reuses cached token
        user3 = await client.create_user(
            market="DK",
            locale="da_DK",
            external_user_id="example_user_3"
        )
        users.append(user3)
        
        print(f"Created {len(users)} users successfully")
        
        # In a real application, you would:
        # - Redirect users to Tink OAuth for authentication
        # - Get user tokens with appropriate scopes
        # - Use user tokens for user-specific operations
        
        # Example of getting user info (requires user token):
        # user_info = await client.get_user(user_token)
        
        # Example of deleting user (requires user token):
        # await client.delete_user(user_token)
        
    finally:
        await client.close()

# Run the example
asyncio.run(user_management_example())
```

## Token Best Practices

1. **No manual management**: The library handles all client token management
2. **User tokens**: Only user tokens from OAuth flow need manual handling
3. **Automatic refresh**: Client tokens are automatically refreshed when needed
4. **Error handling**: The library handles token expiration gracefully
5. **Caching**: Tokens are cached to reduce API calls

## Important Notes

1. **User Tokens**: Operations like `get_user()` and `delete_user()` require user tokens obtained through Tink's OAuth flow, not client tokens.

2. **External User ID**: The `external_user_id` parameter allows you to associate your own user identifier with Tink users for easier reference.

3. **Scopes**: Different operations require different OAuth scopes:
   - User creation: `authorization:grant,user:create` (handled automatically)
   - User reading: `user:read` (requires user token)
   - User deletion: `user:delete` (requires user token)

4. **Permanent Deletion**: The `delete_user()` method permanently deletes the user and all associated data. Use with caution.

5. **Environment Variables**: Make sure to set `TINK_CLIENT_ID` and `TINK_CLIENT_SECRET` environment variables or pass them to the client constructor.

6. **Automatic Retry**: The library automatically retries operations on token expiration (401 errors).

7. **Token Caching**: Client tokens are cached to improve performance and reduce API calls. 