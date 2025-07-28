"""
Tests for transaction functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from tink_finance.client import TinkClient
from tink_finance.models import (
    TransactionsResponse, 
    AccountsResponse, 
    Transaction, 
    Account,
    TokenResponse,
    Token
)


class TestTransactionFunctionality:
    """Test transaction-related functionality."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TinkClient(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
    
    @pytest.fixture
    def mock_token_response(self):
        """Mock token response."""
        return TokenResponse(
            access_token="test_access_token",
            token_type="bearer",
            expires_in=1800,
            scope="accounts:read,balances:read,transactions:read"
        )
    
    @pytest.fixture
    def mock_transactions_response(self):
        """Mock transactions response."""
        return {
            "transactions": [
                {
                    "id": "transaction_1",
                    "accountId": "account_1",
                    "amount": 100.50,
                    "currencyCode": "EUR",
                    "description": "Test transaction",
                    "date": "2024-01-15",
                    "status": "BOOKED"
                }
            ],
            "nextPageToken": "next_page_token",
            "totalCount": 1
        }
    
    @pytest.fixture
    def mock_accounts_response(self):
        """Mock accounts response."""
        return {
            "accounts": [
                {
                    "id": "account_1",
                    "name": "Test Account",
                    "type": "CHECKING",
                    "balance": 1000.00,
                    "currencyCode": "EUR",
                    "status": "ACTIVE"
                }
            ],
            "totalCount": 1
        }
    
    def test_get_connection_url(self, client):
        """Test connection URL generation."""
        url = client.get_connection_url(
            redirect_uri="https://example.com/callback",
            market="ES",
            locale="en_US",
            state="test_state"
        )
        
        assert "https://link.tink.com/1.0/transactions/connect-accounts/" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A//example.com/callback" in url
        assert "market=ES" in url
        assert "locale=en_US" in url
        assert "state=test_state" in url
    
    @pytest.mark.asyncio
    async def test_get_transactions_with_code(self, client, mock_token_response, mock_transactions_response):
        """Test getting transactions with authorization code."""
        with patch.object(client.http_client, 'post', new_callable=AsyncMock) as mock_post, \
             patch.object(client.http_client, 'get', new_callable=AsyncMock) as mock_get:
            
            # Mock token response
            mock_post.return_value.json.return_value = mock_token_response.model_dump()
            mock_post.return_value.raise_for_status = AsyncMock()
            
            # Mock transactions response
            mock_get.return_value.json.return_value = mock_transactions_response
            mock_get.return_value.raise_for_status = AsyncMock()
            
            result = await client.get_transactions_with_code(
                authorization_code="test_auth_code",
                page_size=50,
                booked_date_gte="2024-01-01",
                booked_date_lte="2024-01-31"
            )
            
            assert isinstance(result, TransactionsResponse)
            assert len(result.transactions) == 1
            assert result.transactions[0].id == "transaction_1"
            assert result.transactions[0].amount == 100.50
            assert result.nextPageToken == "next_page_token"
            assert result.totalCount == 1
    
    @pytest.mark.asyncio
    async def test_get_accounts_with_code(self, client, mock_token_response, mock_accounts_response):
        """Test getting accounts with authorization code."""
        with patch.object(client.http_client, 'post', new_callable=AsyncMock) as mock_post, \
             patch.object(client.http_client, 'get', new_callable=AsyncMock) as mock_get:
            
            # Mock token response
            mock_post.return_value.json.return_value = mock_token_response.model_dump()
            mock_post.return_value.raise_for_status = AsyncMock()
            
            # Mock accounts response
            mock_get.return_value.json.return_value = mock_accounts_response
            mock_get.return_value.raise_for_status = AsyncMock()
            
            result = await client.get_accounts_with_code(
                authorization_code="test_auth_code"
            )
            
            assert isinstance(result, AccountsResponse)
            assert len(result.accounts) == 1
            assert result.accounts[0].id == "account_1"
            assert result.accounts[0].name == "Test Account"
            assert result.accounts[0].balance == 1000.00
            assert result.totalCount == 1
    
    @pytest.mark.asyncio
    async def test_get_transactions_with_filters(self, client, mock_token_response, mock_transactions_response):
        """Test getting transactions with filters."""
        with patch.object(client.http_client, 'post', new_callable=AsyncMock) as mock_post, \
             patch.object(client.http_client, 'get', new_callable=AsyncMock) as mock_get:
            
            # Mock token response
            mock_post.return_value.json.return_value = mock_token_response.model_dump()
            mock_post.return_value.raise_for_status = AsyncMock()
            
            # Mock transactions response
            mock_get.return_value.json.return_value = mock_transactions_response
            mock_get.return_value.raise_for_status = AsyncMock()
            
            result = await client.get_transactions_with_code(
                authorization_code="test_auth_code",
                account_id_in=["account_1", "account_2"],
                status_in=["BOOKED", "PENDING"],
                page_size=100,
                page_token="test_page_token"
            )
            
            # Verify the request was made with correct parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "accountIdIn" in call_args[1]["params"]
            assert "statusIn" in call_args[1]["params"]
            assert call_args[1]["params"]["pageSize"] == 100
            assert call_args[1]["params"]["pageToken"] == "test_page_token"
    
    @pytest.mark.asyncio
    async def test_invalid_authorization_code(self, client):
        """Test handling of invalid authorization code."""
        with patch.object(client.http_client, 'post', new_callable=AsyncMock) as mock_post:
            # Mock 401 response
            mock_post.return_value.raise_for_status.side_effect = Exception("401")
            mock_post.return_value.status_code = 401
            
            with pytest.raises(Exception):
                await client.get_transactions_with_code(
                    authorization_code="invalid_auth_code"
                )
    
    @pytest.mark.asyncio
    async def test_page_size_limit(self, client, mock_token_response, mock_transactions_response):
        """Test that page size is limited to 100."""
        with patch.object(client.http_client, 'post', new_callable=AsyncMock) as mock_post, \
             patch.object(client.http_client, 'get', new_callable=AsyncMock) as mock_get:
            
            # Mock token response
            mock_post.return_value.json.return_value = mock_token_response.model_dump()
            mock_post.return_value.raise_for_status = AsyncMock()
            
            # Mock transactions response
            mock_get.return_value.json.return_value = mock_transactions_response
            mock_get.return_value.raise_for_status = AsyncMock()
            
            await client.get_transactions_with_code(
                authorization_code="test_auth_code",
                page_size=150  # Should be limited to 100
            )
            
            # Verify page size was limited
            call_args = mock_get.call_args
            assert call_args[1]["params"]["pageSize"] == 100 