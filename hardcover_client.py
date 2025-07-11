"""Hardcover API GraphQL client for book recommendations."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from config import config


class HardcoverClient:
    """Asynchronous GraphQL client for Hardcover API."""

    def __init__(self):
        """Initialize the Hardcover client."""
        if not config.HARDCOVER_API_TOKEN:
            raise ValueError("Hardcover API token not configured")

        self.api_url = config.HARDCOVER_API_URL
        self.headers = config.get_hardcover_headers()
        self._client: Optional[Client] = None

    async def _get_client(self) -> Client:
        """Get or create the GraphQL client."""
        if self._client is None:
            transport = AIOHTTPTransport(
                url=self.api_url,
                headers=self.headers,
                ssl=True,  # Enable SSL certificate verification for security
            )
            self._client = Client(transport=transport, fetch_schema_from_transport=True)
        return self._client

    async def introspect_schema(self) -> Dict[str, Any]:
        """Get the GraphQL schema for exploration."""
        introspection_query = gql("""
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
        """)

        client = await self._get_client()
        async with client as session:
            result = await session.execute(introspection_query)
            return result

    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user information (test query)."""
        query = gql("""
            query {
                me {
                    id
                    username
                    email
                }
            }
        """)

        client = await self._get_client()
        async with client as session:
            result = await session.execute(query)
            return result

    async def search_books(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for books using Hardcover's search API (optimized for production)."""
        search_query = gql("""
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
        """)

        variables = {"query": query, "limit": limit}

        client = await self._get_client()
        async with client as session:
            result = await session.execute(search_query, variable_values=variables)
            search_result = result.get("search", {})

            # If we got book IDs, fetch detailed info for them
            book_ids = search_result.get("ids", [])
            if book_ids:
                # Limit to requested number of books
                book_ids = book_ids[:limit]
                return await self.get_books_by_ids(book_ids)

            return []

    async def search_books_raw(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search for books and return raw search results (includes the huge results blob)."""
        search_query = gql("""
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
        """)

        variables = {"query": query, "limit": limit}

        client = await self._get_client()
        async with client as session:
            result = await session.execute(search_query, variable_values=variables)
            return result.get("search", {})

    async def get_book_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed book information by ID."""
        query = gql("""
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
        """)

        variables = {"id": book_id}

        client = await self._get_client()
        async with client as session:
            result = await session.execute(query, variable_values=variables)
            return result.get("books_by_pk")

    async def get_user_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get personalized book recommendations for the authenticated user."""
        query = gql("""
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
        """)

        variables = {"limit": limit}

        client = await self._get_client()
        async with client as session:
            result = await session.execute(query, variable_values=variables)
            return result.get("recommendations", [])

    async def get_trending_books(
        self,
        from_date: str = "2025-04-01",
        to_date: str = "2025-07-01",
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get currently trending/popular books for a date range."""
        query = gql("""
            query GetTrendingBooks($from: String!, $to: String!, $limit: Int!, $offset: Int!) {
                books_trending(from: $from, to: $to, limit: $limit, offset: $offset) {
                    error
                    ids
                }
            }
        """)

        variables = {"from": from_date, "to": to_date, "limit": limit, "offset": offset}

        client = await self._get_client()
        async with client as session:
            result = await session.execute(query, variable_values=variables)
            return result.get("books_trending", {})

    async def get_books_by_ids(self, book_ids: List[int]) -> List[Dict[str, Any]]:
        """Get detailed book information for multiple books by their IDs."""
        query = gql("""
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
        """)

        variables = {"ids": book_ids}

        client = await self._get_client()
        async with client as session:
            result = await session.execute(query, variable_values=variables)
            return result.get("books", [])

    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close_async()


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
