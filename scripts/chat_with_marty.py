#!/usr/bin/env python3
"""
Terminal chat interface to interact with Marty.
Quick way to test the AI without going through the full SMS pipeline.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MartyChat:
    """Simple terminal chat interface for Marty."""

    def __init__(self):
        self.conversation_history = []
        self.customer_context = {
            "name": "Terminal User",
            "phone": "+1555000000",
            "customer_id": "test_user",
            "current_time": datetime.now(UTC).isoformat(),
            "current_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "current_day": datetime.now(UTC).strftime("%A"),
        }

    async def start_chat(self):
        """Start the interactive chat session."""
        # Import after path setup
        from ai_client import ConversationMessage, generate_ai_response

        print("🧙 Marty Terminal Chat")
        print("=" * 40)
        print("Type 'quit' or 'exit' to end the chat")
        print("Type 'clear' to clear conversation history")
        print("Type 'context' to see current context")
        print("=" * 40)

        # Check API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("❌ ANTHROPIC_API_KEY not found in environment")
            print("Please set your Claude API key in .env file")
            return

        # Start with Marty's natural greeting using the system prompt
        print("\n🤔 Marty is thinking...")
        initial_response = await generate_ai_response(
            user_message="hello",
            conversation_history=[],
            customer_context=self.customer_context,
        )
        print(f"\n🤖 Marty: {initial_response}")

        # Add initial greeting to history
        now = datetime.now(UTC)
        self.conversation_history.append(
            ConversationMessage(role="user", content="hello", timestamp=now)
        )
        self.conversation_history.append(
            ConversationMessage(
                role="assistant", content=initial_response, timestamp=now
            )
        )

        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ["quit", "exit"]:
                    print("\n👋 Goodbye!")
                    break

                if user_input.lower() == "clear":
                    self.conversation_history = []
                    print("\n🧹 Conversation history cleared!")
                    continue

                if user_input.lower() == "context":
                    print("\n📋 Current Context:")
                    for key, value in self.customer_context.items():
                        print(f"  {key}: {value}")
                    continue

                # Update time context for each message
                now = datetime.now(UTC)
                self.customer_context.update(
                    {
                        "current_time": now.isoformat(),
                        "current_date": now.strftime("%Y-%m-%d"),
                        "current_day": now.strftime("%A"),
                    }
                )

                # Generate AI response
                print("\n🤔 Marty is thinking...")
                response = await generate_ai_response(
                    user_message=user_input,
                    conversation_history=self.conversation_history,
                    customer_context=self.customer_context,
                )

                # Add to conversation history
                self.conversation_history.append(
                    ConversationMessage(role="user", content=user_input, timestamp=now)
                )
                self.conversation_history.append(
                    ConversationMessage(
                        role="assistant", content=response, timestamp=datetime.now(UTC)
                    )
                )

                # Keep history reasonable (last 10 messages)
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]

                print(f"\n🤖 Marty: {response}")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Try again or type 'quit' to exit")


async def main():
    """Main entry point."""
    chat = MartyChat()
    await chat.start_chat()


if __name__ == "__main__":
    asyncio.run(main())
