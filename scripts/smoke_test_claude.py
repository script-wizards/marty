#!/usr/bin/env python3
"""
Smoke test for Claude integration.
Minimal test to verify basic functionality is working.
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def smoke_test():
    """Basic smoke test for Claude integration."""
    # Import after path setup to avoid linting issues
    from ai_client import ConversationMessage, generate_ai_response

    print("🔍 Claude Integration Smoke Test")
    print("=" * 40)

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not found in environment")
        return False

    try:
        # Test 1: Basic connection
        print("1. Testing basic connection...")
        response = await generate_ai_response("Hi", [])
        print(f"✅ Response: {response[:50]}...")

        # Test 2: Conversation history
        print("\n2. Testing conversation history...")
        history = [
            ConversationMessage(role="user", content="Hi", timestamp=datetime.now())
        ]
        response2 = await generate_ai_response("What books do you recommend?", history)
        print(f"✅ Response: {response2[:50]}...")

        print("\n🎉 Smoke test PASSED - Claude integration is working!")
        return True

    except Exception as e:
        print(f"❌ Smoke test FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(smoke_test())
    sys.exit(0 if success else 1)
