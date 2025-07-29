"""
Tink Finance API client implementation.
"""

import os
from typing import Optional, List, Dict, Any
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
    UserTokenRequest,
    AuthorizationCodeTokenRequest,
    TransactionsResponse,
    AccountsResponse
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
    
    # Data API endpoints
    DATA_BASE_URL = "https://api.tink.com/data/v2"
    TRANSACTIONS_ENDPOINT = "/transactions"
    ACCOUNTS_ENDPOINT = "/accounts"
    
    # Token scopes for different operations
    USER_CREATION_SCOPES = ["authorization:grant", "user:create"]
    USER_READ_SCOPES = ["user:read"]
    USER_DELETE_SCOPES = ["user:delete"]
    USER_DATA_SCOPES = ["accounts:read", "transactions:read"]
    
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
        local_client_id = client_id or os.getenv("TINK_CLIENT_ID")
        local_client_secret = client_secret or os.getenv("TINK_CLIENT_SECRET")
        if not local_client_id:
            raise ValueError("client_id must be provided or TINK_CLIENT_ID environment variable must be set")
        if not local_client_secret:
            raise ValueError("client_secret must be provided or TINK_CLIENT_SECRET environment variable must be set")
        
        self.client_id = local_client_id
        self.client_secret = local_client_secret
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
                
        self.http_client: httpx.AsyncClient = httpx.AsyncClient(timeout=self.timeout)
        
        # Internal token cache for application-level tokens
        self._token_cache: Optional[Token] = None
        
        # User token cache: maps user identifier to Token
        self._user_token_cache: Dict[str, Token] = {}

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
        scopes: List[str],
        user_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
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
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self.http_client:
            await self.http_client.aclose()            

    def get_connection_url(
        self,
        redirect_uri: str,
        market: str = "ES",
        locale: str = "en_US",
        state: Optional[str] = None,
        authorization_code: Optional[str] = None
    ) -> str:
        """
        Generate a Tink connection URL for account linking.
        
        Args:
            redirect_uri: The URL where users will be redirected after completing the flow
            market: Market code (e.g., 'ES' for Spain, 'SE' for Sweden)
            locale: Locale code (e.g., 'en_US' for English, 'es_ES' for Spanish)
            state: Optional state parameter that will be provided to the callback
            authorization_code: Optional authorization code for continuous access
            
        Returns:
            Complete Tink connection URL with all required parameters.
            
        Example:
            >>> client.get_connection_url(
            ...     redirect_uri="https://example.com/tink/callback",
            ...     market="ES",
            ...     locale="en_US"
            ... )
            'https://link.tink.com/1.0/transactions/connect-accounts/?client_id=...&redirect_uri=...&market=ES&locale=en_US'
            
            >>> client.get_connection_url(
            ...     redirect_uri="https://example.com/tink/callback",
            ...     state="user_session_123",
            ...     authorization_code="auth_code_456"
            ... )
            'https://link.tink.com/1.0/transactions/connect-accounts/?client_id=...&redirect_uri=...&market=ES&locale=en_US&state=user_session_123&authorization_code=auth_code_456'
        """
        from urllib.parse import quote
        
        base_url = "https://link.tink.com/1.0/transactions/connect-accounts/"
        
        # Build query parameters
        params = {
            "client_id": self.client_id,
            "redirect_uri": quote(redirect_uri, safe=""),
            "market": market,
            "locale": locale
        }
        
        # Add optional parameters if provided
        if state is not None:
            params["state"] = state
        if authorization_code is not None:
            params["authorization_code"] = authorization_code
        
        # Construct query string
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        
        return f"{base_url}?{query_string}"

    def _get_user_cache_key(self, user_id: Optional[str] = None, external_user_id: Optional[str] = None, authorization_code: Optional[str] = None) -> str:
        """
        Generate a cache key for user tokens.
        
        Args:
            user_id: User ID
            external_user_id: External user ID
            authorization_code: Authorization code (used when no user identification available)
            
        Returns:
            Cache key string
        """
        if user_id:
            return f"user:{user_id}"
        elif external_user_id:
            return f"external_user:{external_user_id}"
        elif authorization_code:
            return f"auth_code:{authorization_code}"
        else:
            raise ValueError("Either user_id, external_user_id, or authorization_code must be provided")
    
    def _cache_user_token(self, token: Token, user_id: Optional[str] = None, external_user_id: Optional[str] = None, authorization_code: Optional[str] = None) -> None:
        """
        Cache a user token.
        
        Args:
            token: Token to cache
            user_id: User ID
            external_user_id: External user ID
            authorization_code: Authorization code (used when no user identification available)
        """
        cache_key = self._get_user_cache_key(user_id, external_user_id, authorization_code)
        self._user_token_cache[cache_key] = token
    
    def _get_cached_user_token(self, user_id: Optional[str] = None, external_user_id: Optional[str] = None, authorization_code: Optional[str] = None) -> Optional[Token]:
        """
        Get a cached user token if available and valid.
        
        Args:
            user_id: User ID
            external_user_id: External user ID
            authorization_code: Authorization code (used when no user identification available)
            
        Returns:
            Cached token if available and valid, None otherwise
        """
        cache_key = self._get_user_cache_key(user_id, external_user_id, authorization_code)
        token = self._user_token_cache.get(cache_key)
        
        if token and not token.is_expired and token.has_all_scopes(self.USER_DATA_SCOPES):
            return token
        
        # Remove expired or invalid token from cache
        if token:
            del self._user_token_cache[cache_key]
        
        return None
    
    def clear_user_token_cache(self, user_id: Optional[str] = None, external_user_id: Optional[str] = None, authorization_code: Optional[str] = None) -> None:
        """
        Clear cached user token.
        
        Args:
            user_id: User ID to clear cache for
            external_user_id: External user ID to clear cache for
            authorization_code: Authorization code to clear cache for
        """
        if user_id is None and external_user_id is None and authorization_code is None:
            # Clear all user tokens
            self._user_token_cache.clear()
        else:
            cache_key = self._get_user_cache_key(user_id, external_user_id, authorization_code)
            self._user_token_cache.pop(cache_key, None)
    
    async def _get_valid_user_token(
        self, 
        authorization_code: Optional[str] = None, 
        user_id: Optional[str] = None, 
        external_user_id: Optional[str] = None
    ) -> Token:
        """
        Get a valid user token, using cache if available.
        
        Args:
            authorization_code: Authorization code for getting new token if needed
            user_id: User ID for caching
            external_user_id: External user ID for caching
            
        Returns:
            Valid user token
        """
        # Check for cached token first
        cached_token = self._get_cached_user_token(user_id, external_user_id, authorization_code)
        if cached_token:
            return cached_token
        
        # If no cached token and no authorization code, we can't proceed
        if not authorization_code:
            raise ValueError("No cached token available and no authorization code provided")
        
        # Get new token using authorization code
        token = await self._get_user_token_with_code(authorization_code)
        
        # Cache the token using available identification
        if user_id or external_user_id:
            self._cache_user_token(token, user_id, external_user_id)
        else:
            # Cache using authorization code as key
            self._cache_user_token(token, authorization_code=authorization_code)
        
        return token

    async def get_transactions_with_code(
        self,
        authorization_code: str,
        account_id_in: Optional[List[str]] = None,
        status_in: Optional[List[str]] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        booked_date_gte: Optional[str] = None,
        booked_date_lte: Optional[str] = None,
    ) -> TransactionsResponse:
        """
        Get transactions using a cached user token or authorization code.
        
        This method first checks for a cached user token. If available and valid, it uses that.
        Otherwise, it uses the authorization code to get a new user access token and caches it.
        
        Args:
            authorization_code: The authorization code from Tink Link callback (required if no user identification provided)
            account_id_in: List of account IDs to filter transactions (optional)
            status_in: List of transaction statuses to filter (optional)
            page_size: Maximum number of transactions per page (max 100)
            page_token: Token for pagination (optional)
            booked_date_gte: Start date for filtering (YYYY-MM-DD format)
            booked_date_lte: End date for filtering (YYYY-MM-DD format)
            
        Returns:
            TransactionsResponse object containing transactions and pagination info.
            
        Raises:
            TinkAuthenticationError: If the authorization code is invalid or expired.
            TinkAPIError: If the API request fails for other reasons.
            
        Example:
            >>> transactions = await client.get_transactions_with_code(
            ...     authorization_code="auth_code_123",
            ...     page_size=50,
            ...     booked_date_gte="2024-01-01",
            ...     booked_date_lte="2024-01-31"
            ... )
            >>> print(f"Found {len(transactions.transactions)} transactions")
        """
        # Get valid user token (cached or new)
        
        user_token = await self._get_valid_user_token(authorization_code=authorization_code)
        
        # Build query parameters
        params: Dict[str, Any] = {}
        
        if account_id_in:
            for account_id in account_id_in:
                params.setdefault("accountIdIn", []).append(account_id)
        
        if status_in:
            for status in status_in:
                params.setdefault("statusIn", []).append(status)
        
        if page_size is not None:
            params["pageSize"] = min(page_size, 100)  # API limit is 100
        
        if page_token is not None:
            params["pageToken"] = page_token
        
        if booked_date_gte is not None:
            params["bookedDateGte"] = booked_date_gte
        
        if booked_date_lte is not None:
            params["bookedDateLte"] = booked_date_lte
        
        url = self.DATA_BASE_URL + self.TRANSACTIONS_ENDPOINT
        
        try:
            response = await self.http_client.get(
                url,
                params=params,
                headers={
                    "Authorization": f"{user_token.token_type.capitalize()} {user_token.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            response.raise_for_status()
            
            return TransactionsResponse(**response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token might be invalid, clear cache and retry once
                self.clear_user_token_cache(authorization_code=authorization_code)
                user_token = await self._get_valid_user_token(authorization_code=authorization_code)
                
                response = await self.http_client.get(
                    url,
                    params=params,
                    headers={
                        "Authorization": f"{user_token.token_type.capitalize()} {user_token.access_token}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                return TransactionsResponse(**response.json())
            else:
                raise TinkAPIError(f"Get transactions failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e

    async def get_accounts_with_code(self, authorization_code: str) -> AccountsResponse:
        """
        Get accounts using a one-time authorization code.
        
        This method first checks for a cached user token. If available and valid, it uses that.
        Otherwise, it uses the authorization code to get a new user access token and caches it.
        
        Args:
            authorization_code: The authorization code from Tink Link callback
            
        Returns:
            AccountsResponse object containing account information.
            
        Raises:
            TinkAuthenticationError: If the authorization code is invalid or expired.
            TinkAPIError: If the API request fails for other reasons.
            
        Example:
            >>> accounts = await client.get_accounts_with_code("auth_code_123")
            >>> print(f"Found {len(accounts.accounts)} accounts")
        """
        
        user_token = await self._get_valid_user_token(authorization_code=authorization_code)
        
        url = self.DATA_BASE_URL + self.ACCOUNTS_ENDPOINT
        
        try:
            response = await self.http_client.get(
                url,
                headers={
                    "Authorization": f"{user_token.token_type.capitalize()} {user_token.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            response.raise_for_status()
            
            return AccountsResponse(**response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token might be invalid, clear cache and retry once
                self.clear_user_token_cache(authorization_code=authorization_code)
                user_token = await self._get_valid_user_token(authorization_code=authorization_code)
                
                response = await self.http_client.get(
                    url,
                    headers={
                        "Authorization": f"{user_token.token_type.capitalize()} {user_token.access_token}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                return AccountsResponse(**response.json())
            else:
                raise TinkAPIError(f"Get accounts failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e

    async def _get_user_token_with_code(self, authorization_code: str) -> Token:
        """
        Get a user access token using an authorization code (one-time use).
        
        Args:
            authorization_code: The authorization code from Tink Link
            
        Returns:
            Token object containing the user access token.
            
        Raises:
            TinkAuthenticationError: If the authorization code is invalid or expired.
            TinkAPIError: If the API request fails for other reasons.
        """
        token_request = AuthorizationCodeTokenRequest(
            client_id=self.client_id,
            client_secret=self.client_secret,
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
                raise TinkAuthenticationError("Invalid or expired authorization code") from e
            else:
                raise TinkAPIError(f"API request failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TinkAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise TinkAPIError(f"Unexpected error: {str(e)}") from e 