import logging
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

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


def create_book_embed(book_data: dict[str, Any], is_rpg: bool = False) -> discord.Embed:
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
        color=0xFFA227,
    )

    # Add book cover image if available (using set_image for larger size)
    image_url = (
        book_data.get("image", {}).get("url") if book_data.get("image") else None
    )
    if image_url:
        embed.set_image(url=image_url)

    # Add book details as fields
    rating = book_data.get("rating")
    ratings_count = book_data.get("ratings_count")

    # Separate rating and ratings count for cleaner display
    if rating:
        embed.add_field(name="Rating", value=f"⭐ {rating:.1f}", inline=True)

    pages = book_data.get("pages")
    if pages and pages > 0:
        embed.add_field(name="Pages", value=str(pages), inline=True)

    release_year = book_data.get("release_year")
    if release_year:
        embed.add_field(name="Year", value=str(release_year), inline=True)

    if ratings_count:
        embed.add_field(name="Readers", value=f"{ratings_count:,}", inline=True)

    # Add genre/mood tags if available
    cached_tags = book_data.get("cached_tags")
    if cached_tags and isinstance(cached_tags, dict):
        # Extract genres (top 3)
        genres = cached_tags.get("Genre", [])
        if genres and isinstance(genres, list):
            top_genres = [
                genre.get("tag", "") for genre in genres[:3] if genre.get("tag")
            ]
            if top_genres:
                embed.add_field(
                    name="Genres", value=" • ".join(top_genres), inline=True
                )

        # Extract moods (top 2)
        moods = cached_tags.get("Mood", [])
        if moods and isinstance(moods, list):
            top_moods = [mood.get("tag", "") for mood in moods[:2] if mood.get("tag")]
            if top_moods:
                embed.add_field(name="Mood", value=" • ".join(top_moods), inline=True)

    # Add series/compilation info if available
    compilation = book_data.get("compilation")
    subtitle = book_data.get("subtitle", "")
    if compilation and str(compilation).lower() not in ["none", "null", "false"]:
        embed.add_field(name="Series", value=str(compilation), inline=True)
    elif subtitle and "series" in subtitle.lower():
        # If subtitle mentions series (like "The Murderbot Diaries"), show it
        embed.add_field(name="Series", value=subtitle, inline=True)

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

    # Always add Dungeon Books store search first
    title_for_search = quote(title)
    dungeonbooks_url = f"https://www.dungeonbooks.com/s/search?q={title_for_search}"
    links.append(f"[Check Our Store]({dungeonbooks_url})")

    # Add Hardcover reviews link
    if slug:
        hardcover_url = f"https://hardcover.app/books/{slug}?referrer_id=148"
        links.append(f"[Details]({hardcover_url})")
        logger.debug(f"Added Hardcover link for '{title}': {hardcover_url}")
    elif title:
        # Fallback to search URL when slug is missing
        search_query = title.replace(" ", "+").lower()
        hardcover_url = f"https://hardcover.app/search?q={search_query}?referrer_id=148"
        links.append(f"[Details]({hardcover_url})")
        logger.debug(f"Added Hardcover search fallback for '{title}': {hardcover_url}")
    else:
        logger.warning("No slug or title found - cannot create Hardcover link")

    # Only add bookshop link for books (not RPGs)
    if bookshop_link and not is_rpg:
        links.append(f"[Buy Online]({bookshop_link})")

    if links:
        embed.add_field(name="Links", value=" • ".join(links), inline=False)

    # Add footer
    embed.set_footer(text="Dungeon Books • Powered by Hardcover API")

    return embed


async def search_book_shared(hardcover_tool, query: str):
    """Shared logic for book search commands."""
    if not query.strip():
        return None, "need a book title or something to search for"

    try:
        result = await hardcover_tool.execute(
            action="search_books", query=query, limit=1
        )

        if not result.success or not result.data:
            return (
                None,
                f"hmm that book might exist in another dimension, lemme double check '{query}'",
            )

        book_data = result.data[0]
        embed = create_book_embed(book_data)
        return embed, None

    except Exception as e:
        logger.error(f"Error in shared book search: {e}")
        return None, "search spell malfunctioned, try that again"


async def get_recent_releases_shared(hardcover_tool):
    """Shared logic for recent releases commands."""
    try:
        result = await hardcover_tool.execute(action="get_recent_releases", limit=10)

        if not result.success or not result.data:
            return None, "couldn't find any recent releases right now, try again later"

        books = result.data
        if not books:
            return None, "no recent releases found, that's weird"

        # Create simple list embed
        embed = discord.Embed(
            title="✨ Recent Releases",
            description="Fresh books from the last month, sorted by popularity",
            color=0xFFA227,
        )

        # Create numbered list
        book_list = ""
        for i, book in enumerate(books, 1):
            title = book.get("title", "Unknown Title")
            author = book.get("author", "Unknown Author")

            book_list += f"{i}. **{title}** by *{author}*\n"

        embed.description = book_list
        embed.set_footer(text="Dungeon Books • Powered by Hardcover API")

        return embed, None

    except Exception as e:
        logger.error(f"Error in shared recent releases: {e}")
        return None, "recent releases spell malfunctioned, try that again"


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

        # Check if this is a message in a thread created by the bot
        is_bot_thread = (
            hasattr(message.channel, "owner") and message.channel.owner == self.user
        )

        # Only respond to @ mentions, DMs, or messages in bot's threads
        if not (
            self.user.mentioned_in(message)
            or isinstance(message.channel, discord.DMChannel)
            or is_bot_thread
        ):
            return

        # Check if user has any assigned role (skip for DMs and dev environment)
        if not isinstance(message.channel, discord.DMChannel):
            # Skip role check in development environment
            if os.getenv("ENV") != "dev":
                # Allow anyone with any role (excluding @everyone)
                user_roles = [
                    role for role in message.author.roles if role.name != "@everyone"
                ]

                if not user_roles:
                    await message.reply(
                        "sorry, i'm only available to members with assigned roles right now. ping `@nachi` if you need access."
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

        # If we're in a thread created by the bot, use parent channel for conversation lookup
        is_bot_thread = (
            hasattr(message.channel, "owner") and message.channel.owner == self.user
        )

        # For conversation lookup, use parent channel if in bot thread
        conversation_channel_id = channel_id
        if is_bot_thread and hasattr(message.channel, "parent"):
            conversation_channel_id = str(message.channel.parent.id)

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
                    # Use parent channel ID for thread conversations to maintain history
                    conversation = await get_active_conversation(
                        db,
                        user_id,
                        platform="discord",
                        channel_id=conversation_channel_id,
                    )
                    if not conversation:
                        conversation_data = ConversationCreate(
                            customer_id=customer.id,
                            discord_user_id=user_id,
                            discord_channel_id=conversation_channel_id,
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
                    ai_response, tool_results = await generate_ai_response(
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
                    # Check if we need to create a thread for this conversation
                    is_bot_thread = (
                        hasattr(message.channel, "owner")
                        and message.channel.owner == self.user
                    )

                    if not is_bot_thread and not isinstance(
                        message.channel, discord.DMChannel
                    ):
                        # Create a thread for the conversation
                        try:
                            thread = await message.create_thread(name="Chat with Marty")
                            await thread.send(ai_response)

                            # Handle any tool results (like thread renaming)
                            await self._handle_tool_results(
                                tool_results, thread, username
                            )

                            logger.info(
                                f"Created thread and sent Discord response to {username}"
                            )
                        except Exception as thread_error:
                            logger.error(f"Failed to create thread: {thread_error}")
                            # Fallback to regular reply
                            await message.reply(ai_response)

                            # Handle tool results in fallback case too
                            try:
                                await self._handle_tool_results(
                                    tool_results, message.channel, username
                                )
                            except Exception as tool_error:
                                logger.warning(
                                    f"Failed to handle tool results in fallback: {tool_error}"
                                )

                            logger.info(
                                f"Sent Discord response to {username} (fallback)"
                            )
                    else:
                        # Already in thread or DM, reply normally
                        await message.reply(ai_response)

                        # Handle tool results for existing threads and DMs
                        if is_bot_thread or isinstance(
                            message.channel, discord.DMChannel
                        ):
                            await self._handle_tool_results(
                                tool_results, message.channel, username
                            )

                        logger.info(f"Sent Discord response to {username}")

        except Exception as e:
            logger.error(f"Error processing Discord message from {username}: {e}")
            # Send error message in Marty's voice
            error_message = "sorry my brain's lagging, give me a moment"
            try:
                # Use same thread logic for error messages
                is_bot_thread = (
                    hasattr(message.channel, "owner")
                    and message.channel.owner == self.user
                )

                if not is_bot_thread and not isinstance(
                    message.channel, discord.DMChannel
                ):
                    # Try to create thread for error message too
                    try:
                        thread = await message.create_thread(name="Chat with Marty")
                        await thread.send(error_message)
                    except Exception:
                        # Fallback to regular reply
                        await message.reply(error_message)
                else:
                    await message.reply(error_message)
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")

    async def _handle_tool_results(
        self, tool_results: list[dict], thread, username: str
    ) -> None:
        """Handle tool results from AI response."""
        for tool_result in tool_results:
            tool_name = tool_result.get("tool_name")
            result = tool_result.get("result")

            if tool_name == "rename_thread" and result and result.success:
                try:
                    thread_name = result.data.get("thread_name")
                    if thread_name and hasattr(thread, "edit"):
                        await thread.edit(name=thread_name)
                        logger.info(f"Renamed thread to '{thread_name}' for {username}")
                except Exception as e:
                    logger.warning(f"Failed to rename thread: {e}")

            elif tool_name == "hardcover_api" and result and result.success:
                try:
                    await self._send_book_embeds(tool_result, thread, username)
                except Exception as e:
                    logger.warning(f"Failed to send book embed: {e}")

    async def _send_book_embeds(self, tool_result: dict, thread, username: str) -> None:
        """Send book embeds for Hardcover API results."""
        result = tool_result.get("result")
        tool_input = tool_result.get("tool_input", {})
        action = tool_input.get("action", "")

        if not result or not result.success or not result.data:
            return

        # Handle different Hardcover actions that return book data
        books_data = []

        if action in ["search_books", "get_books_by_ids"]:
            # These return a list of books
            books_data = result.data if isinstance(result.data, list) else []
        elif action == "get_book_by_id":
            # This returns a single book
            if isinstance(result.data, dict):
                books_data = [result.data]

        # Send embeds for books (limit to 3 to avoid spam)
        for book_data in books_data[:3]:
            if book_data and isinstance(book_data, dict):
                try:
                    embed = create_book_embed(book_data)
                    await thread.send(embed=embed)
                    logger.info(
                        f"Sent book embed for '{book_data.get('title', 'Unknown')}' to {username}"
                    )
                except Exception as e:
                    logger.error(f"Error creating book embed: {e}")
                    logger.debug(
                        f"Book data that caused error: {book_data.get('cached_tags')} (type: {type(book_data.get('cached_tags'))})"
                    )
                    # Continue without the embed rather than failing completely


def create_bot() -> MartyBot:
    """Create and return a MartyBot instance."""
    bot = MartyBot()

    @bot.command()
    async def book(ctx: commands.Context, *, query: str) -> None:
        """Search for a book and display its information using Hardcover API."""
        if not bot.hardcover:
            await ctx.send("search spell's broken rn, try again later")
            return

        async with ctx.typing():
            embed, error_msg = await search_book_shared(bot.hardcover, query)

            if error_msg:
                await ctx.send(error_msg)
                return

            await ctx.send(embed=embed)
            logger.info("Sent book embed via !book command")

    @bot.command()
    async def recent(ctx: commands.Context) -> None:
        """Show recent book releases using Hardcover API."""
        if not bot.hardcover:
            await ctx.send("search spell's broken rn, try again later")
            return

        async with ctx.typing():
            embed, error_msg = await get_recent_releases_shared(bot.hardcover)

            if error_msg:
                await ctx.send(error_msg)
                return

            await ctx.send(embed=embed)
            logger.info("Sent recent releases via !recent command")

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

        await interaction.response.defer()

        embed, error_msg = await search_book_shared(bot.hardcover, query)

        if error_msg:
            await interaction.followup.send(error_msg)
            return

        await interaction.followup.send(embed=embed)
        logger.info("Sent book embed via /book slash command")

    @bot.tree.command(
        name="recent", description="Show the 10 most recent book releases in a list"
    )
    async def recent_slash(interaction: discord.Interaction) -> None:
        """Slash command to show recent book releases in a grid format."""
        if not bot.hardcover:
            await interaction.response.send_message(
                "search spell's broken rn, try again later", ephemeral=True
            )
            return

        await interaction.response.defer()

        embed, error_msg = await get_recent_releases_shared(bot.hardcover)

        if error_msg:
            await interaction.followup.send(error_msg)
            return

        await interaction.followup.send(embed=embed)
        logger.info("Sent recent releases via /recent slash command")

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
