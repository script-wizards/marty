"""
Test configuration for Marty SMS Bot.
Ensures test isolation and prevents accidental use of production services.

CRITICAL: All tests must mock Claude/Anthropic API calls to prevent:
- Unnecessary API costs
- Rate limiting and quota exhaustion
- Non-deterministic test results
- Leaking test data to external services

Only explicit smoke tests should use real API calls, never in CI.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def test_environment():
    """Force test environment setup - no production API keys."""
    with patch.dict(
        os.environ,
        {
            # Remove production API keys
            "ANTHROPIC_API_KEY": "",
            # Set test database URL so health check works correctly
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            # Set test values if needed
            "HARDCOVER_API_TOKEN": "test-token",
        },
        clear=False,
    ):
        yield


@pytest.fixture(autouse=True)
def mock_claude_api():
    """
    Global mock for Claude/Anthropic API calls.

    This fixture automatically mocks all Claude API calls to:
    - Prevent accidental real API usage in tests
    - Ensure deterministic test results
    - Avoid API costs and rate limiting

    Tests can override the mock response using:
    mock_claude_api.messages.create.return_value = custom_response
    """
    # Create a mock response that matches Claude's actual response structure
    default_response = MagicMock()
    default_response.content = [MagicMock(text="hey! what can I help you with?")]

    # Mock the client instance directly (not the class)
    with patch("ai_client.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=default_response)

        # Reset the mock between tests
        mock_client.messages.create.reset_mock()

        yield mock_client


@pytest.fixture
def claude_response():
    """
    Factory fixture for creating Claude response objects.

    Usage:
        def test_something(claude_response):
            response = claude_response("Hello there!")
            mock_claude_api.messages.create.return_value = response
    """

    def _create_response(text: str):
        response = MagicMock()
        response.content = [MagicMock(text=text)]
        return response

    return _create_response
