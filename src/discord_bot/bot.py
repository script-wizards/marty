import logging
import os
from datetime import UTC, datetime
from typing import Any

import discord  # type: ignore
from discord.ext import commands  # type: ignore

from ..ai_client import ConversationMessage, generate_ai_response
from ..database import (
    ConversationCreate,
    CustomerCreate,
    MessageCreate,
    add_message,
    create_conversation,
    create_customer,
    get_active_conversation,
    get_conversation_messages,
    get_customer_by_discord_id,
    get_db_session,
)

logger = logging.getLogger(__name__)


class MartyBot(commands.Bot):
    """Discord bot for Marty, the AI bookstore assistant."""

    def __init__(self) -> None:
        intents = discord.Intents.default()  # type: ignore
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self) -> None:
        """Called when the bot has finished logging in and setting up."""
        logger.info(f"{self.user} has connected to Discord!")

    async def on_message(self, message: Any) -> None:
        """Handle incoming Discord messages."""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Ignore messages that start with command prefix
        if message.content.startswith(self.command_prefix):
            await self.process_commands(message)
            return

        # Only respond to @ mentions or DMs
        if not (
            self.user.mentioned_in(message)
            or isinstance(message.channel, discord.DMChannel)
        ):
            return

        # Check if user has Staff role (skip for DMs)
        if not isinstance(message.channel, discord.DMChannel):
            staff_role = discord.utils.get(message.guild.roles, name="Staff")
            if not staff_role or staff_role not in message.author.roles:
                await message.reply(
                    "sorry, i'm only available to staff right now. ping `@nachi` if you need access."
                )
                return

        # Process the message through Marty's AI system
        await self.process_marty_message(message)

    async def process_marty_message(self, message: Any) -> None:
        """Process a Discord message through Marty's conversation system."""
        user_id = str(message.author.id)
        username = message.author.display_name
        user_message = message.content
        channel_id = str(message.channel.id)
        guild_id = str(message.guild.id) if message.guild else None

        logger.info(
            f"Processing Discord message from {username} ({user_id}): {user_message}"
        )

        try:
            async with message.channel.typing():
                async with get_db_session() as db:
                    # Get or create customer
                    customer = await get_customer_by_discord_id(db, user_id)
                    if not customer:
                        customer_data = CustomerCreate(
                            discord_user_id=user_id,
                            discord_username=username,
                            platform="discord",
                        )
                        customer = await create_customer(db, customer_data)
                        logger.info(f"Created new customer for Discord user {username}")

                    # Get or create active conversation
                    conversation = await get_active_conversation(
                        db, user_id, platform="discord", channel_id=channel_id
                    )
                    if not conversation:
                        conversation_data = ConversationCreate(
                            customer_id=customer.id,
                            discord_user_id=user_id,
                            discord_channel_id=channel_id,
                            discord_guild_id=guild_id,
                            platform="discord",
                            status="active",
                        )
                        conversation = await create_conversation(db, conversation_data)
                        logger.info(
                            f"Created new conversation for Discord user {username}"
                        )

                    # Save the incoming message FIRST
                    incoming_message = MessageCreate(
                        conversation_id=conversation.id,
                        direction="inbound",
                        content=user_message,
                        status="received",
                    )
                    await add_message(db, incoming_message)

                    # Get recent conversation history AFTER saving the current message
                    recent_messages = await get_conversation_messages(
                        db, conversation.id, limit=6
                    )

                    # Convert to ConversationMessage format (exclude the current message)
                    conversation_history = []
                    for msg in recent_messages[
                        1:
                    ]:  # Exclude the current message (first in desc order)
                        conversation_history.append(
                            ConversationMessage(
                                role="user"
                                if msg.direction == "inbound"
                                else "assistant",
                                content=msg.content,
                                timestamp=msg.timestamp,
                            )
                        )

                    logger.debug(
                        f"Conversation history: {len(conversation_history)} messages"
                    )
                    for i, msg in enumerate(
                        conversation_history[-3:]
                    ):  # Show last 3 messages
                        logger.debug(f"  {i}: {msg.role}: {msg.content[:50]}...")

                    # Prepare customer context
                    customer_context = {
                        "customer_id": customer.id,
                        "discord_user_id": user_id,
                        "discord_username": username,
                        "name": customer.name or username,
                        "current_time": datetime.now(UTC).strftime("%I:%M %p"),
                        "current_date": datetime.now(UTC).strftime("%B %d, %Y"),
                        "current_day": datetime.now(UTC).strftime("%A"),
                        "platform": "discord",
                    }

                    # Generate AI response
                    ai_response = await generate_ai_response(
                        user_message=user_message,
                        conversation_history=conversation_history,
                        customer_context=customer_context,
                        platform="discord",
                    )

                    # Save the response message to database
                    response_message = MessageCreate(
                        conversation_id=conversation.id,
                        direction="outbound",
                        content=ai_response,
                        status="sent",
                    )
                    await add_message(db, response_message)

                    # Send response to Discord
                    await message.reply(ai_response)
                    logger.info(f"Sent Discord response to {username}")

        except Exception as e:
            logger.error(f"Error processing Discord message from {username}: {e}")
            # Send error message in Marty's voice
            error_message = "sorry my brain's lagging, give me a moment"
            try:
                await message.reply(error_message)
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")


def create_bot() -> MartyBot:
    """Create and return a MartyBot instance."""
    return MartyBot()


async def run_bot() -> None:
    """Run the Discord bot."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable is required")

    bot = create_bot()
    await bot.start(token)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bot())
