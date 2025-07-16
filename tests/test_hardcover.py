"""
Tests for HardcoverTool - Hardcover API integration tool.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tools.external.hardcover import HardcoverTool

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
async def hardcover_tool():
    """Create a HardcoverTool instance for testing with minimal delays."""
    with patch(
        "tools.external.hardcover.config.HARDCOVER_API_TOKEN", "Bearer test_token"
    ):
        with patch(
            "tools.external.hardcover.config.get_hardcover_headers"
        ) as mock_headers:
            mock_headers.return_value = {
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json",
            }
            # Use minimal delays for testing
            tool = HardcoverTool(
                retry_count=3, retry_delay=0.01, rate_limit_max_requests=100
            )
            yield tool
            await tool.close()


@pytest_asyncio.fixture
async def mock_gql_session():
    """Create a mock GraphQL session that properly handles async context."""
    mock_session = AsyncMock()
    mock_client = AsyncMock()

    # Mock the context manager behavior
    mock_client.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("tools.external.hardcover.Client") as mock_client_class:
        mock_client_class.return_value = mock_client
        yield mock_session


class TestHardcoverToolBasics:
    """Test basic HardcoverTool functionality."""

    @pytest.mark.asyncio
    async def test_tool_initialization(self, hardcover_tool: HardcoverTool):
        """Test tool initializes with correct configuration."""
        assert hardcover_tool.api_url is not None
        assert hardcover_tool.headers is not None
        assert hardcover_tool._client is None  # Should be lazy-loaded

    def test_tool_properties(self, hardcover_tool: HardcoverTool):
        """Test tool properties for BaseTool interface."""
        assert hardcover_tool.name == "hardcover_api"
        assert "Hardcover book data API" in hardcover_tool.description

        parameters = hardcover_tool.parameters
        assert "action" in parameters
        assert "query" in parameters
        assert "book_id" in parameters
        assert "book_ids" in parameters

    def test_validate_input(self, hardcover_tool: HardcoverTool):
        """Test input validation."""
        # Valid inputs
        assert (
            hardcover_tool.validate_input(action="search_books", query="python") is True
        )
        assert (
            hardcover_tool.validate_input(action="get_book_by_id", book_id=123) is True
        )
        assert (
            hardcover_tool.validate_input(
                action="get_books_by_ids", book_ids=[123, 456]
            )
            is True
        )
        assert hardcover_tool.validate_input(action="get_current_user") is True

        # Invalid inputs
        assert hardcover_tool.validate_input() is False
        assert (
            hardcover_tool.validate_input(action="search_books") is False
        )  # Missing query
        assert (
            hardcover_tool.validate_input(action="get_book_by_id") is False
        )  # Missing book_id

    @pytest.mark.asyncio
    async def test_execute_validation_error(self, hardcover_tool: HardcoverTool):
        """Test execute with validation error."""
        result = await hardcover_tool.execute(action="search_books")  # Missing query

        assert result.success is False
        assert result.error is not None
        assert "Invalid parameters" in result.error

    @pytest.mark.asyncio
    async def test_get_current_user_action(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test getting current user information."""
        mock_gql_session.execute.return_value = MOCK_USER_RESPONSE

        result = await hardcover_tool.execute(action="get_current_user")

        assert result.success is True
        assert result.data == MOCK_USER_RESPONSE
        assert result.data["me"][0]["id"] == 148
        assert result.data["me"][0]["username"] == "testuser"
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_books_action(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test searching for books."""
        # Mock search response and books response
        mock_gql_session.execute.side_effect = [
            MOCK_SEARCH_RESPONSE,  # First call to search
            MOCK_BOOKS_RESPONSE,  # Second call to get_books_by_ids
        ]

        result = await hardcover_tool.execute(
            action="search_books", query="Python", limit=5
        )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["id"] == 123
        assert result.data[0]["title"] == "The Python Handbook"
        assert mock_gql_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_book_by_id_action(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test getting book by ID."""
        mock_gql_session.execute.return_value = MOCK_BOOK_RESPONSE

        result = await hardcover_tool.execute(action="get_book_by_id", book_id=123)

        assert result.success is True
        assert result.data == MOCK_BOOK_RESPONSE["books_by_pk"]
        assert result.data["id"] == 123
        assert result.data["title"] == "The Python Handbook"
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_books_by_ids_action(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test getting books by IDs."""
        mock_gql_session.execute.return_value = MOCK_BOOKS_RESPONSE

        result = await hardcover_tool.execute(
            action="get_books_by_ids", book_ids=[123, 456]
        )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["id"] == 123
        assert result.data[0]["title"] == "The Python Handbook"
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_recommendations_action(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test getting user recommendations."""
        mock_gql_session.execute.return_value = MOCK_RECOMMENDATIONS_RESPONSE

        result = await hardcover_tool.execute(
            action="get_user_recommendations", limit=5
        )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["id"] == 1
        assert result.data[0]["book"]["id"] == 123
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_trending_books_action(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test getting trending books."""
        mock_gql_session.execute.return_value = MOCK_TRENDING_RESPONSE

        result = await hardcover_tool.execute(action="get_trending_books", limit=5)

        assert result.success is True
        assert result.data == MOCK_TRENDING_RESPONSE["books_trending"]
        assert result.data["ids"] == [123, 456, 789]
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_introspect_schema_action(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test GraphQL schema introspection."""
        mock_gql_session.execute.return_value = MOCK_SCHEMA_RESPONSE

        result = await hardcover_tool.execute(action="introspect_schema")

        assert result.success is True
        assert result.data == MOCK_SCHEMA_RESPONSE
        assert "__schema" in result.data
        assert "types" in result.data["__schema"]
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_action(self, hardcover_tool: HardcoverTool):
        """Test handling of unknown action."""
        result = await hardcover_tool.execute(action="unknown_action")

        assert result.success is False
        assert result.error is not None
        assert "Unknown action" in result.error

    @pytest.mark.asyncio
    async def test_search_books_empty_results(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test handling of empty search results."""
        mock_gql_session.execute.return_value = {"search": {"error": None, "ids": []}}

        result = await hardcover_tool.execute(
            action="search_books", query="NonexistentTopic"
        )

        assert result.success is True
        assert len(result.data) == 0
        mock_gql_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test error handling in execute method."""
        mock_gql_session.execute.side_effect = RuntimeError("GraphQL error")

        result = await hardcover_tool.execute(action="get_current_user")

        assert result.success is False
        assert result.error is not None
        assert (
            "GraphQL error" in result.error or "Failed after 3 attempts" in result.error
        )

    @pytest.mark.asyncio
    async def test_missing_token_error(self):
        """Test error when API token is missing."""
        with patch("tools.external.hardcover.config.HARDCOVER_API_TOKEN", None):
            from tools.external.hardcover import HardcoverAuthError

            with pytest.raises(
                HardcoverAuthError, match="Hardcover API token not configured"
            ):
                HardcoverTool()
