import base64
import hashlib
import hmac
import json
import os
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from src.main import app
from src.sms_handler import rate_limit
from src.tools.external.sinch import (
    SinchSMSWebhookPayload,
    normalize_phone_number,
    validate_phone_number,
    verify_sinch_signature,
)

client = TestClient(app)


@pytest.fixture
def mock_redis():
    with patch("src.sms_handler.redis.from_url") as mock:
        redis_mock = AsyncMock()
        # Default behavior - can be overridden in individual tests
        redis_mock.incr.return_value = 1
        redis_mock.expire = AsyncMock()
        mock.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def mock_sinch_client():
    """Mock Sinch client using dependency injection."""
    from src.tools.external.sinch import reset_sinch_client, set_sinch_client

    mock_client = AsyncMock()
    mock_client.send_sms = AsyncMock()

    # Set the mock client using dependency injection
    set_sinch_client(mock_client)

    yield mock_client

    # Clean up after test
    reset_sinch_client()


@pytest.fixture
def valid_webhook_payload():
    return {
        "id": "test-id",
        "type": "mo_text",
        "from": {"type": "number", "endpoint": "+12125551234"},
        "to": {"type": "number", "endpoint": "+19876543210"},
        "message": "Hello, Marty!",
        "received_at": "2024-07-17T00:00:00Z",
    }


@pytest.fixture
def unique_webhook_payload():
    """Create unique payloads for each test to avoid rate limiting conflicts."""
    import uuid

    phone_number = f"+1212555{str(uuid.uuid4().int)[:4]}"
    return {
        "id": f"test-id-{uuid.uuid4()}",
        "type": "mo_text",
        "from": {"type": "number", "endpoint": phone_number},
        "to": {"type": "number", "endpoint": "+19876543210"},
        "message": "Hello, Marty!",
        "received_at": "2024-07-17T00:00:00Z",
    }


@pytest.fixture
def mock_redis_reset():
    """Mock Redis that always returns 1 for incr calls - used for integration tests."""
    with patch("src.sms_handler.redis.from_url") as mock:
        redis_mock = AsyncMock()
        # Always return 1 for each incr call to simulate fresh Redis state
        redis_mock.incr.side_effect = lambda key: 1
        redis_mock.expire = AsyncMock()
        mock.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def webhook_secret():
    return "test-secret-key"


def create_signature(payload: str, secret: str) -> str:
    mac = hmac.new(secret.encode(), msg=payload.encode(), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


class TestPhoneNumberNormalization:
    """Test phone number normalization and validation."""

    def test_normalize_phone_number_us(self):
        """Test US phone number normalization."""
        # Test various US formats with valid area codes
        assert normalize_phone_number("+1-212-555-1234") == "12125551234"
        assert normalize_phone_number("(212) 555-1234") == "12125551234"
        assert normalize_phone_number("212.555.1234") == "12125551234"
        assert normalize_phone_number("2125551234") == "12125551234"
        assert normalize_phone_number("1-212-555-1234") == "12125551234"

    def test_normalize_phone_number_international(self):
        """Test international phone number normalization."""
        # UK number
        assert normalize_phone_number("+44 20 7946 0958") == "442079460958"
        # German number
        assert normalize_phone_number("+49 30 12345678") == "493012345678"
        # French number
        assert normalize_phone_number("+33 1 42 86 20 00") == "33142862000"
        # Japanese number
        assert normalize_phone_number("+81 3-1234-5678") == "81312345678"

    def test_normalize_phone_number_invalid(self):
        """Test invalid phone number handling."""
        with pytest.raises(ValueError, match="Invalid phone number"):
            normalize_phone_number("123")

        with pytest.raises(ValueError, match="Could not parse phone number"):
            normalize_phone_number("not-a-number")

        with pytest.raises(ValueError, match="Invalid phone number"):
            normalize_phone_number("+1-555-123")  # Too short

    def test_validate_phone_number(self):
        """Test phone number validation."""
        # Valid numbers
        assert validate_phone_number("+1-212-555-1234") is True
        assert validate_phone_number("+44 20 7946 0958") is True
        assert validate_phone_number("(212) 555-1234") is True

        # Invalid numbers
        assert validate_phone_number("123") is False
        assert validate_phone_number("not-a-number") is False
        assert validate_phone_number("+1-555-123") is False  # Too short


class TestSignatureVerification:
    def test_verify_sinch_signature_valid(self, webhook_secret):
        payload = {"test": "data"}
        payload_str = json.dumps(payload)
        signature = create_signature(payload_str, webhook_secret)
        current_time = str(int(time.time()))
        assert verify_sinch_signature(
            payload_str.encode(), signature, webhook_secret, current_time
        )

    def test_verify_sinch_signature_invalid(self, webhook_secret):
        payload = {"test": "data"}
        payload_str = json.dumps(payload)
        signature = "invalid-signature"
        current_time = str(int(time.time()))
        assert not verify_sinch_signature(
            payload_str.encode(), signature, webhook_secret, current_time
        )

    def test_verify_sinch_signature_wrong_secret(self, webhook_secret):
        payload = {"test": "data"}
        payload_str = json.dumps(payload)
        signature = create_signature(payload_str, "wrong-secret")
        current_time = str(int(time.time()))
        assert not verify_sinch_signature(
            payload_str.encode(), signature, "correct-secret", current_time
        )

    def test_verify_sinch_signature_old_timestamp(self, webhook_secret):
        payload = {"test": "data"}
        payload_str = json.dumps(payload)
        signature = create_signature(payload_str, webhook_secret)
        old_time = str(
            int(time.time()) - 400
        )  # 400 seconds ago (older than 5 min limit)
        assert not verify_sinch_signature(
            payload_str.encode(), signature, webhook_secret, old_time
        )

    def test_verify_sinch_signature_future_timestamp(self, webhook_secret):
        payload = {"test": "data"}
        payload_str = json.dumps(payload)
        signature = create_signature(payload_str, webhook_secret)
        future_time = str(int(time.time()) + 100)  # 100 seconds in future
        assert not verify_sinch_signature(
            payload_str.encode(), signature, webhook_secret, future_time
        )


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_first_message(self, mock_redis):
        await rate_limit("+12125551234", mock_redis)
        # Should call incr twice: once for rate limit, once for burst protection
        assert mock_redis.incr.call_count == 2
        mock_redis.incr.assert_any_call("sms:rate:+12125551234")
        mock_redis.incr.assert_any_call("sms:burst:+12125551234")
        # Should call expire twice: once for rate limit, once for burst protection
        assert mock_redis.expire.call_count == 2
        mock_redis.expire.assert_any_call("sms:rate:+12125551234", 60)
        mock_redis.expire.assert_any_call("sms:burst:+12125551234", 3600)

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, mock_redis):
        mock_redis.incr.return_value = 6  # Exceeds limit of 5
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit("+12125551234", mock_redis)
        exception = exc_info.value
        assert exception.status_code == 429
        assert "whoa slow down there, give me a sec to catch up" in str(
            exception.detail
        )

    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(self, mock_redis):
        mock_redis.incr.return_value = 3  # in limit
        await rate_limit("+12125551234", mock_redis)
        # Should call incr twice: once for rate limit, once for burst protection
        assert mock_redis.incr.call_count == 2
        mock_redis.incr.assert_any_call("sms:rate:+12125551234")
        mock_redis.incr.assert_any_call("sms:burst:+12125551234")

    @pytest.mark.asyncio
    async def test_burst_limit_exceeded(self, mock_redis):
        # Mock rate limit as OK but burst limit exceeded
        mock_redis.incr.side_effect = [
            3,
            11,
        ]  # rate=3 (OK), burst=11 (exceeds limit of 10)
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit("+12125551234", mock_redis)
        exception = exc_info.value
        assert exception.status_code == 429
        assert "whoa slow down there, give me a sec to catch up" in str(
            exception.detail
        )


class TestSMSWebhook:
    def _auth_header(self, username: str, password: str) -> dict[str, str]:
        import base64

        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def test_webhook_missing_auth(self, valid_webhook_payload):
        # No Authorization header
        response = client.post("/webhook/sms", json=valid_webhook_payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_webhook_invalid_auth(self, valid_webhook_payload):
        # Wrong username/password
        headers = self._auth_header("wronguser", "wrongpass")
        response = client.post(
            "/webhook/sms", json=valid_webhook_payload, headers=headers
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication credentials"

    @patch.dict(
        os.environ,
        {"SINCH_WEBHOOK_USERNAME": "testuser", "SINCH_WEBHOOK_PASSWORD": "testpass"},
    )
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_webhook_valid_auth(
        self,
        unique_webhook_payload,
        mock_redis_reset,
        mock_sinch_client,
        use_postgres_db,
        clean_postgres_db,
    ):
        TestSessionLocal, test_engine = use_postgres_db
        import importlib

        import src.sms_handler

        importlib.reload(src.sms_handler)
        headers = self._auth_header("testuser", "testpass")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/webhook/sms", json=unique_webhook_payload, headers=headers
            )
        assert response.status_code == 200
        assert response.json()["message"] == "Inbound message received"

    def test_webhook_invalid_payload_with_auth(self):
        with patch.dict(
            os.environ,
            {
                "SINCH_WEBHOOK_USERNAME": "testuser",
                "SINCH_WEBHOOK_PASSWORD": "testpass",
            },
        ):
            import importlib

            import src.sms_handler

            importlib.reload(src.sms_handler)

            headers = self._auth_header("testuser", "testpass")
            invalid_payload = {"invalid": "data"}
            response = client.post(
                "/webhook/sms", json=invalid_payload, headers=headers
            )
            assert response.status_code == 400

    @patch.dict(
        os.environ,
        {"SINCH_WEBHOOK_USERNAME": "testuser", "SINCH_WEBHOOK_PASSWORD": "testpass"},
    )
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_webhook_stop_opt_out(
        self,
        unique_webhook_payload,
        mock_redis_reset,
        mock_sinch_client,
        use_postgres_db,
        clean_postgres_db,
    ):
        TestSessionLocal, test_engine = use_postgres_db
        import importlib

        import src.sms_handler
        from src.database import get_customer_by_phone

        importlib.reload(src.sms_handler)
        headers = self._auth_header("testuser", "testpass")
        stop_payload = unique_webhook_payload.copy()
        stop_payload["message"] = "STOP"

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/webhook/sms", json=stop_payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Opt-out confirmation sent"
        mock_sinch_client.send_sms.assert_awaited_with(
            body="Dungeon Books: You have unsubscribed and will no longer receive messages. Reply HELP for help.",
            to=[stop_payload["from"]["endpoint"]],
            from_=stop_payload["to"]["endpoint"],
        )

        # Check DB for opted_out - use the test database session directly
        async with TestSessionLocal() as db:
            customer = await get_customer_by_phone(db, stop_payload["from"]["endpoint"])
            assert customer is not None
            assert customer.opted_out is True

    @patch.dict(
        os.environ,
        {"SINCH_WEBHOOK_USERNAME": "testuser", "SINCH_WEBHOOK_PASSWORD": "testpass"},
    )
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_webhook_help_message(
        self,
        unique_webhook_payload,
        mock_redis_reset,
        mock_sinch_client,
        use_postgres_db,
        clean_postgres_db,
    ):
        TestSessionLocal, test_engine = use_postgres_db
        import importlib

        import src.sms_handler
        from src.database import get_customer_by_phone

        importlib.reload(src.sms_handler)
        headers = self._auth_header("testuser", "testpass")
        help_payload = unique_webhook_payload.copy()
        help_payload["message"] = "HELP"

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/webhook/sms", json=help_payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Help message sent"
        mock_sinch_client.send_sms.assert_awaited_with(
            body="Dungeon Books: For help, contact hello@dungeonbooks.com or reply STOP to unsubscribe. Msg&data rates may apply.",
            to=[help_payload["from"]["endpoint"]],
            from_=help_payload["to"]["endpoint"],
        )

        # Check DB for opted_out remains False - use the test database session directly
        async with TestSessionLocal() as db:
            customer = await get_customer_by_phone(db, help_payload["from"]["endpoint"])
            assert customer is not None, (
                f"No customer found for phone {help_payload['from']['endpoint']}"
            )
            assert customer.opted_out is False


class TestBackgroundTask:
    @pytest.fixture
    def setup_mocks(self):
        """Set up all mocks for process_incoming_sms test."""
        with (
            patch("src.sms_handler.get_db_session") as mock_get_db_session,
            patch("src.sms_handler.get_customer_by_phone") as mock_get_customer,
            patch("src.sms_handler.create_customer") as mock_create_customer,
            patch("src.sms_handler.get_active_conversation") as mock_get_conversation,
            patch("src.sms_handler.create_conversation") as mock_create_conversation,
            patch("src.sms_handler.add_message") as mock_add_message,
            patch("src.sms_handler.get_conversation_messages") as mock_get_messages,
            patch("src.sms_handler.generate_ai_response") as mock_ai_response,
        ):
            mock_db = AsyncMock()

            # Mock the async context manager
            mock_get_db_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_db
            )
            mock_get_db_session.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_customer = AsyncMock()
            mock_customer.id = "customer-123"
            mock_get_customer.return_value = None
            mock_create_customer.return_value = mock_customer

            mock_conversation = AsyncMock()
            mock_conversation.id = "conversation-123"
            mock_get_conversation.return_value = None
            mock_create_conversation.return_value = mock_conversation

            mock_get_messages.return_value = []
            mock_ai_response.return_value = "Here's a great sci-fi book recommendation!"

            yield (
                mock_get_db_session,
                mock_get_customer,
                mock_create_customer,
                mock_get_conversation,
                mock_create_conversation,
                mock_add_message,
                mock_get_messages,
                mock_ai_response,
            )

    @pytest.mark.asyncio
    async def test_process_incoming_sms(self, mock_sinch_client, setup_mocks):
        (
            mock_get_db_session,
            mock_get_customer,
            mock_create_customer,
            mock_get_conversation,
            mock_create_conversation,
            mock_add_message,
            mock_get_messages,
            mock_ai_response,
        ) = setup_mocks

        payload = SinchSMSWebhookPayload.model_validate(
            {
                "id": "test-id",
                "type": "mo_text",
                "from": {
                    "type": "number",
                    "endpoint": "+12125551234",
                },
                "to": {
                    "type": "number",
                    "endpoint": "+19876543210",
                },
                "message": "Hello, Marty!",
                "received_at": "2024-07-17T00:00:00Z",
            }
        )

        # Import the function within the test to ensure proper patching
        from src.sms_handler import process_incoming_sms

        await process_incoming_sms(payload)

        # Verify AI response was generated
        mock_ai_response.assert_called_once()

        # Verify database operations were called
        mock_add_message.assert_called()  # Called twice: once for incoming, once for outgoing
        assert mock_add_message.call_count == 2

        # Verify SMS was sent with AI response
        mock_sinch_client.send_sms.assert_called_once_with(
            body="Here's a great sci-fi book recommendation!",
            to=["+12125551234"],
            from_="+19876543210",
        )


class TestPydanticModels:
    def test_sinch_webhook_payload_valid(self):
        data = {
            "id": "test-id",
            "type": "mo_text",
            "from": {"type": "number", "endpoint": "+1234567890"},
            "to": {"type": "number", "endpoint": "+0987654321"},
            "message": "Test message",
            "received_at": "2023-01-01T12:00:00Z",
        }
        payload = SinchSMSWebhookPayload.model_validate(data)
        assert payload.type == "mo_text"
        assert payload.from_info["endpoint"] == "+1234567890"
        assert payload.to["endpoint"] == "+0987654321"
        assert payload.message == "Test message"

    def test_sinch_webhook_payload_missing_required_fields(self):
        data = {"type": "mo_text"}  # Missing required fields
        with pytest.raises(ValidationError):
            SinchSMSWebhookPayload.model_validate(data)


@pytest.fixture
async def test_redis():
    """Redis client for integration testing."""
    import os

    import redis.asyncio as redis

    redis_url = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")
    client = redis.from_url(redis_url, decode_responses=True)

    # Clean up any existing test data
    await client.flushdb()

    yield client

    # Clean up after test
    await client.flushdb()
    await client.aclose()


class TestRedisIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rate_limit_with_real_redis(self, test_redis):
        """Test rate limiting directly with real Redis to avoid event loop conflicts."""
        phone = "+12125551234"

        # Test rate limiting function directly with real Redis
        # First 5 calls should succeed
        for _i in range(5):
            await rate_limit(phone, test_redis)

        # 6th call should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit(phone, test_redis)

        assert exc_info.value.status_code == 429
        assert "whoa slow down there, give me a sec to catch up" in str(
            exc_info.value.detail
        )

        # Verify rate limit key exists and has correct value
        rate_key = f"sms:rate:{phone}"
        count = await test_redis.get(rate_key)
        assert count is not None
        assert int(count) == 6

        # Verify TTL is set
        ttl = await test_redis.ttl(rate_key)
        assert ttl > 0

        # Verify burst key exists
        burst_key = f"sms:burst:{phone}"
        burst_count = await test_redis.get(burst_key)
        assert burst_count is not None
        assert int(burst_count) == 6
