# Tink Finance Client

A Python client for the Tink Finance API that provides easy-to-use async methods for interacting with Tink's financial services with automatic token management.

## Installation

```bash
pip install tink-finance
```

## Quick Start

```python
import asyncio
from tink_finance import TinkClient

async def main():
    # Initialize client with environment variables
    client = TinkClient()
    
    # Create a user - token management is automatic!
    user = await client.create_user(
        market="ES",
        locale="es_ES",
        external_user_id="my_user_123"
    )
    print(f"Created user: {user.user_id}")

# Run the async function
asyncio.run(main())
```

## Environment Variables

The client uses the following environment variables:

- `TINK_CLIENT_ID`: Your Tink client ID
- `TINK_CLIENT_SECRET`: Your Tink client secret

## Configuration

You can also initialize the client with explicit credentials:

```python
client = TinkClient(
    client_id="your_client_id",
    client_secret="your_client_secret"
)
```

## Features

- ✅ **Automatic token management** - No manual token handling required
- ✅ **Token caching and refresh** - Optimized performance with automatic retry
- ✅ **Async HTTP client** using httpx
- ✅ **Type hints** throughout
- ✅ **Pydantic models** for request/response validation
- ✅ **Environment variable support**
- ✅ **Comprehensive error handling**
- ✅ **User management** - Create, read, and delete users

## User Management

The library provides simple user management with automatic token handling:

```python
# Create users with automatic token management
user1 = await client.create_user(market="ES", locale="es_ES")
user2 = await client.create_user(market="SE", locale="sv_SE")

# User operations (require user tokens from OAuth flow)
user_info = await client.get_user(user_token)
await client.delete_user(user_token)
```

## Development

To set up the development environment:

```bash
git clone <repository-url>
cd tink-finance
pip install -e ".[dev]"
```

## License

MIT License - see LICENSE file for details. 