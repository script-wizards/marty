"""
BookEnricher Tool - Enriches AI responses with validated book data.

This tool processes AI responses to extract book mentions, validates them
against the Hardcover API, and stores verified books in the database.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from database import (
    AsyncSessionLocal,
    Book,
    BookCreate,
    init_database,
)
from tools.base import BaseTool, ToolResult
from tools.external.hardcover import HardcoverAPIError, HardcoverTool

logger = logging.getLogger(__name__)


@dataclass
class BookMention:
    """Represents a book mentioned in AI response."""

    title: str
    author: str | None = None
    isbn: str | None = None
    confidence: float = 0.0
    context: str = ""
    message_id: str = ""
    validated: bool = False
    hardcover_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnrichedResponse:
    """AI response enriched with validated book data."""

    original_response: str
    book_mentions: list[BookMention]
    validated_books: list[dict[str, Any]]
    enrichment_metadata: dict[str, Any] = field(default_factory=dict)


class BookEnricherTool(BaseTool):
    """
    Enriches AI responses with validated book data.

    This tool processes AI responses to:
    1. Extract book mentions using Claude AI
    2. Validate books against Hardcover API
    3. Store validated books in database
    4. Prepare data for RCS cards and recommendations
    """

    def __init__(self, hardcover_tool: HardcoverTool | None = None):
        super().__init__()
        self.hardcover_tool = hardcover_tool or HardcoverTool()
        # Simple but effective ISBN pattern for ISBN-10 and ISBN-13
        self.isbn_pattern = re.compile(
            r"(?:ISBN[-:\s]*)?((?:97[89][-\s]?)?(?:\d[-\s]?){9,12}\d)", re.IGNORECASE
        )

    @property
    def name(self) -> str:
        return "book_enricher"

    @property
    def description(self) -> str:
        return (
            "Enriches AI responses with validated book data. "
            "Extracts book mentions from AI responses, validates them against "
            "the Hardcover API, and stores verified books in the database."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "ai_response": {
                "type": "string",
                "description": "The AI-generated response text to enrich",
            },
            "conversation_id": {
                "type": "string",
                "description": "ID of the conversation",
            },
            "message_id": {"type": "string", "description": "ID of the message"},
        }

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        required_fields = ["ai_response", "conversation_id", "message_id"]
        return all(field in kwargs and kwargs[field] for field in required_fields)

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the book enrichment tool."""
        if not self.validate_input(**kwargs):
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameters: ai_response, conversation_id, message_id",
            )

        try:
            ai_response = kwargs["ai_response"]
            conversation_id = kwargs["conversation_id"]
            message_id = kwargs["message_id"]

            enriched_response = await self._enrich_response(
                ai_response, conversation_id, message_id
            )

            return ToolResult(
                success=True,
                data=enriched_response,
                metadata={
                    "books_found": len(enriched_response.book_mentions),
                    "books_validated": len(enriched_response.validated_books),
                    "processed_at": datetime.now(UTC).isoformat(),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"error_type": type(e).__name__},
            )

    async def _enrich_response(
        self, ai_response: str, conversation_id: str, message_id: str
    ) -> EnrichedResponse:
        """
        Enrich an AI response with validated book data.

        Args:
            ai_response: The AI-generated response text
            conversation_id: ID of the conversation
            message_id: ID of the message

        Returns:
            EnrichedResponse with validated book data
        """
        self.logger.info(f"Enriching response for conversation {conversation_id}")

        # Extract book mentions from AI response
        book_mentions = await self._extract_book_mentions(ai_response, message_id)

        # Validate books against Hardcover API
        validated_books = []
        for mention in book_mentions:
            try:
                validated_book = await self._validate_book(mention)
                if validated_book:
                    mention.validated = True
                    mention.hardcover_id = str(validated_book.get("id"))
                    mention.metadata = validated_book
                    validated_books.append(validated_book)

                    # Store in database
                    await self._store_book(validated_book)

            except Exception as e:
                self.logger.warning(f"Failed to validate book '{mention.title}': {e}")
                # Keep unvalidated mention for context

        return EnrichedResponse(
            original_response=ai_response,
            book_mentions=book_mentions,
            validated_books=validated_books,
            enrichment_metadata={
                "conversation_id": conversation_id,
                "message_id": message_id,
                "processed_at": datetime.now(UTC).isoformat(),
                "mentions_found": len(book_mentions),
                "books_validated": len(validated_books),
            },
        )

    async def _extract_book_mentions(
        self, text: str, message_id: str
    ) -> list[BookMention]:
        """Extract book mentions from AI response text."""
        mentions = []

        # Quick ISBN detection
        isbn_matches = self.isbn_pattern.findall(text)
        for isbn in isbn_matches:
            mentions.append(
                BookMention(
                    title=isbn.strip(),
                    isbn=isbn.strip(),
                    confidence=0.9,
                    context=text,
                    message_id=message_id,
                )
            )

        # Use AI for natural language book extraction
        try:
            from ai_client import generate_ai_response

            prompt = f"""Extract book titles and authors from this AI response about books.
Return ONLY a JSON array of objects with this structure:
[{{"title": "Book Title", "author": "Author Name or null", "confidence": 0.0-1.0}}]

AI Response: "{text}"

Guidelines:
- Only extract actual book titles, not just the word "book"
- High confidence (0.8+) for explicit mentions, lower for implicit ones
- Include novels, series, textbooks, any specific book titles
- Return empty array [] if no books mentioned
- Be conservative - only extract clear book references
"""

            response = await generate_ai_response(prompt, [])

            # Parse JSON response
            try:
                book_data = json.loads(response.strip())
                if not isinstance(book_data, list):
                    return mentions  # Return the ISBN mentions we found

                # Extend existing mentions (don't create new list)
                for book in book_data:
                    if isinstance(book, dict) and "title" in book:
                        mentions.append(
                            BookMention(
                                title=book.get("title", "").strip(),
                                author=book.get("author"),
                                confidence=float(book.get("confidence", 0.5)),
                                context=text,
                                message_id=message_id,
                            )
                        )

                return mentions

            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse AI response as JSON: {response}")
                return mentions  # Return the ISBN mentions we found

        except Exception as e:
            self.logger.error(f"AI book extraction failed: {e}")
            raise

    async def _validate_book(self, mention: BookMention) -> dict[str, Any] | None:
        """Validate a book mention against Hardcover API."""
        try:
            # Search for the book
            search_query = f"{mention.title}"
            if mention.author:
                search_query += f" {mention.author}"

            # Use the HardcoverTool to search for books
            result = await self.hardcover_tool.execute(
                action="search_books", query=search_query, limit=3
            )

            if not result.success:
                self.logger.error(f"Failed to search books: {result.error}")
                return None

            books = result.data

            if not books:
                self.logger.debug(f"No books found for: {search_query}")
                return None

            # Find the best match
            best_match = self._find_best_match(mention, books)
            if best_match:
                self.logger.info(f"Validated book: {best_match.get('title')}")
                return best_match

            return None

        except HardcoverAPIError as e:
            self.logger.error(f"Hardcover API error for '{mention.title}': {e}")
            return None

    def _find_best_match(
        self, mention: BookMention, books: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Find the best matching book from search results."""
        if not books:
            return None

        # Simple matching logic - can be enhanced
        for book in books:
            book_title = book.get("title", "").lower()
            mention_title = mention.title.lower()

            # Exact match
            if book_title == mention_title:
                return book

            # Partial match (title contains mention or vice versa)
            if mention_title in book_title or book_title in mention_title:
                # Check author if available
                if mention.author:
                    authors = book.get("authors", [])
                    if authors:
                        book_author = authors[0].get("name", "").lower()
                        if mention.author.lower() in book_author:
                            return book
                else:
                    return book

        # If no good match found, return the first book as fallback
        return books[0]

    async def _store_book(self, book_data: dict[str, Any]) -> None:
        """Store validated book in database."""
        try:
            init_database()
            assert AsyncSessionLocal is not None

            async with AsyncSessionLocal() as session:
                # Check if book already exists
                from sqlalchemy import select

                hardcover_id = str(book_data.get("id"))
                result = await session.execute(
                    select(Book).where(Book.hardcover_id == hardcover_id)
                )
                existing_book = result.scalars().first()

                if existing_book:
                    self.logger.debug(f"Book already exists: {existing_book.title}")
                    return

                # Create new book
                book_create = BookCreate(
                    title=book_data.get("title", ""),
                    author=book_data.get("authors", [{}])[0].get("name")
                    if book_data.get("authors")
                    else None,
                    description=book_data.get("description"),
                    hardcover_id=hardcover_id,
                    isbn=book_data.get("isbn"),
                    publisher=book_data.get("publisher"),
                    page_count=book_data.get("pages"),
                    price=None,  # Not available from Hardcover API
                    genre=None,  # Not available from Hardcover API
                    format=None,  # Not available from Hardcover API
                )

                db_book = Book(**book_create.model_dump())
                session.add(db_book)
                await session.commit()

                self.logger.info(f"Stored book: {db_book.title}")

        except Exception as e:
            self.logger.error(f"Failed to store book: {e}")
            raise

    async def close(self) -> None:
        """Close any resources."""
        if self.hardcover_tool:
            await self.hardcover_tool.close()
