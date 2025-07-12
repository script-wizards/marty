"""
Test configuration for Marty SMS Bot.
Ensures test isolation and prevents accidental use of production services.
"""

import os
from unittest.mock import patch

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
def mock_claude_client():
    """Mock the Claude client creation to prevent any real API initialization."""
    from unittest.mock import AsyncMock, MagicMock

    # Mock the entire AsyncAnthropic class
    with patch("ai_client.AsyncAnthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock()
        mock_anthropic.return_value = mock_client
        yield mock_client
