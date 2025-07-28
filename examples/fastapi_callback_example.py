#!/usr/bin/env python3
"""
FastAPI example demonstrating Tink callback handling.

This example shows how to create a FastAPI endpoint that handles Tink Link callbacks,
parsing both successful responses and various error cases.
"""

import asyncio
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from tink_finance.client import TinkClient
from tink_finance.callback import (
    parse_tink_callback,
    is_user_cancelled,
    get_error_category,
    get_error_reason,
    get_user_message,
    get_tracking_id
)
from tink_finance.exceptions import TinkCallbackError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Tink Callback Handler", version="1.0.0")

# Initialize Tink client
tink_client = TinkClient()


class CallbackResponse(BaseModel):
    """Response model for callback endpoint."""
    success: bool
    message: str
    data: Dict[str, Any] = {}


@app.get("/tink/callback")
async def handle_tink_callback(request: Request) -> CallbackResponse:
    """
    Handle Tink Link callback.
    
    This endpoint receives callbacks from Tink Link and processes them appropriately.
    It handles both successful responses and various error cases.
    
    The endpoint automatically extracts all query parameters from the request,
    making it future-proof for any new parameters Tink might add.
    """
    try:
        # Parse the callback directly from the request
        result = parse_tink_callback(dict(request.query_params))
        
        # Log the callback for debugging
        logger.info(f"Tink callback received: success={result.is_success}, user_cancelled={result.is_user_cancelled}")
        
        # Handle different cases
        if result.is_success:
            return await _handle_success_callback(result)
        elif result.is_user_cancelled:
            return await _handle_user_cancelled(result)
        else:
            return await _handle_error_callback(result)
            
    except TinkCallbackError as e:
        logger.error(f"Callback parsing error: {e}")
        return CallbackResponse(
            success=False,
            message="Invalid callback parameters",
            data={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error handling callback: {e}")
        return CallbackResponse(
            success=False,
            message="Internal server error",
            data={"error": str(e)}
        )


async def _handle_success_callback(result) -> CallbackResponse:
    """Handle successful callback."""
    logger.info(f"Success callback: code={result.success.code}, credentials_id={result.success.credentials_id}")
    
    try:
        # Get transactions using the authorization code
        transactions = await tink_client.get_transactions_with_code(
            authorization_code=result.success.code,
            page_size=50
        )
        
        # Get accounts using the same code
        accounts = await tink_client.get_accounts_with_code(
            authorization_code=result.success.code
        )
        
        return CallbackResponse(
            success=True,
            message="Successfully retrieved financial data",
            data={
                "code": result.success.code,
                "credentials_id": result.success.credentials_id,
                "state": result.success.state,
                "transactions_count": len(transactions.transactions),
                "accounts_count": len(accounts.accounts),
                "total_transactions": transactions.totalCount,
                "total_accounts": accounts.totalCount
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting data with authorization code: {e}")
        return CallbackResponse(
            success=False,
            message="Failed to retrieve financial data",
            data={
                "code": result.success.code,
                "credentials_id": result.success.credentials_id,
                "error": str(e)
            }
        )


async def _handle_user_cancelled(result) -> CallbackResponse:
    """Handle user cancellation (not an error)."""
    logger.info("User cancelled the Tink flow")
    
    return CallbackResponse(
        success=True,  # Not an error, just user choice
        message="User cancelled the bank connection flow",
        data={
            "user_cancelled": True,
            "state": result.error.state if result.error else None
        }
    )


async def _handle_error_callback(result) -> CallbackResponse:
    """Handle error callback."""
    error_category = get_error_category(result)
    error_reason = get_error_reason(result)
    user_message = get_user_message(result)
    tracking_id = get_tracking_id(result)
    
    logger.error(f"Tink error: {error_category} - {error_reason} (tracking_id: {tracking_id})")
    
    # Determine appropriate user message based on error type
    if error_category == "BAD_REQUEST":
        user_friendly_message = "There was an issue with the request. Please try again."
    elif error_category == "AUTHENTICATION_ERROR":
        user_friendly_message = "There was an issue with bank authentication. Please try again."
    elif error_category == "TEMPORARY_ERROR":
        user_friendly_message = "Temporary service issue. Please try again later."
    elif error_category == "INTERNAL_ERROR":
        user_friendly_message = "An unexpected error occurred. Please contact support."
    else:
        user_friendly_message = user_message or "An error occurred during the bank connection process."
    
    return CallbackResponse(
        success=False,
        message=user_friendly_message,
        data={
            "error_category": error_category,
            "error_reason": error_reason,
            "tracking_id": tracking_id,
            "state": result.error.state if result.error else None,
            "provider_name": result.error.provider_name if result.error else None,
            "credentials": result.error.credentials if result.error else None
        }
    )


@app.get("/tink/start")
async def start_tink_flow() -> HTMLResponse:
    """
    Start the Tink flow by redirecting to the connection URL.
    """
    connection_url = tink_client.get_connection_url(
        redirect_uri="http://localhost:8000/tink/callback",
        market="ES",
        locale="en_US",
        state="user_session_123"
    )
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Start Tink Flow</title>
    </head>
    <body>
        <h1>Connect Your Bank Account</h1>
        <p>Click the button below to connect your bank account using Tink:</p>
        <a href="{connection_url}" style="
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
        ">
            Connect Bank Account
        </a>
        <p><small>This will redirect you to Tink to securely connect your bank account.</small></p>
    </body>
    </html>
    """)


@app.get("/")
async def root() -> HTMLResponse:
    """Root endpoint with links to start the flow."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tink Finance Demo</title>
    </head>
    <body>
        <h1>Tink Finance Integration Demo</h1>
        <p>This demo shows how to handle Tink Link callbacks with proper error handling.</p>
        
        <h2>Available Endpoints:</h2>
        <ul>
            <li><a href="/tink/start">Start Tink Flow</a> - Begin the bank connection process</li>
            <li><a href="/tink/callback">Callback Endpoint</a> - Handles Tink callbacks (called by Tink)</li>
            <li><a href="/docs">API Documentation</a> - View the API docs</li>
        </ul>
        
        <h2>How it works:</h2>
        <ol>
            <li>Click "Start Tink Flow" to begin</li>
            <li>You'll be redirected to Tink to connect your bank</li>
            <li>Tink will redirect back to the callback endpoint</li>
            <li>The callback handler will process the response and show results</li>
        </ol>
        
        <h2>Error Handling:</h2>
        <p>The callback handler properly handles all Tink error cases:</p>
        <ul>
            <li><strong>USER_CANCELLED</strong> - User cancelled the flow (not an error)</li>
            <li><strong>BAD_REQUEST</strong> - Invalid request parameters</li>
            <li><strong>AUTHENTICATION_ERROR</strong> - Bank authentication issues</li>
            <li><strong>TEMPORARY_ERROR</strong> - Temporary service issues</li>
            <li><strong>INTERNAL_ERROR</strong> - Unexpected Tink platform errors</li>
        </ul>
        
        <h2>Future-Proof Design:</h2>
        <p>The callback handler automatically extracts all query parameters from the request,
        making it future-proof for any new parameters Tink might add.</p>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Tink Callback Handler Demo")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🏠 Homepage: http://localhost:8000/")
    print("🔗 Start Flow: http://localhost:8000/tink/start")
    print("")
    print("Make sure to set your TINK_CLIENT_ID and TINK_CLIENT_SECRET environment variables!")
    
    uvicorn.run(app, host="0.0.0.0", port=8000) 