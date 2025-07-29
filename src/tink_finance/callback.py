"""
Tink callback parsing utilities.

This module provides utilities for parsing Tink Link callback responses,
handling both successful responses and various error cases.
"""

from typing import Dict, Any, Optional, Union
from urllib.parse import parse_qs, urlparse
from tink_finance.models import TinkCallbackResult, TinkCallbackSuccess, TinkCallbackError
from tink_finance.exceptions import TinkCallbackError as TinkCallbackParseError

def parse_tink_callback_from_request(request: Any) -> TinkCallbackResult:
    """
    Parse Tink callback from a web framework Request object.
    
    This function extracts query parameters from various web framework Request objects
    and parses the Tink callback response. It supports FastAPI, Flask, and Django.
    
    Args:
        request: Request object from FastAPI, Flask, or Django containing the callback parameters
        
    Returns:
        TinkCallbackResult with either success or error information
        
    Raises:
        TinkCallbackParseError: If the callback parameters are invalid or missing required fields
        
    Example:
        >>> # FastAPI
        >>> from fastapi import Request
        >>> @app.get("/tink/callback")
        >>> async def handle_callback(request: Request):
        >>>     result = parse_tink_callback_from_request(request)
        >>> 
        >>> # Flask
        >>> from flask import request
        >>> @app.route("/tink/callback")
        >>> def handle_callback():
        >>>     result = parse_tink_callback_from_request(request)
        >>> 
        >>> # Django
        >>> from django.http import HttpRequest
        >>> def handle_callback(request: HttpRequest):
        >>>     result = parse_tink_callback_from_request(request)
    """
    try:
        # Extract query parameters based on the request type
        query_params = _extract_query_params(request)
        
        # Parse the callback using the existing function
        return parse_tink_callback(query_params)
        
    except Exception as e:
        raise TinkCallbackParseError(f"Failed to parse callback from request: {str(e)}") from e


def _extract_query_params(request: Any) -> Dict[str, Any]:
    """
    Extract query parameters from various web framework request objects.
    
    Args:
        request: Request object from FastAPI, Flask, or Django
        
    Returns:
        Dictionary of query parameters
        
    Raises:
        TinkCallbackParseError: If the request type is not supported
    """
    # Try to detect the framework and extract parameters accordingly
    
    # FastAPI Request
    if hasattr(request, 'query_params'):
        return dict(request.query_params)
    
    # Flask Request
    elif hasattr(request, 'args'):
        return dict(request.args)
    
    # Django HttpRequest
    elif hasattr(request, 'GET'):
        return dict(request.GET)
    
    # Generic object with query_params attribute
    elif hasattr(request, 'query_params'):
        return dict(request.query_params)
    
    # Generic object with args attribute
    elif hasattr(request, 'args'):
        return dict(request.args)
    
    # Generic object with GET attribute
    elif hasattr(request, 'GET'):
        return dict(request.GET)
    
    else:
        raise TinkCallbackParseError(
            f"Unsupported request type: {type(request)}. "
            "Expected FastAPI Request, Flask request, or Django HttpRequest. "
            "The request object should have query_params, args, or GET attribute."
        )


def parse_tink_callback(query_params: Dict[str, Any]) -> TinkCallbackResult:
    """
    Parse Tink callback query parameters.
    
    This function handles both successful responses and error cases from Tink Link.
    It's the core parsing function that works with any dictionary of query parameters.
    
    Args:
        query_params: Dictionary of query parameters from the callback URL
        
    Returns:
        TinkCallbackResult with either success or error information
        
    Raises:
        TinkCallbackParseError: If the callback parameters are invalid or missing required fields
        
    Example:
        >>> # Success case
        >>> params = {"code": "auth_code_123", "credentials_id": "cred_456", "state": "user_session"}
        >>> result = parse_tink_callback(params)
        >>> print(result.is_success)  # True
        >>> print(result.success.code)  # "auth_code_123"
        
        >>> # Error case
        >>> params = {"error": "AUTHENTICATION_ERROR", "error_reason": "USER_DECLINED_CONSENT", ...}
        >>> result = parse_tink_callback(params)
        >>> print(result.is_success)  # False
        >>> print(result.error.error)  # "AUTHENTICATION_ERROR"
    """
    # Check if this is an error response
    if "error" in query_params:
        return _parse_error_callback(query_params)
    
    # Check if this is a success response
    if "code" in query_params and "credentials_id" in query_params:
        return _parse_success_callback(query_params)
    
    # Invalid callback - missing required fields
    raise TinkCallbackParseError(
        "Invalid callback parameters: missing required fields. "
        "Expected either 'code' and 'credentials_id' for success, "
        "or 'error' for error responses."
    )


def parse_tink_callback_url(callback_url: str) -> TinkCallbackResult:
    """
    Parse Tink callback URL.
    
    Args:
        callback_url: Full callback URL from Tink
        
    Returns:
        TinkCallbackResult with parsed information
        
    Raises:
        TinkCallbackParseError: If the URL is invalid or missing required parameters
    """
    try:
        parsed_url = urlparse(callback_url)
        query_string = parsed_url.query
        
        if not query_string:
            raise TinkCallbackParseError("Callback URL has no query parameters")
        
        # Parse query string into dictionary
        query_params = {}
        for key, values in parse_qs(query_string).items():
            # parse_qs returns lists, but we expect single values
            query_params[key] = values[0] if values else ""
        
        return parse_tink_callback(query_params)
        
    except Exception as e:
        raise TinkCallbackParseError(f"Failed to parse callback URL: {str(e)}") from e


def _parse_success_callback(params: Dict[str, Any]) -> TinkCallbackResult:
    """Parse successful callback parameters."""
    try:
        success = TinkCallbackSuccess(
            code=params["code"],
            credentials_id=params["credentials_id"],
            state=params.get("state")
        )
        return TinkCallbackResult.from_success(success)
    except Exception as e:
        raise TinkCallbackParseError(f"Failed to parse success callback: {str(e)}") from e


def _parse_error_callback(params: Dict[str, Any]) -> TinkCallbackResult:
    """Parse error callback parameters."""
    try:
        error = TinkCallbackError(
            error=params["error"],
            error_reason=params["error_reason"],
            message=params["message"],
            tracking_id=params["tracking_id"],
            credentials=params.get("credentials"),
            error_type=params.get("error_type"),
            provider_name=params.get("provider_name"),
            payment_request_id=params.get("payment_request_id"),
            state=params.get("state")
        )
        return TinkCallbackResult.from_error(error)
    except Exception as e:
        raise TinkCallbackParseError(f"Failed to parse error callback: {str(e)}") from e


def is_user_cancelled(result: TinkCallbackResult) -> bool:
    """
    Check if the callback indicates user cancellation.
    
    Args:
        result: Parsed callback result
        
    Returns:
        True if the user cancelled the flow (not an error)
    """
    return result.is_user_cancelled


def get_error_category(result: TinkCallbackResult) -> Optional[str]:
    """
    Get the error category for error callbacks.
    
    Args:
        result: Parsed callback result
        
    Returns:
        Error category string or None if not an error
    """
    if result.is_success or result.is_user_cancelled:
        return None
    return result.error.error if result.error else None


def get_error_reason(result: TinkCallbackResult) -> Optional[str]:
    """
    Get the specific error reason for error callbacks.
    
    Args:
        result: Parsed callback result
        
    Returns:
        Error reason string or None if not an error
    """
    if result.is_success or result.is_user_cancelled:
        return None
    return result.error.error_reason if result.error else None


def get_user_message(result: TinkCallbackResult) -> Optional[str]:
    """
    Get the user-facing error message for error callbacks.
    
    Args:
        result: Parsed callback result
        
    Returns:
        User-friendly error message or None if not an error
    """
    if result.is_success or result.is_user_cancelled:
        return None
    return result.error.message if result.error else None


def get_tracking_id(result: TinkCallbackResult) -> Optional[str]:
    """
    Get the tracking ID for error callbacks.
    
    Args:
        result: Parsed callback result
        
    Returns:
        Tracking ID string or None if not an error
    """
    if result.is_success or result.is_user_cancelled:
        return None
    return result.error.tracking_id if result.error else None 