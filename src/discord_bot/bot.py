import logging
import os
from datetime import UTC, datetime
from typing import Any

import discord  # type: ignore
from discord import app_commands  # type: ignore
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
from ..tools.external.hardcover import HardcoverTool

logger = logging.getLogger(__name__)


def create_book_embed(book_data: dict[str, Any]) -> discord.Embed:
    """Create a rich Discord embed for a book using Hardcover API data."""
    title = book_data.get("title", "Unknown Title")
    author = book_data.get("author") or book_data.get(
        "cached_contributors", "Unknown Author"
    )
    description = book_data.get("description", "")

    # Create the embed with book title and author
    embed = discord.Embed(
        title=title,
        description=f"by {author}",
        color=0x8B4513,  # Saddle brown color for bookstore theme
    )

    # Add book cover image if available
    image_url = (
        book_data.get("image", {}).get("url") if book_data.get("image") else None
    )
    if image_url:
        embed.set_thumbnail(url=image_url)

    # Add book details as fields
    rating = book_data.get("rating")
    if rating:
        embed.add_field(name="Rating", value=f"⭐ {rating:.1f}", inline=True)

    pages = book_data.get("pages")
    if pages:
        embed.add_field(name="Pages", value=str(pages), inline=True)

    release_year = book_data.get("release_year")
    if release_year:
        embed.add_field(name="Year", value=str(release_year), inline=True)

    ratings_count = book_data.get("ratings_count")
    if ratings_count:
        embed.add_field(name="Ratings", value=f"{ratings_count:,} readers", inline=True)

    # Add description (truncated if too long)
    if description:
        # Discord embed description limit is 4096 characters
        truncated_desc = (
            description[:500] + "..." if len(description) > 500 else description
        )
        embed.add_field(name="Description", value=truncated_desc, inline=False)

    # Add links
    bookshop_link = book_data.get("bookshop_link")
    slug = book_data.get("slug")

    links = []
    if slug:
        hardcover_url = f"https://hardcover.app/books/{slug}"
        links.append(f"[Hardcover]({hardcover_url})")
    if bookshop_link:
        links.append(f"[Buy Book]({bookshop_link})")

    if links:
        embed.add_field(name="Links", value=" • ".join(links), inline=False)

    # Add footer
    embed.set_footer(text="📚 Dungeon Books • Powered by Hardcover API")

    return embed


class MartyBot(commands.Bot):
    """Discord bot for Marty, the AI bookstore assistant."""

    def __init__(self) -> None:
        intents = discord.Intents.default()  # type: ignore
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        # Initialize Hardcover API tool
        try:
            self.hardcover = HardcoverTool()
        except Exception as e:
            logger.error(f"Failed to initialize Hardcover API: {e}")
            self.hardcover = None

    async def on_ready(self) -> None:
        """Called when the bot has finished logging in and setting up."""
        logger.info(f"{self.user} has connected to Discord!")

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")

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

        # Check if user has Staff role (skip for DMs and dev environment)
        if not isinstance(message.channel, discord.DMChannel):
            # Skip staff role check in development environment
            if os.getenv("ENV") != "dev":
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

                    # Get recent conversation history FIRST (before saving new message)
                    recent_messages = await get_conversation_messages(
                        db, conversation.id, limit=6
                    )

                    # Convert to ConversationMessage format (reverse for chronological order)
                    conversation_history = []
                    for msg in reversed(
                        recent_messages
                    ):  # Reverse to get chronological order
                        conversation_history.append(
                            ConversationMessage(
                                role="user"
                                if msg.direction == "inbound"
                                else "assistant",
                                content=msg.content,
                                timestamp=msg.timestamp,
                            )
                        )

                    # Save the incoming message AFTER getting history
                    incoming_message = MessageCreate(
                        conversation_id=conversation.id,
                        direction="inbound",
                        content=user_message,
                        status="received",
                    )
                    await add_message(db, incoming_message)

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
    bot = MartyBot()

    @bot.command()
    async def book(ctx: commands.Context, *, query: str) -> None:
        """Search for a book and display its information using Hardcover API."""
        if not bot.hardcover:
            await ctx.send("search spell's broken rn, try again later")
            return

        if not query.strip():
            await ctx.send("need a book title or something to search for")
            return

        try:
            async with ctx.typing():
                # Search for the book using Hardcover API
                result = await bot.hardcover.execute(
                    action="search_books", query=query, limit=1
                )

                if not result.success or not result.data:
                    await ctx.send(
                        f"hmm that book might exist in another dimension, lemme double check '{query}'"
                    )
                    return

                book_data = result.data[0]  # Get the first book result
                embed = create_book_embed(book_data)
                await ctx.send(embed=embed)

                logger.info(
                    f"Sent book embed for '{book_data.get('title', 'Unknown')}' in response to !book command"
                )

        except Exception as e:
            logger.error(f"Error in book command: {e}")
            await ctx.send("search spell malfunctioned, try that again")

    @bot.tree.command(
        name="book", description="Search for a book and get detailed information"
    )
    @app_commands.describe(query="Book title or author to search for")
    async def book_slash(interaction: discord.Interaction, query: str) -> None:
        """Slash command version of book search."""
        if not bot.hardcover:
            await interaction.response.send_message(
                "search spell's broken rn, try again later", ephemeral=True
            )
            return

        if not query.strip():
            await interaction.response.send_message(
                "need a book title or something to search for", ephemeral=True
            )
            return

        try:
            # Defer the response since API calls might take time
            await interaction.response.defer()

            # Search for the book using Hardcover API
            result = await bot.hardcover.execute(
                action="search_books", query=query, limit=1
            )

            if not result.success or not result.data:
                await interaction.followup.send(
                    f"hmm that book might exist in another dimension, lemme double check '{query}'"
                )
                return

            book_data = result.data[0]  # Get the first book result
            embed = create_book_embed(book_data)
            await interaction.followup.send(embed=embed)

            logger.info(
                f"Sent book embed for '{book_data.get('title', 'Unknown')}' in response to /book slash command"
            )

        except Exception as e:
            logger.error(f"Error in book slash command: {e}")
            try:
                await interaction.followup.send(
                    "search spell malfunctioned, try that again"
                )
            except Exception as e:
                # If followup fails, try editing the original response
                logger.error(f"Failed to send error message: {e}")
                await interaction.edit_original_response(
                    content="search spell malfunctioned, try that again"
                )

    return bot


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
