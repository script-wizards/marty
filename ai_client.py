import os
from datetime import datetime
from pathlib import Path

from anthropic import AsyncAnthropic
from pydantic import BaseModel

# Initialize the Claude client
client = AsyncAnthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)


class ConversationMessage(BaseModel):
    """A message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


def load_system_prompt(prompt_file: str = "prompts/marty_system_prompt.md") -> str:
    """Load the system prompt from a file."""
    try:
        prompt_path = Path(__file__).parent / prompt_file
        return prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        print(f"Warning: Prompt file {prompt_file} not found. Using fallback prompt.")
        return "You are Marty, a helpful AI assistant who works at Dungeon Books. Help customers find great books!"


# Load Marty's character prompt from file
MARTY_SYSTEM_PROMPT = load_system_prompt()


async def generate_ai_response(
    user_message: str,
    conversation_history: list[ConversationMessage],
    customer_context: dict | None = None,
) -> str:
    """
    Generate an AI response using Claude.

    Args:
        user_message: The current message from the user
        conversation_history: Previous messages in the conversation
        customer_context: Optional context about the customer

    Returns:
        The AI-generated response
    """
    try:
        # Build the conversation history for Claude
        messages = []

        # Add conversation history
        for msg in conversation_history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        # Add customer context to the system prompt if available
        system_prompt = MARTY_SYSTEM_PROMPT
        if customer_context:
            context_info = []
            if customer_context.get("first_name"):
                context_info.append(f"Customer name: {customer_context['first_name']}")
            if customer_context.get("phone"):
                context_info.append(f"Phone: {customer_context['phone']}")

            if context_info:
                system_prompt += f"\n\nCustomer Context:\n{' | '.join(context_info)}"

        # Generate response with Claude
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            temperature=0.7,
            system=system_prompt,
            messages=messages,
        )

        # Extract the response text
        if response.content and len(response.content) > 0:
            content_block = response.content[0]
            response_text = getattr(content_block, "text", str(content_block))
        else:
            response_text = "I'm having trouble generating a response right now."

        return response_text

    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "Sorry, I'm having trouble thinking right now. Can you try again? 🤔"
