"""
Tests for Tink callback parsing functionality.
"""

import pytest
from unittest.mock import Mock
from tink_finance.callback import (
    parse_tink_callback,
    parse_tink_callback_url,
    is_user_cancelled,
    get_error_category,
    get_error_reason,
    get_user_message,
    get_tracking_id
)
from tink_finance.models import TinkCallbackResult
from tink_finance.exceptions import TinkCallbackError


class TestCallbackParsing:
    """Test callback parsing functionality."""
    
    def test_parse_success_callback(self):
        """Test parsing successful callback."""
        params = {
            "code": "auth_code_123",
            "credentials_id": "cred_456",
            "state": "user_session_789"
        }
        
        result = parse_tink_callback(params)
        
        assert result.is_success is True
        assert result.is_user_cancelled is False
        assert result.success.code == "auth_code_123"
        assert result.success.credentials_id == "cred_456"
        assert result.success.state == "user_session_789"
        assert result.error is None
    
    def test_parse_success_callback_minimal(self):
        """Test parsing successful callback with minimal parameters."""
        params = {
            "code": "auth_code_123",
            "credentials_id": "cred_456"
        }
        
        result = parse_tink_callback(params)
        
        assert result.is_success is True
        assert result.success.code == "auth_code_123"
        assert result.success.credentials_id == "cred_456"
        assert result.success.state is None
    
    def test_parse_error_callback(self):
        """Test parsing error callback."""
        params = {
            "error": "AUTHENTICATION_ERROR",
            "error_reason": "USER_DECLINED_CONSENT",
            "message": "The user declined to provide consent",
            "tracking_id": "track_123",
            "state": "user_session_789",
            "provider_name": "Test Bank",
            "credentials": "cred_456"
        }
        
        result = parse_tink_callback(params)
        
        assert result.is_success is False
        assert result.is_user_cancelled is False
        assert result.error.error == "AUTHENTICATION_ERROR"
        assert result.error.error_reason == "USER_DECLINED_CONSENT"
        assert result.error.message == "The user declined to provide consent"
        assert result.error.tracking_id == "track_123"
        assert result.error.state == "user_session_789"
        assert result.error.provider_name == "Test Bank"
        assert result.error.credentials == "cred_456"
        assert result.success is None
    
    def test_parse_user_cancelled_callback(self):
        """Test parsing user cancelled callback."""
        params = {
            "error": "USER_CANCELLED",
            "error_reason": "USER_CANCELLED",
            "message": "The user cancelled the flow",
            "tracking_id": "track_123",
            "state": "user_session_789"
        }
        
        result = parse_tink_callback(params)
        
        assert result.is_success is False
        assert result.is_user_cancelled is True
        assert result.error.error == "USER_CANCELLED"
        assert result.error.error_reason == "USER_CANCELLED"
    
    def test_parse_callback_url(self):
        """Test parsing callback URL."""
        url = "https://example.com/callback?code=auth_code_123&credentials_id=cred_456&state=user_session"
        
        result = parse_tink_callback_url(url)
        
        assert result.is_success is True
        assert result.success.code == "auth_code_123"
        assert result.success.credentials_id == "cred_456"
        assert result.success.state == "user_session"
    
    def test_parse_callback_url_with_errors(self):
        """Test parsing callback URL with error parameters."""
        url = "https://example.com/callback?error=AUTHENTICATION_ERROR&error_reason=USER_DECLINED_CONSENT&message=User%20declined&tracking_id=track_123"
        
        result = parse_tink_callback_url(url)
        
        assert result.is_success is False
        assert result.error.error == "AUTHENTICATION_ERROR"
        assert result.error.error_reason == "USER_DECLINED_CONSENT"
        assert result.error.message == "User declined"
        assert result.error.tracking_id == "track_123"
    
    def test_invalid_callback_missing_required_fields(self):
        """Test handling of invalid callback with missing required fields."""
        params = {"state": "user_session"}
        
        with pytest.raises(TinkCallbackError, match="Invalid callback parameters"):
            parse_tink_callback(params)
    
    def test_invalid_callback_url(self):
        """Test handling of invalid callback URL."""
        url = "https://example.com/callback"
        
        with pytest.raises(TinkCallbackError, match="Callback URL has no query parameters"):
            parse_tink_callback_url(url)
    
    def test_utility_functions_success(self):
        """Test utility functions with success callback."""
        params = {
            "code": "auth_code_123",
            "credentials_id": "cred_456"
        }
        result = parse_tink_callback(params)
        
        assert is_user_cancelled(result) is False
        assert get_error_category(result) is None
        assert get_error_reason(result) is None
        assert get_user_message(result) is None
        assert get_tracking_id(result) is None
    
    def test_utility_functions_error(self):
        """Test utility functions with error callback."""
        params = {
            "error": "AUTHENTICATION_ERROR",
            "error_reason": "USER_DECLINED_CONSENT",
            "message": "User declined consent",
            "tracking_id": "track_123"
        }
        result = parse_tink_callback(params)
        
        assert is_user_cancelled(result) is False
        assert get_error_category(result) == "AUTHENTICATION_ERROR"
        assert get_error_reason(result) == "USER_DECLINED_CONSENT"
        assert get_user_message(result) == "User declined consent"
        assert get_tracking_id(result) == "track_123"
    
    def test_utility_functions_user_cancelled(self):
        """Test utility functions with user cancelled callback."""
        params = {
            "error": "USER_CANCELLED",
            "error_reason": "USER_CANCELLED",
            "message": "User cancelled",
            "tracking_id": "track_123"
        }
        result = parse_tink_callback(params)
        
        assert is_user_cancelled(result) is True
        assert get_error_category(result) is None  # User cancelled is not treated as error
        assert get_error_reason(result) is None
        assert get_user_message(result) is None
        assert get_tracking_id(result) is None
    
    def test_various_error_types(self):
        """Test parsing various error types."""
        error_cases = [
            {
                "error": "BAD_REQUEST",
                "error_reason": "INVALID_PARAMETER_CLIENT_ID",
                "message": "Invalid client ID",
                "tracking_id": "track_123"
            },
            {
                "error": "TEMPORARY_ERROR",
                "error_reason": "REQUEST_FAILED_FETCH_PROVIDER",
                "message": "Temporary service issue",
                "tracking_id": "track_456"
            },
            {
                "error": "INTERNAL_ERROR",
                "error_reason": "REQUEST_FAILED_CREATE_CREDENTIALS",
                "message": "Internal server error",
                "tracking_id": "track_789"
            }
        ]
        
        for error_case in error_cases:
            result = parse_tink_callback(error_case)
            
            assert result.is_success is False
            assert result.is_user_cancelled is False
            assert result.error.error == error_case["error"]
            assert result.error.error_reason == error_case["error_reason"]
            assert result.error.message == error_case["message"]
            assert result.error.tracking_id == error_case["tracking_id"] 