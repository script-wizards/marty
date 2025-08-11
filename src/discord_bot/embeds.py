"""Discord embed utilities for book displays."""

import logging
from typing import Any
from urllib.parse import quote

import discord  # type: ignore

logger = logging.getLogger(__name__)

# Minimum number of ratings required to display a book's rating
MIN_RATING_THRESHOLD = 5


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
    image_data = book_data.get("image")
    image_url = None

    # Enhanced logging and image URL extraction
    if image_data:
        logger.debug(
            f"Image data for '{title}': {image_data} (type: {type(image_data)})"
        )
        if isinstance(image_data, dict):
            image_url = image_data.get("url")
        elif isinstance(image_data, str):
            image_url = image_data
            logger.debug(f"Image data is string: {image_url}")
    else:
        logger.debug(f"No image data found for '{title}'")

    if image_url:
        logger.debug(f"Setting cover image for '{title}': {image_url}")
        embed.set_image(url=image_url)
    else:
        logger.warning(
            f"No valid image URL found for '{title}' - image_data: {image_data}"
        )

    # Add book details as fields
    rating = book_data.get("rating")
    ratings_count = book_data.get("ratings_count")

    # Only show rating if there are enough ratings to make it meaningful
    if rating and ratings_count and ratings_count >= MIN_RATING_THRESHOLD:
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


def create_recent_releases_embed(books: list[dict[str, Any]]) -> discord.Embed:
    """Create a Discord embed for recent book releases."""
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

    return embed
