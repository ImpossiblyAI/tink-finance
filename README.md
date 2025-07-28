# Tink Finance Python Client

A Python client for the Tink Finance API, providing easy access to financial data and user management capabilities.

## Features

- **User Management**: Create, read, and delete users
- **Transaction Data**: Get transactions using authorization codes
- **Account Data**: Get account information and balances
- **OAuth Integration**: Automatic token management with caching and refresh
- **Type Safety**: Full type hints and Pydantic models
- **Async Support**: Built on httpx for modern async/await patterns

## Installation

```bash
pip install tink-finance
```

## Quick Start

### Basic Setup

```python
import asyncio
from tink_finance.client import TinkClient

async def main():
    # Initialize client with environment variables
    client = TinkClient()
    
    # Your code here...
    
    await client.close()

asyncio.run(main())
```

### Environment Variables

Set these environment variables or pass them directly to the client:

```bash
export TINK_CLIENT_ID="your_client_id"
export TINK_CLIENT_SECRET="your_client_secret"
```

## Usage Examples

### User Management

```python
# Create a user
user_response = await client.create_user(
    market="ES",
    locale="es_ES",
    external_user_id="user_123"
)
print(f"Created user: {user_response.user_id}")

# Get user information
user = await client.get_user(external_user_id="user_123")
print(f"User: {user.id}")

# Delete user
await client.delete_user(external_user_id="user_123")
```

### Callback Handling

The library provides comprehensive callback parsing for Tink Link responses:

```python
from tink_finance.callback import parse_tink_callback, is_user_cancelled

# Parse callback parameters from FastAPI request
query_params = {
    "code": "auth_code_123",
    "credentials_id": "cred_456",
    "state": "user_session"
}

result = parse_tink_callback(query_params)

if result.is_success:
    print(f"Success! Code: {result.success.code}")
    print(f"Credentials ID: {result.success.credentials_id}")
elif result.is_user_cancelled:
    print("User cancelled the flow (not an error)")
else:
    print(f"Error: {result.error.error} - {result.error.error_reason}")
    print(f"Message: {result.error.message}")
    print(f"Tracking ID: {result.error.tracking_id}")
```

#### FastAPI Integration

```python
from fastapi import FastAPI, Request
from tink_finance.callback import parse_tink_callback_from_request

app = FastAPI()

@app.get("/tink/callback")
async def handle_callback(request: Request):
    # Parse the callback directly from the request
    # This automatically extracts all query parameters, making it future-proof
    result = parse_tink_callback(dict(request.query_params))
    
    if result.is_success:
        # Handle success
        return {"status": "success", "code": result.success.code}
    elif result.is_user_cancelled:
        # Handle user cancellation
        return {"status": "cancelled"}
    else:
        # Handle error
        return {
            "status": "error",
            "error": result.error.error,
            "message": result.error.message
        }
```

**Framework-Agnostic Design**: The `parse_tink_callback_from_request()` function works with any request object that has a `query_params` attribute, making it compatible with FastAPI, Flask, Django, or any other web framework.

#### Framework Examples

**FastAPI:**
```python
from fastapi import Request
from tink_finance.callback import parse_tink_callback_from_request

@app.get("/tink/callback")
async def handle_callback(request: Request):
    result = parse_tink_callback_from_request(request)
    # Handle result...
```

**Flask:**
```python
from flask import request
from tink_finance.callback import parse_tink_callback_from_request

@app.route("/tink/callback")
def handle_callback():
    result = parse_tink_callback_from_request(request)
    # Handle result...
```

**Django:**
```python
from django.http import HttpRequest
from tink_finance.callback import parse_tink_callback_from_request

def handle_callback(request: HttpRequest):
    result = parse_tink_callback_from_request(request)
    # Handle result...
```

**Manual (any framework):**
```python
from tink_finance.callback import parse_tink_callback

# Extract query parameters manually
query_params = dict(request.query_params)  # or request.args, request.GET, etc.
result = parse_tink_callback(query_params)
```

### Transaction Data Flow

The transaction flow involves three main steps:

1. **Generate Connection URL**: Create a URL for your frontend
2. **Handle Authorization Code**: Receive the code from Tink Link callback
3. **Get Data**: Use the code to fetch transactions and accounts

#### Step 1: Generate Connection URL

```python
# Generate a URL for your frontend
connection_url = client.get_connection_url(
    redirect_uri="https://your-app.com/tink/callback",
    market="ES",
    locale="en_US",
    state="user_session_123"
)
print(f"Frontend URL: {connection_url}")
```

#### Step 2: Handle Authorization Code

Your frontend will redirect users to the connection URL. After the user completes the flow, Tink will redirect back to your callback URL with an authorization code.

#### Step 3: Get Transactions and Accounts

```python
# Get transactions using the authorization code
transactions = await client.get_transactions_with_code(
    authorization_code="auth_code_from_callback",
    page_size=50,
    booked_date_gte="2024-01-01",
    booked_date_lte="2024-01-31"
)

print(f"Found {len(transactions.transactions)} transactions")

# Get accounts using the same authorization code
accounts = await client.get_accounts_with_code(
    authorization_code="auth_code_from_callback"
)

print(f"Found {len(accounts.accounts)} accounts")
```

### Transaction Filtering

```python
# Filter transactions by account
filtered_transactions = await client.get_transactions_with_code(
    authorization_code="auth_code_from_callback",
    account_id_in=["account_1", "account_2"],
    status_in=["BOOKED", "PENDING"],
    page_size=100
)

# Filter by date range
recent_transactions = await client.get_transactions_with_code(
    authorization_code="auth_code_from_callback",
    booked_date_gte="2024-01-01",
    booked_date_lte="2024-01-31"
)
```

### Pagination

```python
# Get first page
response = await client.get_transactions_with_code(
    authorization_code="auth_code_from_callback",
    page_size=50
)

# Get next page if available
if response.nextPageToken:
    next_page = await client.get_transactions_with_code(
        authorization_code="auth_code_from_callback",
        page_size=50,
        page_token=response.nextPageToken
    )
```

## API Reference

### TinkClient

#### Constructor

```python
TinkClient(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 30.0
)
```

#### Methods

##### User Management

- `create_user(market: str, locale: str, external_user_id: Optional[str] = None) -> CreateUserResponse`
- `get_user(user_id: Optional[str] = None, external_user_id: Optional[str] = None) -> UserResponse`
- `delete_user(user_id: Optional[str] = None, external_user_id: Optional[str] = None) -> None`

##### Transaction Data

- `get_transactions_with_code(authorization_code: str, **filters) -> TransactionsResponse`
- `get_accounts_with_code(authorization_code: str) -> AccountsResponse`

##### URL Generation

- `get_connection_url(redirect_uri: str, market: str = "ES", locale: str = "en_US", state: Optional[str] = None, authorization_code: Optional[str] = None) -> str`

### Callback Parsing

The library provides utilities for parsing Tink Link callbacks:

#### Functions

- `parse_tink_callback(query_params: Dict[str, Any]) -> TinkCallbackResult`
- `parse_tink_callback_url(callback_url: str) -> TinkCallbackResult`
- `is_user_cancelled(result: TinkCallbackResult) -> bool`
- `get_error_category(result: TinkCallbackResult) -> Optional[str]`
- `get_error_reason(result: TinkCallbackResult) -> Optional[str]`
- `get_user_message(result: TinkCallbackResult) -> Optional[str]`
- `get_tracking_id(result: TinkCallbackResult) -> Optional[str]`

#### Models

- `TinkCallbackSuccess` - Success response with code and credentials_id
- `TinkCallbackError` - Error response with detailed error information
- `TinkCallbackResult` - Union type containing either success or error

### Transaction Filters

The `get_transactions_with_code` method supports these optional filters:

- `account_id_in: List[str]` - Filter by account IDs
- `status_in: List[str]` - Filter by transaction status
- `page_size: int` - Number of transactions per page (max 100)
- `page_token: str` - Token for pagination
- `booked_date_gte: str` - Start date (YYYY-MM-DD format)
- `booked_date_lte: str` - End date (YYYY-MM-DD format)

## Error Handling

The client raises specific exceptions for different error types:

```python
from tink_finance.exceptions import TinkAPIError, TinkAuthenticationError

try:
    transactions = await client.get_transactions_with_code("auth_code")
except TinkAuthenticationError as e:
    print(f"Authentication failed: {e}")
except TinkAPIError as e:
    print(f"API error: {e}")
```

## Examples

See the `examples/` directory for complete working examples:

- `transaction_example.py` - Complete transaction flow demonstration
- `user_management_example.py` - User management examples

## Development

### Running Examples

```bash
# Set environment variables
export TINK_CLIENT_ID="your_client_id"
export TINK_CLIENT_SECRET="your_client_secret"

# Run transaction example
python examples/transaction_example.py
```

### Testing

```bash
pytest tests/
```

## License

MIT License - see LICENSE file for details. 