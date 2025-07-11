"""Hardcover API GraphQL client for book recommendations."""

import asyncio
import logging
import time
from typing import Any

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportError, TransportQueryError

from config import config

# Configure logging
logger = logging.getLogger(__name__)


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


class HardcoverClient:
    """Asynchronous GraphQL client for Hardcover API."""

    def __init__(
        self,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        rate_limit_max_requests: int = 60,
    ):
        """Initialize the Hardcover client.

        Args:
            retry_count: Number of retries for failed requests (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
            rate_limit_max_requests: Max requests per minute (default: 60)
        """
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
                    logger.debug(
                        f"Executing query (attempt {attempt + 1}/{self._retry_count})"
                    )
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

    async def introspect_schema(self) -> dict[str, Any]:
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

    async def get_current_user(self) -> dict[str, Any]:
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

    async def search_books(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
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

        logger.info(f"Searching books: query={query}, limit={limit}")
        result = await self._execute_with_retry(search_query, variables)
        search_result = result.get("search", {})

        # If we got book IDs, fetch detailed info for them
        book_ids = search_result.get("ids", [])
        if book_ids:
            # Limit to requested number of books
            book_ids = book_ids[:limit]
            return await self.get_books_by_ids(book_ids)

        return []

    async def search_books_raw(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Search for books and return raw search results (includes the huge results blob)."""
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

        logger.info(f"Searching books (raw): query={query}, limit={limit}")
        result = await self._execute_with_retry(search_query, variables)
        return result.get("search", {})

    async def get_book_by_id(self, book_id: int) -> dict[str, Any] | None:
        """Get detailed book information by ID."""
        query = gql(
            """
            query GetBook($id: Int!) {
                books_by_pk(id: $id) {
                    id
                    title
                    description
                    isbn13
                    pages
                    release_year
                    cached_contributors
                    cached_tags
                    slug
                    image {
                        url
                    }
                    contributions {
                        author {
                            id
                            name
                        }
                    }
                    book_category {
                        id
                        name
                    }
                }
            }
        """
        )

        variables = {"id": book_id}

        logger.info(f"Getting book details: id={book_id}")
        result = await self._execute_with_retry(query, variables)
        return result.get("books_by_pk")

    async def get_user_recommendations(self, limit: int = 10) -> list[dict[str, Any]]:
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

    async def get_trending_books(
        self,
        from_date: str = "2025-04-01",
        to_date: str = "2025-07-01",
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get currently trending/popular books for a date range."""
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

    async def get_books_by_ids(self, book_ids: list[int]) -> list[dict[str, Any]]:
        """Get detailed book information for multiple books by their IDs."""
        query = gql(
            """
            query GetBooksByIds($ids: [Int!]!) {
                books(where: {id: {_in: $ids}}) {
                    id
                    title
                    description
                    isbn13
                    pages
                    release_year
                    cached_contributors
                    cached_tags
                    slug
                    image {
                        url
                    }
                    contributions {
                        author {
                            id
                            name
                        }
                    }
                    book_category {
                        id
                        name
                    }
                }
            }
        """
        )

        variables = {"ids": book_ids}

        logger.info(
            f"Getting books by IDs: ids={book_ids[:5]}{'...' if len(book_ids) > 5 else ''}"
        )
        result = await self._execute_with_retry(query, variables)
        return result.get("books", [])

    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close_async()
            self._client = None


# Convenience function for testing
async def test_hardcover_connection():
    """Test the Hardcover API connection."""
    client = HardcoverClient()

    try:
        # Test authentication
        user = await client.get_current_user()
        print(f"Connected as user: {user}")

        # Test schema introspection
        print("Fetching GraphQL schema...")
        schema = await client.introspect_schema()

        # Extract available query types
        query_type = schema.get("__schema", {}).get("queryType", {})
        print(f"Query type: {query_type.get('name')}")

        # Find all available root queries
        types = schema.get("__schema", {}).get("types", [])
        query_fields = []

        for type_def in types:
            if type_def.get("name") == query_type.get("name"):
                fields = type_def.get("fields", [])
                query_fields = [field.get("name") for field in fields]
                break

        print(f"Available root queries: {query_fields}")

        return schema

    except Exception as e:
        print(f"Error connecting to Hardcover API: {e}")
        return None

    finally:
        await client.close()


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_hardcover_connection())
