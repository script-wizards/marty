"""
Working tests for Hardcover API integration.
Tests only the methods that actually exist in HardcoverClient.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import AsyncGenerator, Dict, Any
import json

from hardcover_client import HardcoverClient


# Mock responses matching actual API structure
MOCK_USER_RESPONSE = {
    "me": [{"id": 148, "username": "testuser", "email": "test@example.com"}]
}

MOCK_SCHEMA_RESPONSE = {
    "__schema": {
        "queryType": {"name": "Query"},
        "types": [
            {
                "name": "Book",
                "kind": "OBJECT",
                "fields": [
                    {"name": "id", "type": {"name": "ID"}},
                    {"name": "title", "type": {"name": "String"}},
                    {"name": "author", "type": {"name": "String"}},
                ],
            }
        ],
    }
}

MOCK_SEARCH_RESPONSE = {
    "search": {"error": None, "ids": [123, 456], "query": "Python programming"}
}

MOCK_BOOKS_RESPONSE = {
    "books": [
        {
            "id": 123,
            "title": "The Python Handbook",
            "description": "A comprehensive guide to Python programming",
            "isbn13": "9781234567890",
            "pages": 450,
            "release_year": 2023,
            "cached_contributors": "John Pythonista",
            "cached_tags": "programming, python",
            "slug": "python-handbook",
            "image": {"url": "https://example.com/cover.jpg"},
            "contributions": [{"author": {"id": 1, "name": "John Pythonista"}}],
            "book_category": {"id": 1, "name": "Programming"},
        }
    ]
}

MOCK_BOOK_RESPONSE = {
    "books_by_pk": {
        "id": 123,
        "title": "The Python Handbook",
        "description": "A comprehensive guide to Python programming",
        "isbn13": "9781234567890",
        "pages": 450,
        "release_year": 2023,
        "cached_contributors": "John Pythonista",
        "cached_tags": "programming, python",
        "slug": "python-handbook",
        "image": {"url": "https://example.com/cover.jpg"},
        "contributions": [{"author": {"id": 1, "name": "John Pythonista"}}],
        "book_category": {"id": 1, "name": "Programming"},
    }
}

MOCK_RECOMMENDATIONS_RESPONSE = {
    "recommendations": [
        {
            "id": 1,
            "book": {
                "id": 123,
                "title": "The Python Handbook",
                "description": "A comprehensive guide to Python programming",
                "cached_contributors": "John Pythonista",
                "cached_tags": "programming, python",
                "slug": "python-handbook",
                "image": {"url": "https://example.com/cover.jpg"},
            },
        }
    ]
}

MOCK_TRENDING_RESPONSE = {"books_trending": {"error": None, "ids": [123, 456, 789]}}


@pytest_asyncio.fixture
async def hardcover_client():
    """Create a HardcoverClient instance for testing."""
    with patch("hardcover_client.config.HARDCOVER_API_TOKEN", "Bearer test_token"):
        client = HardcoverClient()
        yield client
        await client.close()


@pytest_asyncio.fixture
async def mock_gql_session():
    """Create a mock GraphQL session that properly handles async context."""
    mock_session = AsyncMock()
    mock_client = AsyncMock()

    # Mock the context manager behavior
    mock_client.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("hardcover_client.Client") as mock_client_class:
        mock_client_class.return_value = mock_client
        yield mock_session


class TestHardcoverClientBasics:
    """Test basic HardcoverClient functionality."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, hardcover_client: HardcoverClient):
        """Test client initializes with correct configuration."""
        assert hardcover_client.api_url is not None
        assert hardcover_client.headers is not None
        assert hardcover_client._client is None  # Should be lazy-loaded

    @pytest.mark.asyncio
    async def test_get_current_user(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test getting current user information."""
        mock_gql_session.execute.return_value = MOCK_USER_RESPONSE

        result = await hardcover_client.get_current_user()

        assert result == MOCK_USER_RESPONSE
        assert result["me"][0]["id"] == 148
        assert result["me"][0]["username"] == "testuser"
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_introspect_schema(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test GraphQL schema introspection."""
        mock_gql_session.execute.return_value = MOCK_SCHEMA_RESPONSE

        schema = await hardcover_client.introspect_schema()

        assert schema == MOCK_SCHEMA_RESPONSE
        assert "__schema" in schema
        assert "types" in schema["__schema"]
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_books(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test searching for books."""
        # Mock search response and books response
        mock_gql_session.execute.side_effect = [
            MOCK_SEARCH_RESPONSE,  # First call to search
            MOCK_BOOKS_RESPONSE,  # Second call to get_books_by_ids
        ]

        books = await hardcover_client.search_books("Python", limit=5)

        assert len(books) == 1
        assert books[0]["id"] == 123
        assert books[0]["title"] == "The Python Handbook"
        assert mock_gql_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_search_books_raw(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test raw search for books."""
        mock_gql_session.execute.return_value = MOCK_SEARCH_RESPONSE

        result = await hardcover_client.search_books_raw("Python", limit=5)

        assert result == MOCK_SEARCH_RESPONSE["search"]
        assert result["ids"] == [123, 456]
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_book_by_id(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test getting book by ID."""
        mock_gql_session.execute.return_value = MOCK_BOOK_RESPONSE

        book = await hardcover_client.get_book_by_id(123)

        assert book == MOCK_BOOK_RESPONSE["books_by_pk"]
        assert book["id"] == 123
        assert book["title"] == "The Python Handbook"
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_recommendations(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test getting user recommendations."""
        mock_gql_session.execute.return_value = MOCK_RECOMMENDATIONS_RESPONSE

        recommendations = await hardcover_client.get_user_recommendations(limit=5)

        assert len(recommendations) == 1
        assert recommendations[0]["id"] == 1
        assert recommendations[0]["book"]["id"] == 123
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_trending_books(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test getting trending books."""
        mock_gql_session.execute.return_value = MOCK_TRENDING_RESPONSE

        trending = await hardcover_client.get_trending_books(limit=5)

        assert trending == MOCK_TRENDING_RESPONSE["books_trending"]
        assert trending["ids"] == [123, 456, 789]
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_books_by_ids(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test getting books by IDs."""
        mock_gql_session.execute.return_value = MOCK_BOOKS_RESPONSE

        books = await hardcover_client.get_books_by_ids([123, 456])

        assert len(books) == 1
        assert books[0]["id"] == 123
        assert books[0]["title"] == "The Python Handbook"
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_books_empty_results(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test handling of empty search results."""
        mock_gql_session.execute.return_value = {"search": {"error": None, "ids": []}}

        books = await hardcover_client.search_books("NonexistentTopic")

        assert len(books) == 0
        mock_gql_session.execute.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_gql_exception_handling(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test handling of GraphQL exceptions."""
        mock_gql_session.execute.side_effect = Exception("GraphQL error")

        # These should handle errors gracefully
        with pytest.raises(Exception):
            await hardcover_client.get_current_user()

        with pytest.raises(Exception):
            await hardcover_client.search_books("test")

    @pytest.mark.asyncio
    async def test_missing_token_error(self):
        """Test error when API token is missing."""
        with patch("hardcover_client.config.HARDCOVER_API_TOKEN", None):
            # Should raise ValueError during initialization
            with pytest.raises(ValueError, match="Hardcover API token not configured"):
                HardcoverClient()

    @pytest.mark.asyncio
    async def test_malformed_response_handling(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test handling of malformed API responses."""
        mock_gql_session.execute.return_value = {"invalid": "format"}

        books = await hardcover_client.search_books("test")

        # Should return empty list when search key is missing
        assert books == []


class TestConfigurationHandling:
    """Test configuration and environment handling."""

    @pytest.mark.asyncio
    async def test_custom_api_url(self):
        """Test using custom API URL."""
        custom_url = "https://custom.hardcover.app/graphql"
        with patch("hardcover_client.config.HARDCOVER_API_URL", custom_url):
            with patch(
                "hardcover_client.config.HARDCOVER_API_TOKEN", "Bearer test_token"
            ):
                client = HardcoverClient()
                assert client.api_url == custom_url

    @pytest.mark.asyncio
    async def test_headers_configuration(self):
        """Test that headers are properly configured."""
        with patch("hardcover_client.config.HARDCOVER_API_TOKEN", "Bearer test_token"):
            with patch("hardcover_client.config.get_hardcover_headers") as mock_headers:
                mock_headers.return_value = {
                    "Authorization": "Bearer test_token",
                    "Content-Type": "application/json",
                }
                client = HardcoverClient()
                assert "Authorization" in client.headers
                assert client.headers["Authorization"] == "Bearer test_token"
                assert "Content-Type" in client.headers


class TestIntegrationScenarios:
    """Test integration scenarios for the SMS bot."""

    @pytest.mark.asyncio
    async def test_book_verification_workflow(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test book verification workflow for Claude AI recommendations."""
        # Mock search and books responses
        mock_gql_session.execute.side_effect = [
            MOCK_SEARCH_RESPONSE,
            MOCK_BOOKS_RESPONSE,
        ]

        # Simulate Claude recommending books
        claude_recommendations = ["The Python Handbook"]

        verified_books = []
        for book_title in claude_recommendations:
            books = await hardcover_client.search_books(book_title)
            if books:
                verified_books.append(books[0])

        assert len(verified_books) == 1
        assert verified_books[0]["id"] == 123
        assert verified_books[0]["title"] == "The Python Handbook"

    @pytest.mark.asyncio
    async def test_trending_books_for_recommendations(
        self, hardcover_client: HardcoverClient, mock_gql_session
    ):
        """Test getting trending books for recommendations."""
        mock_gql_session.execute.return_value = MOCK_TRENDING_RESPONSE

        trending = await hardcover_client.get_trending_books(
            from_date="2025-01-01", to_date="2025-01-31", limit=10
        )

        assert trending["ids"] == [123, 456, 789]
        assert trending["error"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
