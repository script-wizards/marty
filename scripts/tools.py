"""
Example Chat Flow - Demonstrates the new architecture with separated concerns.

ConversationManagerTool: Handles conversation state only
BookEnricherTool: Processes AI responses for book mentions and validation
"""

import asyncio
import logging
from typing import Any

from ai_client import ConversationMessage, generate_ai_response
from tools.book.enricher import BookEnricherTool
from tools.conversation.manager import ConversationManagerTool

logger = logging.getLogger(__name__)


async def process_chat_message(phone: str, user_message: str) -> dict[str, Any]:
    """
    Process a chat message using the new separated architecture.

    Flow:
    1. Add user message to conversation
    2. Generate AI response
    3. Enrich AI response with validated book data
    4. Add AI response to conversation
    5. Return enriched response to user
    """

    # Step 1: Get conversation manager tool and add user message
    conv_tool = ConversationManagerTool()

    # Add user message to conversation
    result = await conv_tool.execute(
        action="add_message", phone=phone, content=user_message, direction="inbound"
    )

    if not result.success:
        raise Exception(f"Failed to add user message: {result.error}")

    conversation = result.data

    # Step 2: Prepare conversation history for AI
    ai_history = []
    for msg in conversation.messages[-5:]:  # Last 5 messages for context
        role = "user" if msg.direction == "inbound" else "assistant"
        ai_history.append(
            ConversationMessage(role=role, content=msg.content, timestamp=msg.timestamp)
        )

    # Step 3: Generate AI response
    customer_context = {
        "phone": phone,
        "customer_id": conversation.customer_id,
        "current_time": "2025-01-12 16:30:00 PST",
        "current_date": "2025-01-12",
        "current_day": "Sunday",
    }

    ai_response = await generate_ai_response(
        user_message,
        ai_history[:-1],  # Exclude the current user message from history
        customer_context,
    )

    # Step 4: Enrich AI response with book data
    enricher = BookEnricherTool()
    try:
        result = await enricher.execute(
            ai_response=ai_response,
            conversation_id=conversation.conversation_id,
            message_id=f"ai_msg_{conversation.conversation_id}_{len(conversation.messages)}",
        )

        if result.success:
            enriched = result.data
            # Step 5: Add AI response to conversation
            final_result = await conv_tool.execute(
                action="add_message",
                phone=phone,
                content=enriched.original_response,
                direction="outbound",
                metadata={
                    "books_mentioned": len(enriched.book_mentions),
                    "books_validated": len(enriched.validated_books),
                    "enrichment_metadata": enriched.enrichment_metadata,
                },
            )

            if not final_result.success:
                raise Exception(f"Failed to add AI response: {final_result.error}")

            final_conversation = final_result.data

            # Step 6: Return enriched response
            return {
                "response": enriched.original_response,
                "conversation_id": conversation.conversation_id,
                "books_mentioned": [
                    {
                        "title": book.title,
                        "author": book.author,
                        "validated": book.validated,
                        "hardcover_id": book.hardcover_id,
                        "confidence": book.confidence,
                    }
                    for book in enriched.book_mentions
                ],
                "validated_books": enriched.validated_books,
                "message_count": len(final_conversation.messages),
            }
        else:
            # Tool execution failed
            logger.error(f"BookEnricherTool failed: {result.error}")
            raise Exception(f"Book enrichment failed: {result.error}")

    except Exception as e:
        logger.error(f"Error enriching response: {e}")

        # Fallback: Just add AI response without enrichment
        final_result = await conv_tool.execute(
            action="add_message", phone=phone, content=ai_response, direction="outbound"
        )

        if not final_result.success:
            raise Exception(
                f"Failed to add fallback AI response: {final_result.error}"
            ) from e

        final_conversation = final_result.data

        return {
            "response": ai_response,
            "conversation_id": conversation.conversation_id,
            "books_mentioned": [],
            "validated_books": [],
            "message_count": len(final_conversation.messages),
            "error": "Book enrichment failed",
        }

    finally:
        await enricher.close()
        await conv_tool.close()


async def example_conversation():
    """Example conversation demonstrating the new architecture."""

    phone = "+1234567890"

    print("🤖 Marty Chat Example - New Architecture")
    print("=" * 50)

    try:
        # User asks for book recommendation
        print("\n👤 User: I'm looking for a good fantasy book to read")

        result1 = await process_chat_message(
            phone, "I'm looking for a good fantasy book to read"
        )

        print(f"🤖 Marty: {result1['response']}")
        print(f"📚 Books mentioned: {len(result1['books_mentioned'])}")
        print(f"✅ Books validated: {len(result1['validated_books'])}")

        if result1["validated_books"]:
            for book in result1["validated_books"]:
                print(
                    f"   - {book['title']} by {book.get('cached_contributors', 'Unknown')}"
                )

        # User responds about the recommendation
        print("\n👤 User: Tell me more about The Name of the Wind")

        result2 = await process_chat_message(
            phone, "Tell me more about The Name of the Wind"
        )

        print(f"🤖 Marty: {result2['response']}")
        print(f"📚 Books mentioned: {len(result2['books_mentioned'])}")
        print(f"✅ Books validated: {len(result2['validated_books'])}")

        # Show conversation summary
        conv_tool = ConversationManagerTool()
        summary_result = await conv_tool.execute(action="summary", phone=phone)

        if summary_result.success:
            summary = summary_result.data
            print("\n📊 Conversation Summary:")
            print(f"   - Total messages: {summary['message_count']}")
            print(f"   - Conversation ID: {summary['conversation_id']}")
            print(f"   - Last activity: {summary['last_activity']}")
        else:
            print(f"\n❌ Failed to get conversation summary: {summary_result.error}")

        await conv_tool.close()

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Run example
    asyncio.run(example_conversation())
