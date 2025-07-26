"""
Hardcover API Tool - Provides access to Hardcover book data API.

This tool wraps the Hardcover API GraphQL client to provide book search,
book details, user recommendations, and trending books functionality.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

import structlog
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportError, TransportQueryError

from src.config import config
from src.tools.base import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


# Note: extract_isbn_13_from_editions function removed as direct ISBN links may be international editions


# Note: extract_and_replace_bookshop_link function removed as the 'links' field is always empty


def generate_bookshop_search_link(
    title: str, author: str | None = None, our_affiliate_id: str = "108216"
) -> str:
    """Generate a bookshop.org search link with our affiliate ID using just the title."""
    # Just use title for better search results - authors often hurt search accuracy
    search_query = title.replace(" ", "+")
    return f"https://bookshop.org/search?keywords={search_query}&affiliate={our_affiliate_id}"


class HardcoverAPIError(Exception):
    """Base exception for Hardcover API errors."""

    pass


class HardcoverAuthError(HardcoverAPIError):
    """Authentication/Authorization errors."""

    pass


class HardcoverRateLimitError(HardcoverAPIError):
    """Rate limit exceeded (60 requests per minute)."""

    pass


class HardcoverTimeoutError(HardcoverAPIError):
    """Query timeout exceeded (30 seconds max)."""

    pass


class RateLimiter:
    """Simple rate limiter for API calls (60 requests per minute)."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to respect rate limits."""
        async with self._lock:
            now = time.monotonic()
            # Remove old requests outside the window
            self.requests = [
                req_time
                for req_time in self.requests
                if now - req_time < self.window_seconds
            ]

            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = self.requests[0]
                wait_time = self.window_seconds - (now - oldest_request)
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached, waiting {wait_time:.1f} seconds"
                    )
                    await asyncio.sleep(wait_time + 0.1)  # Add small buffer
                    # Recursive call to re-check
                    return await self.acquire()

            # Add current request
            self.requests.append(now)


class HardcoverTool(BaseTool):
    """
    Hardcover API Tool - Provides access to Hardcover book data API.

    This tool wraps the Hardcover API GraphQL client to provide:
    - Book search functionality
    - Book details retrieval
    - User recommendations
    - Trending books
    - Schema introspection
    """

    def __init__(
        self,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        rate_limit_max_requests: int = 60,
    ):
        super().__init__()
        if not config.HARDCOVER_API_TOKEN:
            raise HardcoverAuthError("Hardcover API token not configured")

        self.api_url = config.HARDCOVER_API_URL
        self.headers = config.get_hardcover_headers()
        self._client: Client | None = None
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_max_requests, window_seconds=60
        )
        self._retry_count = retry_count
        self._retry_delay = retry_delay

    @property
    def name(self) -> str:
        return "hardcover_api"

    @property
    def description(self) -> str:
        return (
            "Gets book details, ratings, and purchase links via Hardcover API. "
            "Use when user asks about a specific book's rating, where to buy, or for Hardcover links. "
            "Supports book search, book details, purchase link generation, and Hardcover.app link generation."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": [
                    "search_books",
                    "search_books_raw",
                    "get_book_by_id",
                    "get_books_by_ids",
                    "get_user_recommendations",
                    "get_trending_books",
                    "get_current_user",
                    "introspect_schema",
                    "generate_hardcover_link",
                ],
            },
            "query": {
                "type": "string",
                "description": "Search query (required for search_books actions). Include both title and author for better results, e.g. 'The Scar China Miéville'",
            },
            "book_id": {
                "type": "integer",
                "description": "Book ID (required for get_book_by_id action)",
            },
            "book_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of book IDs (required for get_books_by_ids action)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5 for search, 10 for others)",
            },
            "offset": {
                "type": "integer",
                "description": "Number of results to skip (for pagination, default: 0)",
            },
            "from_date": {
                "type": "string",
                "description": "Start date in YYYY-MM-DD format (for trending books)",
            },
            "to_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format (for trending books)",
            },
        }

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        action = kwargs.get("action")

        if not action:
            return False

        if action in ["search_books", "search_books_raw"]:
            return bool(kwargs.get("query"))
        elif action == "generate_hardcover_link":
            return bool(kwargs.get("query"))
        elif action == "get_book_by_id":
            return bool(kwargs.get("book_id"))
        elif action == "get_books_by_ids":
            book_ids = kwargs.get("book_ids")
            return bool(book_ids and isinstance(book_ids, list) and len(book_ids) > 0)

        # Other actions don't require additional parameters
        return True

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the Hardcover API action."""
        if not self.validate_input(**kwargs):
            return ToolResult(
                success=False,
                data=None,
                error="Invalid parameters. Check action and required fields.",
            )

        try:
            action = kwargs["action"]

            if action == "search_books":
                query = kwargs["query"]
                limit = kwargs.get("limit", 5)
                data = await self._search_books(query, limit)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "query": query, "limit": limit},
                )

            elif action == "search_books_raw":
                query = kwargs["query"]
                limit = kwargs.get("limit", 5)
                data = await self._search_books_raw(query, limit)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "query": query, "limit": limit},
                )

            elif action == "get_book_by_id":
                book_id = kwargs["book_id"]
                data = await self._get_book_by_id(book_id)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "book_id": book_id},
                )

            elif action == "get_books_by_ids":
                book_ids = kwargs["book_ids"]
                data = await self._get_books_by_ids(book_ids)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "book_count": len(book_ids)},
                )

            elif action == "get_user_recommendations":
                limit = kwargs.get("limit", 10)
                data = await self._get_user_recommendations(limit)
                return ToolResult(
                    success=True, data=data, metadata={"action": action, "limit": limit}
                )

            elif action == "get_trending_books":
                from_date = kwargs.get("from_date")
                to_date = kwargs.get("to_date")
                limit = kwargs.get("limit", 10)
                offset = kwargs.get("offset", 0)
                data = await self._get_trending_books(from_date, to_date, limit, offset)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={
                        "action": action,
                        "from_date": from_date,
                        "to_date": to_date,
                        "limit": limit,
                    },
                )

            elif action == "get_current_user":
                data = await self._get_current_user()
                return ToolResult(success=True, data=data, metadata={"action": action})

            elif action == "introspect_schema":
                data = await self._introspect_schema()
                return ToolResult(success=True, data=data, metadata={"action": action})

            elif action == "generate_hardcover_link":
                query = kwargs["query"]
                data = await self._generate_hardcover_link(query)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "query": query},
                )

            else:
                return ToolResult(
                    success=False, data=None, error=f"Unknown action: {action}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={
                    "error_type": type(e).__name__,
                    "action": kwargs.get("action"),
                },
            )

    async def _get_client(self) -> Client:
        """Get or create the GraphQL client."""
        if self._client is None:
            transport = AIOHTTPTransport(
                url=self.api_url,
                headers=self.headers,
                ssl=True,  # Enable SSL certificate verification for security
                timeout=30,  # 30 second timeout as per API docs
            )
            self._client = Client(transport=transport, fetch_schema_from_transport=True)
        return self._client

    async def _execute_with_retry(self, query, variables=None):
        """Execute a GraphQL query with rate limiting and retry logic."""
        # Apply rate limiting
        await self.rate_limiter.acquire()

        last_error = None
        for attempt in range(self._retry_count):
            try:
                client = await self._get_client()
                async with client as session:
                    # Minimal logging to reduce noise
                    result = await session.execute(query, variable_values=variables)
                    return result

            except TransportQueryError as e:
                # GraphQL errors (like field not found)
                logger.error(f"GraphQL query error: {e}")
                raise HardcoverAPIError(f"GraphQL query error: {e}") from e

            except TransportError as e:
                # Transport errors (network, timeout, etc)
                if "401" in str(e) or "403" in str(e):
                    raise HardcoverAuthError(f"Authentication failed: {e}") from e
                elif "429" in str(e):
                    # Rate limit hit despite our limiter - wait longer
                    wait_time = (
                        self._retry_delay * (attempt + 1) * 10
                    )  # Progressive backoff for rate limits
                    logger.warning(f"Rate limit hit, waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                    last_error = HardcoverRateLimitError(f"Rate limit exceeded: {e}")
                elif "timeout" in str(e).lower():
                    raise HardcoverTimeoutError(
                        f"Query timeout (30s limit): {e}"
                    ) from e
                else:
                    last_error = e
                    if attempt < self._retry_count - 1:
                        delay = self._retry_delay * (2**attempt)  # Exponential backoff
                        logger.warning(f"Request failed, retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                last_error = e
                if attempt < self._retry_count - 1:
                    delay = self._retry_delay * (2**attempt)
                    await asyncio.sleep(delay)

        # All retries failed
        if isinstance(last_error, HardcoverAPIError):
            raise last_error
        else:
            raise HardcoverAPIError(
                f"Failed after {self._retry_count} attempts: {last_error}"
            )

    async def _search_books(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for books using Hardcover's search API (optimized for production)."""
        search_query = gql(
            """
            query SearchBooks($query: String!, $limit: Int!) {
                search(
                    query: $query,
                    query_type: "books",
                    per_page: $limit,
                    page: 1,
                    sort: "activities_count:desc"
                ) {
                    error
                    ids
                    query
                }
            }
        """
        )

        variables = {"query": query, "limit": limit}

        logger.debug(f"Searching books: query={query}, limit={limit}")
        result = await self._execute_with_retry(search_query, variables)
        search_result = result.get("search", {})

        # If we got book IDs, fetch detailed info for them
        book_ids = search_result.get("ids", [])
        if book_ids:
            # Limit to requested number of books
            book_ids = book_ids[:limit]
            return await self._get_books_by_ids(book_ids)

        return []

    async def _search_books_raw(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Search for books and return raw search results."""
        search_query = gql(
            """
            query SearchBooksRaw($query: String!, $limit: Int!) {
                search(
                    query: $query,
                    query_type: "books",
                    per_page: $limit,
                    page: 1,
                    sort: "activities_count:desc"
                ) {
                    error
                    ids
                    query
                    results
                }
            }
        """
        )

        variables = {"query": query, "limit": limit}

        logger.debug(f"Searching books (raw): query={query}, limit={limit}")
        result = await self._execute_with_retry(search_query, variables)
        return result.get("search", {})

    async def _get_book_by_id(self, book_id: int) -> dict[str, Any] | None:
        """Get detailed book information by ID."""
        query = gql(
            """
            query GetBook($id: Int!) {
                books_by_pk(id: $id) {
                    id
                    title
                    subtitle
                    description
                    pages
                    release_year
                    rating
                    cached_contributors
                    cached_tags
                    slug
                    compilation
                    links
                    image {
                        url
                    }
                    contributions {
                        author {
                            id
                            name
                        }
                    }
                    ratings_count
                    reviews_count
                    users_count
                    editions {
                        id
                        isbn_10
                        isbn_13
                    }
                }
            }
        """
        )

        variables = {"id": book_id}

        logger.debug(f"Getting book details: id={book_id}")
        result = await self._execute_with_retry(query, variables)
        book = result.get("books_by_pk")

        # Add purchase link and author information
        if book:
            # Extract author from contributions
            contributions = book.get("contributions", [])
            authors = []
            for contribution in contributions:
                if isinstance(contribution, dict) and "author" in contribution:
                    author = contribution["author"]
                    if isinstance(author, dict) and "name" in author:
                        authors.append(author["name"])

            # Set author field (use first author or cached_contributors as fallback)
            if authors:
                book["author"] = authors[0] if len(authors) == 1 else ", ".join(authors)
            elif book.get("cached_contributors"):
                book["author"] = book["cached_contributors"]

            # Use search links as primary approach since direct ISBN links may be international editions
            if book.get("title"):
                book["bookshop_link"] = generate_bookshop_search_link(
                    book["title"], book.get("author")
                )
                logger.debug(
                    f"Generated search link for book: {book.get('title')} by {book.get('author', 'Unknown')}"
                )

        return book

    async def _get_books_by_ids(self, book_ids: list[int]) -> list[dict[str, Any]]:
        """Get detailed book information for multiple books by their IDs."""
        query = gql(
            """
            query GetBooksByIds($ids: [Int!]!) {
                books(where: {id: {_in: $ids}}) {
                    id
                    title
                    subtitle
                    description
                    pages
                    release_year
                    rating
                    cached_contributors
                    cached_tags
                    slug
                    compilation
                    links
                    image {
                        url
                    }
                    contributions {
                        author {
                            id
                            name
                        }
                    }
                    ratings_count
                    reviews_count
                    users_count
                    editions {
                        id
                        isbn_10
                        isbn_13
                    }
                }
            }
        """
        )

        variables = {"ids": book_ids}

        logger.debug(
            f"Getting books by IDs: ids={book_ids[:5]}{'...' if len(book_ids) > 5 else ''}"
        )
        result = await self._execute_with_retry(query, variables)
        books = result.get("books", [])

        # Enhance books with purchase links and author information
        for book in books:
            # Extract author from contributions
            contributions = book.get("contributions", [])
            authors = []
            for contribution in contributions:
                if isinstance(contribution, dict) and "author" in contribution:
                    author = contribution["author"]
                    if isinstance(author, dict) and "name" in author:
                        authors.append(author["name"])

            # Set author field (use first author or cached_contributors as fallback)
            if authors:
                book["author"] = authors[0] if len(authors) == 1 else ", ".join(authors)
            elif book.get("cached_contributors"):
                book["author"] = book["cached_contributors"]

            # Use search links as primary approach since direct ISBN links may be international editions
            title = book.get("title", "")
            if title:
                book["bookshop_link"] = generate_bookshop_search_link(
                    title, book.get("author")
                )
                logger.debug(
                    f"Generated search link for book: {title} by {book.get('author', 'Unknown')}"
                )

        return books

    async def _get_user_recommendations(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get personalized book recommendations for the authenticated user."""
        query = gql(
            """
            query GetRecommendations($limit: Int!) {
                recommendations(limit: $limit) {
                    id
                    book {
                        id
                        title
                        description
                        cached_contributors
                        cached_tags
                        slug
                        image {
                            url
                        }
                    }
                }
            }
        """
        )

        variables = {"limit": limit}

        logger.info(f"Getting user recommendations: limit={limit}")
        result = await self._execute_with_retry(query, variables)
        return result.get("recommendations", [])

    async def _get_trending_books(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get currently trending/popular books for a date range."""
        # Use relative dates if not provided
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if to_date is None:
            to_date = datetime.now().strftime("%Y-%m-%d")

        query = gql(
            """
            query GetTrendingBooks($from: String!, $to: String!, $limit: Int!, $offset: Int!) {
                books_trending(from: $from, to: $to, limit: $limit, offset: $offset) {
                    error
                    ids
                }
            }
        """
        )

        variables = {"from": from_date, "to": to_date, "limit": limit, "offset": offset}

        logger.info(
            f"Getting trending books: from={from_date}, to={to_date}, limit={limit}"
        )
        result = await self._execute_with_retry(query, variables)
        return result.get("books_trending", {})

    async def _get_current_user(self) -> dict[str, Any]:
        """Get current user information (test query)."""
        query = gql(
            """
            query {
                me {
                    id
                    username
                    email
                }
            }
        """
        )

        logger.info("Getting current user information")
        return await self._execute_with_retry(query)

    async def _introspect_schema(self) -> dict[str, Any]:
        """Get the GraphQL schema for exploration."""
        introspection_query = gql(
            """
            query IntrospectionQuery {
                __schema {
                    queryType { name }
                    mutationType { name }
                    subscriptionType { name }
                    types {
                        ...FullType
                    }
                }
            }

            fragment FullType on __Type {
                kind
                name
                description
                fields(includeDeprecated: true) {
                    name
                    description
                    args {
                        ...InputValue
                    }
                    type {
                        ...TypeRef
                    }
                    isDeprecated
                    deprecationReason
                }
                inputFields {
                    ...InputValue
                }
                interfaces {
                    ...TypeRef
                }
                enumValues(includeDeprecated: true) {
                    name
                    description
                    isDeprecated
                    deprecationReason
                }
                possibleTypes {
                    ...TypeRef
                }
            }

            fragment InputValue on __InputValue {
                name
                description
                type { ...TypeRef }
                defaultValue
            }

            fragment TypeRef on __Type {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                        ofType {
                                            kind
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        )

        logger.info("Introspecting GraphQL schema")
        return await self._execute_with_retry(introspection_query)

    async def _generate_hardcover_link(self, query: str) -> dict[str, Any] | None:
        """Generate a Hardcover.app link for a book by searching for it."""
        try:
            # Search for the book to get its slug
            books = await self._search_books(query, limit=1)

            if not books:
                return {
                    "error": f"No books found for query: {query}",
                    "hardcover_link": None,
                    "title": None,
                    "author": None,
                }

            book = books[0]
            slug = book.get("slug")

            if not slug:
                return {
                    "error": f"No slug found for book: {book.get('title', 'Unknown')}",
                    "hardcover_link": None,
                    "title": book.get("title"),
                    "author": book.get("author"),
                }

            hardcover_link = f"https://hardcover.app/books/{slug}"

            logger.debug(f"Generated Hardcover link: {hardcover_link}")

            return {
                "hardcover_link": hardcover_link,
                "title": book.get("title"),
                "author": book.get("author"),
                "slug": slug,
            }

        except Exception as e:
            logger.error(f"Error generating Hardcover link for query '{query}': {e}")
            return {
                "error": f"Failed to generate link: {str(e)}",
                "hardcover_link": None,
                "title": None,
                "author": None,
            }

    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close_async()
            self._client = None
