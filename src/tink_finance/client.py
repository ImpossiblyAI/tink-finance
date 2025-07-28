"""
Tink Finance API client implementation.
"""

import os
from typing import Optional, List
from datetime import datetime

import httpx
from dotenv import load_dotenv

from tink_finance.models import (
    TokenRequest, 
    TokenResponse, 
    Token,
    CreateUserRequest, 
    CreateUserResponse, 
    UserResponse,
    AuthorizationGrantRequest,
    AuthorizationGrantResponse,
    UserTokenRequest
)
from tink_finance.exceptions import TinkAPIError, TinkAuthenticationError

# Load environment variables
load_dotenv()


class TinkClient:
    """
    Async client for the Tink Finance API.
    
    Supports environment variable configuration and explicit credential overrides.
    Automatically manages tokens with caching and refresh.
    """
    
    BASE_URL = "https://api.tink.com/api/v1"
    TOKEN_ENDPOINT = "/oauth/token"
    AUTHORIZATION_GRANT_ENDPOINT = "/oauth/authorization-grant"
    USER_ENDPOINT = "/user"
    CREATE_USER_ENDPOINT = "/user/create"
    DELETE_USER_ENDPOINT = "/user/delete"
    
    # Token scopes for different operations
    USER_CREATION_SCOPES = ["authorization:grant", "user:create"]
    USER_READ_SCOPES = ["user:read"]
    USER_DELETE_SCOPES = ["user:delete"]
    
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
        
        self.http_client: httpx.AsyncClient = httpx.AsyncClient(timeout=self.timeout)
        
        # Internal token cache
        self._token_cache: Optional[Token] = None
        
    async def _get_access_token(self, scope: str) -> Token:
        """
        Get an OAuth access token from Tink API.
        
        Args:
            scope: OAuth scope for the token request.
            
        Returns:
            Token object containing the access token and metadata with validation capabilities.
            
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
        
        url = self.base_url + self.TOKEN_ENDPOINT
        
        try:
            response = await self.http_client.post(
                url,
                data=token_request.model_dump(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            response.raise_for_status()
            
            token_response = TokenResponse(**response.json())
            return Token.from_token_response(token_response)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TinkAuthenticationError("Invalid client credentials") from e
            else:
                raise TinkAPIError(f"API request failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e

    async def _get_valid_token(self, required_scopes: List[str]) -> Token:
        """
        Get a valid token with the required scopes, using cache if available.
        
        Args:
            required_scopes: List of required scopes for the operation
            
        Returns:
            Valid Token object with required scopes
        """
        # Check if we have a cached token that's valid and has required scopes
        if (self._token_cache and 
            not self._token_cache.is_expired and 
            self._token_cache.has_all_scopes(required_scopes)):
            return self._token_cache
        
        # Get new token with required scopes
        scope_string = ",".join(required_scopes)
        self._token_cache = await self._get_access_token(scope=scope_string)
        return self._token_cache

    async def create_user(
        self, 
        market: str = 'ES', 
        locale: str = 'es_ES', 
        external_user_id: Optional[str] = None
    ) -> CreateUserResponse:
        """
        Create a new user in Tink.
        
        Args:
            market: Market code (e.g., 'ES' for Spain, 'SE' for Sweden)
            locale: Locale code (e.g., 'es_ES' for Spanish, 'sv_SE' for Swedish)
            external_user_id: Optional external user ID for your own reference
            
        Returns:
            CreateUserResponse object containing the created user ID.
            
        Raises:
            TinkAuthenticationError: If authentication fails.
            TinkAPIError: If the API request fails for other reasons.
        """
        # Get valid token automatically
        token = await self._get_valid_token(self.USER_CREATION_SCOPES)
        
        create_request = CreateUserRequest(
            market=market,
            locale=locale,
            external_user_id=external_user_id
        )
        
        url = self.base_url + self.CREATE_USER_ENDPOINT
        
        try:
            response = await self.http_client.post(
                url,
                json=create_request.model_dump(exclude_none=True),
                headers={
                    "Authorization": f"{token.token_type.capitalize()} {token.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            response.raise_for_status()
            
            return CreateUserResponse(**response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token might be invalid, clear cache and retry once
                self._token_cache = None
                token = await self._get_valid_token(self.USER_CREATION_SCOPES)
                
                response = await self.http_client.post(
                    url,
                    json=create_request.model_dump(exclude_none=True),
                    headers={
                        "Authorization": f"{token.token_type.capitalize()} {token.access_token}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                return CreateUserResponse(**response.json())
            else:
                raise TinkAPIError(f"Create user failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e

    async def get_user(self, user_id: Optional[str] = None, external_user_id: Optional[str] = None) -> UserResponse:
        """
        Get the authenticated user's information.
        
        Args:
            user_id: The user ID to get information for (cannot be used with external_user_id)
            external_user_id: The external user ID to get information for (cannot be used with user_id)
            
        Returns:
            UserResponse object containing the user information.
            
        Raises:
            TinkAuthenticationError: If authentication fails.
            TinkAPIError: If the API request fails for other reasons.
            ValueError: If neither user_id nor external_user_id is provided, or both are provided.
        """
        if not user_id and not external_user_id:
            raise ValueError("Either user_id or external_user_id must be provided")
        if user_id and external_user_id:
            raise ValueError("Cannot specify both user_id and external_user_id")
        
        # Grant access and get user token internally
        grant_response = await self._grant_user_access_internal(
            user_id=user_id, 
            external_user_id=external_user_id,
            scopes=["user:read"]
        )
        user_token = await self._get_user_token_internal(grant_response.code)
        
        url = self.base_url + self.USER_ENDPOINT
        
        try:
            response = await self.http_client.get(
                url,
                headers={
                    "Authorization": f"{user_token.token_type.capitalize()} {user_token.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            response.raise_for_status()
            print(response.json())
            return UserResponse(**response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TinkAuthenticationError("Invalid user token") from e
            else:
                raise TinkAPIError(f"Get user failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e

    async def delete_user(self, user_id: Optional[str] = None, external_user_id: Optional[str] = None) -> None:
        """
        Delete the authenticated user and all associated data.
        
        Args:
            user_id: The user ID to delete (cannot be used with external_user_id)
            external_user_id: The external user ID to delete (cannot be used with user_id)
            
        Raises:
            TinkAuthenticationError: If authentication fails.
            TinkAPIError: If the API request fails for other reasons.
            ValueError: If neither user_id nor external_user_id is provided, or both are provided.
        """
        if not user_id and not external_user_id:
            raise ValueError("Either user_id or external_user_id must be provided")
        if user_id and external_user_id:
            raise ValueError("Cannot specify both user_id and external_user_id")
        
        # Grant access and get user token internally
        grant_response = await self._grant_user_access_internal(
            user_id=user_id,
            external_user_id=external_user_id,
            scopes=["user:delete"]
        )
        user_token = await self._get_user_token_internal(grant_response.code)
        
        url = self.base_url + self.DELETE_USER_ENDPOINT
        
        try:
            response = await self.http_client.post(
                url,
                headers={
                    "Authorization": f"{user_token.token_type.capitalize()} {user_token.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            response.raise_for_status()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TinkAuthenticationError("Invalid user token") from e
            else:
                raise TinkAPIError(f"Delete user failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e

    async def _grant_user_access_internal(
        self, 
        user_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        scopes: List[str] = None
    ) -> AuthorizationGrantResponse:
        """
        Internal method to grant access to a user with the requested scopes.
        
        Args:
            user_id: The user ID to grant access to (cannot be used with external_user_id)
            external_user_id: The external user ID to grant access to (cannot be used with user_id)
            scopes: List of scopes to grant
            
        Returns:
            AuthorizationGrantResponse object containing the authorization code.
        """
        if not user_id and not external_user_id:
            raise ValueError("Either user_id or external_user_id must be provided")
        if user_id and external_user_id:
            raise ValueError("Cannot specify both user_id and external_user_id")
        
        # Get valid token automatically
        token = await self._get_valid_token(self.USER_CREATION_SCOPES)
        
        grant_request = AuthorizationGrantRequest(
            user_id=user_id,
            external_user_id=external_user_id,
            scope=",".join(scopes)
        )
        
        url = self.base_url + self.AUTHORIZATION_GRANT_ENDPOINT
        
        try:
            response = await self.http_client.post(
                url,
                data=grant_request.model_dump(),
                headers={
                    "Authorization": f"{token.token_type.capitalize()} {token.access_token}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            response.raise_for_status()
            
            return AuthorizationGrantResponse(**response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token might be invalid, clear cache and retry once
                self._token_cache = None
                token = await self._get_valid_token(self.USER_CREATION_SCOPES)
                
                response = await self.http_client.post(
                    url,
                    data=grant_request.model_dump(),
                    headers={
                        "Authorization": f"{token.token_type.capitalize()} {token.access_token}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                )
                response.raise_for_status()
                return AuthorizationGrantResponse(**response.json())
            else:
                raise TinkAPIError(f"Grant user access failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e

    async def _get_user_token_internal(self, authorization_code: str) -> Token:
        """
        Internal method to get a user access token using an authorization code.
        
        Args:
            authorization_code: The authorization code from grant_user_access
            
        Returns:
            Token object containing the user access token.
        """
        token_request = UserTokenRequest(
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type="authorization_code",
            code=authorization_code
        )
        
        url = self.base_url + self.TOKEN_ENDPOINT
        
        try:
            response = await self.http_client.post(
                url,
                data=token_request.model_dump(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            response.raise_for_status()
            
            token_response = TokenResponse(**response.json())
            return Token.from_token_response(token_response)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TinkAuthenticationError("Invalid authorization code") from e
            else:
                raise TinkAPIError(f"API request failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e
    
    async def close(self):
        """Close the HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None 