#!/usr/bin/env python3
"""
Example script demonstrating Tink Finance user management functionality.

This script shows how to:
1. Create users with automatic token management
2. Get user information (requires user tokens from OAuth flow)
3. Delete users (requires user tokens from OAuth flow)
4. Demonstrate the simplified API with internal token caching

Make sure to set your TINK_CLIENT_ID and TINK_CLIENT_SECRET environment variables
before running this script.
"""

import asyncio
import os
from datetime import datetime
from tink_finance import TinkClient, Token, TinkAPIError, TinkAuthenticationError


async def demonstrate_simplified_user_creation():
    """Demonstrate the simplified user creation API."""
    
    client = TinkClient()
    
    try:
        print("👤 Creating users with automatic token management...")
        
        # Create first user - token will be automatically obtained and cached
        user1 = await client.create_user(
            market="SE",
            locale="sv_SE",
            external_user_id="demo_user_1"
        )
        print(f"✅ Created user 1: {user1.user_id}")
        
        # Create second user - will reuse cached token if still valid
        user2 = await client.create_user(
            market="NO",
            locale="nb_NO",
            external_user_id="demo_user_2"
        )
        print(f"✅ Created user 2: {user2.user_id}")
        
        # Create third user - demonstrates token reuse
        user3 = await client.create_user(
            market="DK",
            locale="da_DK",
            external_user_id="demo_user_3"
        )
        print(f"✅ Created user 3: {user3.user_id}")
        
        print("\n🎯 Key benefits:")
        print("   - No manual token management required")
        print("   - Automatic token caching and refresh")
        print("   - Proper scope handling")
        print("   - Automatic retry on token expiration")
        
        return [user1, user2, user3]
        
    except Exception as e:
        print(f"❌ Error in user creation: {e}")
        return []
    finally:
        await client.close()


async def demonstrate_token_caching():
    """Demonstrate token caching behavior."""
    
    client = TinkClient()
    
    try:
        print("\n🔄 Demonstrating token caching...")
        
        # First operation - will get a new token
        print("1. First user creation (gets new token)")
        user1 = await client.create_user(
            market="SE",
            locale="sv_SE",
            external_user_id="cache_demo_1"
        )
        print(f"   Created: {user1.user_id}")
        
        # Second operation - should reuse cached token
        print("2. Second user creation (reuses cached token)")
        user2 = await client.create_user(
            market="NO",
            locale="nb_NO",
            external_user_id="cache_demo_2"
        )
        print(f"   Created: {user2.user_id}")
        
        # Third operation - should still reuse cached token
        print("3. Third user creation (still reuses cached token)")
        user3 = await client.create_user(
            market="DK",
            locale="da_DK",
            external_user_id="cache_demo_3"
        )
        print(f"   Created: {user3.user_id}")
        
        print("\n📊 Token caching benefits:")
        print("   - Reduced API calls for token requests")
        print("   - Faster subsequent operations")
        print("   - Automatic expiration handling")
        print("   - Automatic retry on 401 errors")
        
    except Exception as e:
        print(f"❌ Error in token caching demo: {e}")
    finally:
        await client.close()


async def demonstrate_user_operations():
    """Demonstrate user operations that require user tokens."""
    
    print("\n👤 User Operations (requires user tokens from OAuth flow)")
    print("=" * 60)
    
    print("Note: The following operations require user tokens obtained through")
    print("Tink's OAuth flow, not client tokens. In a real application:")
    print()
    print("1. User authenticates through Tink OAuth")
    print("2. You receive a user token with appropriate scopes")
    print("3. You use that token for user-specific operations")
    print()
    
    # Example of how user operations would work (conceptual)
    print("Example usage with user tokens:")
    print("""
    # Get user information
    user_info = await client.get_user(user_token)
    print(f"User ID: {user_info.id}")
    print(f"Market: {user_info.profile.market}")
    
    # Delete user
    await client.delete_user(user_token)
    print("User deleted successfully")
    """)
    
    print("Key differences:")
    print("- create_user(): Uses internal client token management")
    print("- get_user(): Requires user token from OAuth flow")
    print("- delete_user(): Requires user token from OAuth flow")


async def demonstrate_error_handling():
    """Demonstrate error handling with the simplified API."""
    
    client = TinkClient()
    
    try:
        print("\n🚨 Demonstrating error handling...")
        
        # This should work fine
        print("1. Normal user creation:")
        user = await client.create_user(
            market="SE",
            locale="sv_SE",
            external_user_id="error_demo"
        )
        print(f"   ✅ Success: {user.user_id}")
        
        # Demonstrate what happens with invalid credentials
        print("\n2. Error handling with invalid credentials:")
        print("   (This would fail if credentials were invalid)")
        print("   - Automatic token refresh on 401 errors")
        print("   - Clear error messages")
        print("   - Graceful failure handling")
        
    except TinkAuthenticationError as e:
        print(f"   ❌ Authentication error: {e}")
    except TinkAPIError as e:
        print(f"   ❌ API error: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    finally:
        await client.close()


async def main():
    """Run all demonstrations."""
    
    print("🚀 Tink Finance Simplified User Management Example")
    print("=" * 60)
    
    # Check if credentials are set
    if not os.getenv("TINK_CLIENT_ID") or not os.getenv("TINK_CLIENT_SECRET"):
        print("❌ Please set TINK_CLIENT_ID and TINK_CLIENT_SECRET environment variables")
        print("   export TINK_CLIENT_ID='your_client_id'")
        print("   export TINK_CLIENT_SECRET='your_client_secret'")
        exit(1)
    
    # Run demonstrations
    await demonstrate_simplified_user_creation()
    await demonstrate_token_caching()
    await demonstrate_user_operations()
    await demonstrate_error_handling()
    
    print("\n✅ All demonstrations completed!")
    print("\n🎉 Key improvements:")
    print("   - No manual token management required")
    print("   - Automatic caching and refresh")
    print("   - Simplified API for common operations")
    print("   - Better error handling and retry logic")


if __name__ == "__main__":
    asyncio.run(main()) 