"""
Tests for AI client and Claude integration.
Tests prompt loading, response generation, error handling, and mocking.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_client import (
    MARTY_SYSTEM_PROMPT,
    ConversationMessage,
    generate_ai_response,
    load_system_prompt,
)


class TestSystemPromptLoading:
    """Test system prompt loading functionality."""

    def test_load_system_prompt_success(self):
        """Test successful loading of system prompt."""
        prompt = load_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 1000  # Should be substantial
        assert "Martinus Trismegistus" in prompt
        assert "Never invent books" in prompt  # Safety feature
        assert "Text Formatting Rules" in prompt  # Operational details

    def test_load_system_prompt_custom_file(self):
        """Test loading system prompt from custom file."""
        # Create a temporary test prompt file
        test_prompt = "Test prompt content"
        test_file = Path("test_prompt.txt")
        test_file.write_text(test_prompt)

        try:
            prompt = load_system_prompt("test_prompt.txt")
            assert prompt == test_prompt
        finally:
            test_file.unlink()  # Clean up

    def test_load_system_prompt_file_not_found(self):
        """Test fallback when prompt file doesn't exist."""
        with patch("ai_client.logger.warning") as mock_warning:
            prompt = load_system_prompt("nonexistent_file.txt")

            assert isinstance(prompt, str)
            assert "Marty" in prompt  # Should contain fallback content
            assert len(prompt) > 10  # Should not be empty

            # Check that warning was logged instead of printed
            mock_warning.assert_called_once()
            assert "nonexistent_file.txt" in mock_warning.call_args[0][0]
            assert "not found" in mock_warning.call_args[0][0]

    def test_marty_system_prompt_loaded(self):
        """Test that the global MARTY_SYSTEM_PROMPT is loaded correctly."""
        assert isinstance(MARTY_SYSTEM_PROMPT, str)
        assert len(MARTY_SYSTEM_PROMPT) > 1000
        assert "Martinus Trismegistus" in MARTY_SYSTEM_PROMPT


class TestConversationMessage:
    """Test ConversationMessage model."""

    def test_conversation_message_creation(self):
        """Test creating a ConversationMessage."""
        from datetime import datetime

        msg = ConversationMessage(
            role="user", content="Hello Marty!", timestamp=datetime.now()
        )

        assert msg.role == "user"
        assert msg.content == "Hello Marty!"
        assert isinstance(msg.timestamp, datetime)

    def test_conversation_message_validation(self):
        """Test ConversationMessage validation."""
        from datetime import datetime

        # Valid roles
        for role in ["user", "assistant"]:
            msg = ConversationMessage(
                role=role, content="Test content", timestamp=datetime.now()
            )
            assert msg.role == role


class TestGenerateAIResponse:
    """Test AI response generation with mocked Claude API."""

    @pytest.mark.asyncio
    async def test_generate_ai_response_success(self):
        """Test successful AI response generation."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="hey! what're you looking for?")]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello Marty!", [])

            assert response == "hey! what're you looking for?"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_conversation_history(self):
        """Test AI response generation with conversation history."""
        from datetime import datetime

        history = [
            ConversationMessage(
                role="user", content="I need a Python book", timestamp=datetime.now()
            ),
            ConversationMessage(
                role="assistant",
                content="what level are you?",
                timestamp=datetime.now(),
            ),
        ]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="try Effective Python")]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("intermediate", history)

            assert response == "try Effective Python"

            # Check that conversation history was included
            call_args = mock_create.call_args
            messages = call_args[1]["messages"]
            assert len(messages) == 3  # 2 history + 1 current
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "I need a Python book"
            assert messages[1]["role"] == "assistant"
            assert messages[1]["content"] == "what level are you?"
            assert messages[2]["role"] == "user"
            assert messages[2]["content"] == "intermediate"

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_customer_context(self):
        """Test AI response generation with customer context."""
        customer_context = {
            "name": "John",
            "phone": "+1234567890",
            "customer_id": "123",
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="hey John! what're you looking for?")]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [], customer_context)

            assert response == "hey John! what're you looking for?"

            # Check that customer context was added to system prompt
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert "Customer name: John" in system_prompt
            assert "Phone: +1234567890" in system_prompt
            assert "Customer ID: 123" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_full_name(self):
        """Test AI response generation with full customer name."""
        customer_context = {
            "name": "John Doe",
            "phone": "+1234567890",
            "customer_id": "456",
        }

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="hey John Doe! what can I help you with?")
        ]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [], customer_context)

            assert response == "hey John Doe! what can I help you with?"

            # Check that full name is included in system prompt
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert "Customer name: John Doe" in system_prompt
            assert "Phone: +1234567890" in system_prompt
            assert "Customer ID: 456" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_cultural_name(self):
        """Test AI response generation with culturally diverse names."""
        customer_context = {
            "name": "José García-López",
            "phone": "+1234567890",
            "customer_id": "789",
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="¡Hola José García-López!")]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [], customer_context)

            assert response == "¡Hola José García-López!"

            # Check that full name is passed to Claude for cultural handling
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert "Customer name: José García-López" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_single_name(self):
        """Test AI response generation with single name (e.g., Madonna, Cher)."""
        customer_context = {
            "name": "Madonna",
            "phone": "+1234567890",
            "customer_id": "101",
        }

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="hey Madonna! what can I help you with?")
        ]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [], customer_context)

            assert response == "hey Madonna! what can I help you with?"

            # Check that single name is handled correctly
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert "Customer name: Madonna" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_professional_name(self):
        """Test AI response generation with professional/formal names."""
        customer_context = {
            "name": "Dr. John Smith MD",
            "phone": "+1234567890",
            "customer_id": "202",
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="hello Dr. Smith! how can I help?")]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [], customer_context)

            assert response == "hello Dr. Smith! how can I help?"

            # Check that the full professional name is included
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert "Customer name: Dr. John Smith MD" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_partial_context(self):
        """Test AI response generation with partial customer context."""
        customer_context = {
            "name": "Jane",
            "customer_id": "789",
            # Missing phone
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="hey Jane! how can I help?")]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [], customer_context)

            assert response == "hey Jane! how can I help?"

            # Check that only available fields are included
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert "Customer name: Jane" in system_prompt
            assert "Customer ID: 789" in system_prompt
            assert "Phone:" not in system_prompt  # Should not include missing phone

    @pytest.mark.asyncio
    async def test_generate_ai_response_minimal_context(self):
        """Test AI response generation with minimal customer context."""
        customer_context = {
            "customer_id": "999",
            # Only customer_id provided
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="hello! what are you looking for?")]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [], customer_context)

            assert response == "hello! what are you looking for?"

            # Check that only customer_id is included
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert "Customer ID: 999" in system_prompt
            assert "Customer name:" not in system_prompt
            assert "Phone:" not in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_api_error(self):
        """Test error handling when Claude API fails."""
        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create, patch("ai_client.logger.error") as mock_error:
            mock_create.side_effect = Exception("API Error")

            response = await generate_ai_response("Hello", [])

            assert "having trouble thinking" in response
            assert "🤔" in response

            # Check that error was logged
            mock_error.assert_called_once()
            assert "API Error" in mock_error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_generate_ai_response_empty_content(self):
        """Test handling of empty response content."""
        mock_response = MagicMock()
        mock_response.content = []

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [])

            assert "having trouble generating a response" in response

    @pytest.mark.asyncio
    async def test_generate_ai_response_no_text_attribute(self):
        """Test handling of response content without text attribute."""
        mock_response = MagicMock()
        mock_content = MagicMock()
        del mock_content.text  # Remove text attribute
        mock_response.content = [mock_content]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [])

            # Should fallback to string representation
            assert isinstance(response, str)
            assert len(response) > 0

    @pytest.mark.asyncio
    async def test_claude_api_parameters(self):
        """Test that correct parameters are passed to Claude API."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="test response")]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await generate_ai_response("Hello", [])

            call_args = mock_create.call_args
            assert call_args[1]["model"] == "claude-3-5-sonnet-20241022"
            assert call_args[1]["max_tokens"] == 500
            assert call_args[1]["temperature"] == 0.7
            assert isinstance(call_args[1]["system"], str)
            assert len(call_args[1]["system"]) > 1000  # Should be substantial
            assert isinstance(call_args[1]["messages"], list)

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_datetime_context(self):
        """Test AI response generation with datetime context."""
        customer_context = {
            "name": "John",
            "phone": "+1234567890",
            "customer_id": "123",
            "current_time": "2024-01-15T14:30:00Z",
            "current_date": "2024-01-15",
            "current_day": "Monday",
        }

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="hey John! it's Monday afternoon, what can I help you with?")
        ]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response("Hello", [], customer_context)

            assert "Monday afternoon" in response

            # Check that datetime context was added to system prompt
            call_args = mock_create.call_args
            system_prompt = call_args[1]["system"]
            assert "Current time: 2024-01-15T14:30:00Z" in system_prompt
            assert "Current date: 2024-01-15" in system_prompt
            assert "Day of week: Monday" in system_prompt
            assert "Customer name: John" in system_prompt


class TestEnvironmentIntegration:
    """Test environment integration and configuration."""

    def test_anthropic_api_key_loading(self):
        """Test that API key is loaded from environment."""
        # Test with environment variable
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            # Import client after setting env var
            from ai_client import client

            assert hasattr(client, "api_key")

    def test_missing_api_key_handling(self):
        """Test behavior when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise an error during import
            from ai_client import client

            assert client is not None


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.mark.asyncio
    async def test_book_recommendation_flow(self):
        """Test a complete book recommendation conversation."""
        from datetime import datetime

        # Simulate a conversation asking for book recommendations
        history = [
            ConversationMessage(
                role="user",
                content="I need a good Python book",
                timestamp=datetime.now(),
            ),
            ConversationMessage(
                role="assistant",
                content="what level are you at?",
                timestamp=datetime.now(),
            ),
        ]

        customer_context = {"name": "Alice", "phone": "+1555123456"}

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="try Effective Python by Brett Slatkin")
        ]

        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await generate_ai_response(
                "intermediate level", history, customer_context
            )

            assert "Effective Python" in response

            # Verify the system prompt includes safety features
            system_prompt = mock_create.call_args[1]["system"]
            assert "Never invent books" in system_prompt
            assert "Customer name: Alice" in system_prompt

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self):
        """Test error recovery in conversation flow."""
        # First call fails
        with patch(
            "ai_client.client.messages.create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("Network error")

            response = await generate_ai_response("Hello", [])

            assert "having trouble thinking" in response
            assert "🤔" in response
