"""
Tink Finance API client implementation.
"""

import os
from typing import Optional
from urllib.parse import urljoin

import httpx
from dotenv import load_dotenv

from .models import TokenRequest, TokenResponse
from .exceptions import TinkAPIError, TinkAuthenticationError

# Load environment variables
load_dotenv()


class TinkClient:
    """
    Async client for the Tink Finance API.
    
    Supports environment variable configuration and explicit credential overrides.
    """
    
    BASE_URL = "https://api.tink.com/api/v1"
    TOKEN_ENDPOINT = "/oauth/token"
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the Tink client.
        
        Args:
            client_id: Tink client ID. If not provided, will use TINK_CLIENT_ID env var.
            client_secret: Tink client secret. If not provided, will use TINK_CLIENT_SECRET env var.
            base_url: Base URL for the Tink API. Defaults to production API.
            timeout: Request timeout in seconds.
        """
        self.client_id = client_id or os.getenv("TINK_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("TINK_CLIENT_SECRET")
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        
        if not self.client_id:
            raise ValueError("client_id must be provided or TINK_CLIENT_ID environment variable must be set")
        if not self.client_secret:
            raise ValueError("client_secret must be provided or TINK_CLIENT_SECRET environment variable must be set")
        
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self._http_client
    
    async def get_access_token(self, scope: str = "user:create") -> TokenResponse:
        """
        Get an OAuth access token from Tink API.
        
        Args:
            scope: OAuth scope for the token request.
            
        Returns:
            TokenResponse object containing the access token and metadata.
            
        Raises:
            TinkAuthenticationError: If authentication fails.
            TinkAPIError: If the API request fails for other reasons.
        """
        token_request = TokenRequest(
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type="client_credentials",
            scope=scope,
        )
        
        url = urljoin(self.base_url, self.TOKEN_ENDPOINT)
        
        try:
            response = await self.http_client.post(
                url,
                data=token_request.model_dump(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            response.raise_for_status()
            
            return TokenResponse(**response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TinkAuthenticationError("Invalid client credentials") from e
            else:
                raise TinkAPIError(f"API request failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None 