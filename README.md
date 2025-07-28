# Tink Finance Client

A Python client for the Tink Finance API that provides easy-to-use async methods for interacting with Tink's financial services.

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
    
    # Get access token
    token_response = await client.get_access_token()
    print(f"Access token: {token_response.access_token}")

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

- ✅ Async HTTP client using httpx
- ✅ Type hints throughout
- ✅ Pydantic models for request/response validation
- ✅ Environment variable support
- ✅ Comprehensive error handling

## Development

To set up the development environment:

```bash
git clone <repository-url>
cd tink-finance
pip install -e ".[dev]"
```

## License

MIT License - see LICENSE file for details. 