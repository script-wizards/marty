"""
Tests for HardcoverTool - Hardcover API integration tool.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.tools.external.hardcover import HardcoverTool

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
        "src.tools.external.hardcover.config.HARDCOVER_API_TOKEN", "Bearer test_token"
    ):
        with patch(
            "src.tools.external.hardcover.config.get_hardcover_headers"
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

    with patch("src.tools.external.hardcover.Client") as mock_client_class:
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
        assert (
            "Gets book details, ratings, and purchase links"
            in hardcover_tool.description
        )

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
        # Mock two calls: first for trending IDs, second for book details
        mock_gql_session.execute.side_effect = [
            MOCK_TRENDING_RESPONSE,  # First call to get trending book IDs
            MOCK_BOOKS_RESPONSE,  # Second call to get book details
        ]

        result = await hardcover_tool.execute(action="get_trending_books", limit=5)

        assert result.success is True
        assert result.data["ids"] == [123, 456, 789]
        assert "books" in result.data
        assert len(result.data["books"]) == 1  # MOCK_BOOKS_RESPONSE has 1 book
        assert result.data["books"][0]["title"] == "The Python Handbook"
        assert mock_gql_session.execute.call_count == 2

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
        with patch("src.tools.external.hardcover.config.HARDCOVER_API_TOKEN", None):
            from src.tools.external.hardcover import HardcoverAuthError

            with pytest.raises(
                HardcoverAuthError, match="Hardcover API token not configured"
            ):
                HardcoverTool()

    @pytest.mark.asyncio
    async def test_search_books_intelligent_action(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test intelligent book search with Claude optimization."""
        # Mock the QueryOptimizerTool response for a temporal query
        mock_optimization = {
            "pattern": "AUTHOR_QUERY",
            "query_terms": "Cassandra Khaw",
            "sort_by": "release_date:desc",  # Recent because "new" keyword present
            "author": "Cassandra Khaw",
            "title": None,
            "genre": None,
            "temporal_indicators": ["new"],
            "confidence": 0.9,
            "intent": "Find recent books by Cassandra Khaw",
            "search_strategy": "prioritize recent releases by author",
            "limit": 5,
        }

        # Mock recent releases response
        mock_recent_books = [
            {
                "id": 12345,
                "title": "The Library at Hellebore",
                "author": "Cassandra Khaw",
                "release_year": 2024,
                "cached_contributors": "Cassandra Khaw",
                "description": "A dark fantasy novel",
                "rating": 4.2,
            }
        ]

        with patch(
            "src.tools.utils.query_optimizer.QueryOptimizerTool"
        ) as mock_optimizer_class:
            mock_optimizer = AsyncMock()
            mock_optimizer.execute.return_value = type(
                "ToolResult", (), {"success": True, "data": mock_optimization}
            )()
            mock_optimizer_class.return_value = mock_optimizer

            # Mock the _get_recent_releases_extended method to return our test data
            with (
                patch.object(
                    hardcover_tool,
                    "_get_recent_releases_extended",
                    new_callable=AsyncMock,
                    return_value=mock_recent_books,
                ),
                patch.object(
                    hardcover_tool,
                    "_search_author_books_by_recency",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
                patch.object(
                    hardcover_tool,
                    "_search_books_optimized",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
                patch.object(
                    hardcover_tool,
                    "_search_books",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
            ):
                result = await hardcover_tool.execute(
                    action="search_books_intelligent",
                    query="Cassandra Khaw's new book",
                    limit=5,
                )

                assert result.success is True
                assert len(result.data) >= 1
                assert result.data[0]["title"] == "The Library at Hellebore"
                assert result.data[0]["author"] == "Cassandra Khaw"
                assert result.data[0]["release_year"] == 2024

                # Verify optimizer was called
                mock_optimizer.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_books_intelligent_fallback(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test intelligent search fallback when optimization fails."""
        # Mock search response for fallback
        mock_gql_session.execute.side_effect = [
            MOCK_SEARCH_RESPONSE,  # Search for book IDs
            MOCK_BOOKS_RESPONSE,  # Get book details
        ]

        with patch(
            "src.tools.utils.query_optimizer.QueryOptimizerTool"
        ) as mock_optimizer_class:
            mock_optimizer = AsyncMock()
            mock_optimizer.execute.return_value = type(
                "ToolResult", (), {"success": False, "error": "Claude API error"}
            )()
            mock_optimizer_class.return_value = mock_optimizer

            result = await hardcover_tool.execute(
                action="search_books_intelligent", query="some book query", limit=5
            )

            # Should fallback to standard search and still succeed
            assert result.success is True
            assert len(result.data) >= 1

    @pytest.mark.asyncio
    async def test_search_books_intelligent_popular_author(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test intelligent search for popular books by author (bare author name)."""
        # Mock optimization for popular author query (no temporal keywords)
        mock_optimization = {
            "pattern": "AUTHOR_QUERY",
            "query_terms": "Brandon Sanderson",
            "sort_by": "activities_count:desc",  # Popular because no temporal keywords
            "author": "Brandon Sanderson",
            "title": None,
            "genre": None,
            "temporal_indicators": [],
            "confidence": 0.8,
            "intent": "Find popular books by Brandon Sanderson",
            "search_strategy": "prioritize popular works by author",
            "limit": 5,
        }

        # Mock popular books response
        mock_popular_books = [
            {
                "id": 1,
                "title": "Mistborn: The Final Empire",
                "author": "Brandon Sanderson",
                "release_year": 2006,
                "rating": 4.4,
                "cached_contributors": "Brandon Sanderson",
            }
        ]

        with patch(
            "src.tools.utils.query_optimizer.QueryOptimizerTool"
        ) as mock_optimizer_class:
            mock_optimizer = AsyncMock()
            mock_optimizer.execute.return_value = type(
                "ToolResult", (), {"success": True, "data": mock_optimization}
            )()
            mock_optimizer_class.return_value = mock_optimizer

            # Mock the _search_books_optimized method
            with patch.object(
                hardcover_tool,
                "_search_books_optimized",
                return_value=mock_popular_books,
            ):
                result = await hardcover_tool.execute(
                    action="search_books_intelligent",
                    query="Brandon Sanderson",
                    limit=5,
                )

                assert result.success is True
                assert len(result.data) >= 1
                assert result.data[0]["title"] == "Mistborn: The Final Empire"
                assert result.data[0]["author"] == "Brandon Sanderson"

    @pytest.mark.asyncio
    async def test_search_recent_releases_by_author(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test searching recent releases by specific author."""
        mock_recent_books = [
            {
                "id": 1,
                "title": "The Library at Hellebore",
                "author": "Cassandra Khaw",
                "release_year": 2024,
                "cached_contributors": "Cassandra Khaw",
            },
            {
                "id": 2,
                "title": "Different Author Book",
                "author": "Someone Else",
                "release_year": 2024,
                "cached_contributors": "Someone Else",
            },
            {
                "id": 3,
                "title": "The Salt Grows Heavy",
                "author": "Cassandra Khaw",
                "release_year": 2023,
                "cached_contributors": "Cassandra Khaw",
            },
        ]

        with (
            patch.object(
                hardcover_tool,
                "_get_recent_releases_extended",
                new_callable=AsyncMock,
                return_value=mock_recent_books,
            ),
            patch.object(
                hardcover_tool,
                "_search_author_books_by_recency",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await hardcover_tool._search_recent_releases_by_author(
                "Cassandra Khaw", 5
            )

            # Should only return Cassandra Khaw's books
            assert len(result) == 2
            assert all(
                "Cassandra Khaw" in book.get("author", "")
                or "Cassandra Khaw" in book.get("cached_contributors", "")
                for book in result
            )
            assert result[0]["title"] == "The Library at Hellebore"
            assert result[1]["title"] == "The Salt Grows Heavy"

    @pytest.mark.asyncio
    async def test_search_author_books_by_recency(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test searching author's books sorted by recency."""
        mock_author_books = [
            {
                "id": 1,
                "title": "Old Book",
                "author": "Test Author",
                "release_year": 2020,
            },
            {
                "id": 2,
                "title": "Newer Book",
                "author": "Test Author",
                "release_year": 2023,
            },
            {
                "id": 3,
                "title": "Newest Book",
                "author": "Test Author",
                "release_year": 2024,
            },
        ]

        with patch.object(
            hardcover_tool, "_search_books", return_value=mock_author_books
        ):
            result = await hardcover_tool._search_author_books_by_recency(
                "Test Author", 5
            )

            # Should be sorted by release year descending
            assert len(result) == 3
            assert result[0]["title"] == "Newest Book"
            assert result[0]["release_year"] == 2024
            assert result[1]["title"] == "Newer Book"
            assert result[1]["release_year"] == 2023
            assert result[2]["title"] == "Old Book"
            assert result[2]["release_year"] == 2020

    @pytest.mark.asyncio
    async def test_search_books_optimized(
        self, hardcover_tool: HardcoverTool, mock_gql_session
    ):
        """Test optimized search with custom sort parameters."""
        mock_gql_session.execute.side_effect = [
            MOCK_SEARCH_RESPONSE,  # Search with custom sort
            MOCK_BOOKS_RESPONSE,  # Get book details
        ]

        result = await hardcover_tool._search_books_optimized(
            "fantasy books", "release_date:desc", 5
        )

        assert len(result) >= 1
        assert result[0]["title"] == "The Python Handbook"

        # Verify the GraphQL query was called with custom sort
        assert mock_gql_session.execute.call_count == 2
        # Check that the sort parameter was passed correctly
        call_args = mock_gql_session.execute.call_args_list[0]
        variables = call_args[1]["variable_values"]
        assert variables["sort"] == "release_date:desc"
