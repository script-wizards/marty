import base64
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.sms_handler import rate_limit, router
from src.tools.external.sinch import SinchSMSWebhookPayload, verify_sinch_signature

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def mock_redis():
    with patch("src.sms_handler.redis.from_url") as mock:
        redis_mock = AsyncMock()
        mock.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def mock_sinch_client():
    with patch("src.sms_handler.sinch_client") as mock:
        mock.send_sms = AsyncMock()
        yield mock


@pytest.fixture
def valid_webhook_payload():
    return {
        "id": "test-id",
        "type": "mo_text",
        "from": {"type": "number", "endpoint": "+1234567890"},
        "to": {"type": "number", "endpoint": "+0987654321"},
        "message": "Hello, Marty!",
        "received_at": "2024-07-17T00:00:00Z",
    }


@pytest.fixture
def webhook_secret():
    return "test-secret-key"


def create_signature(payload: str, secret: str) -> str:
    mac = hmac.new(secret.encode(), msg=payload.encode(), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


class TestSignatureVerification:
    def test_verify_sinch_signature_valid(self, webhook_secret):
        payload = {"test": "data"}
        payload_str = json.dumps(payload)
        signature = create_signature(payload_str, webhook_secret)
        assert verify_sinch_signature(payload_str.encode(), signature, webhook_secret)

    def test_verify_sinch_signature_invalid(self, webhook_secret):
        payload = {"test": "data"}
        payload_str = json.dumps(payload)
        signature = "invalid-signature"
        assert not verify_sinch_signature(
            payload_str.encode(), signature, webhook_secret
        )

    def test_verify_sinch_signature_wrong_secret(self):
        payload = {"test": "data"}
        payload_str = json.dumps(payload)
        signature = create_signature(payload_str, "wrong-secret")
        assert not verify_sinch_signature(
            payload_str.encode(), signature, "correct-secret"
        )


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_first_message(self, mock_redis):
        mock_redis.incr.return_value = 1
        mock_redis.expire = AsyncMock()
        await rate_limit("+1234567890", mock_redis)
        mock_redis.incr.assert_called_once_with("sms:rate:+1234567890")
        mock_redis.expire.assert_called_once_with("sms:rate:+1234567890", 60)

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, mock_redis):
        mock_redis.incr.return_value = 6  # Exceeds limit of 5
        with pytest.raises(Exception) as exc_info:
            await rate_limit("+1234567890", mock_redis)
        assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(self, mock_redis):
        mock_redis.incr.return_value = 3  # in limit
        await rate_limit("+1234567890", mock_redis)
        mock_redis.incr.assert_called_once_with("sms:rate:+1234567890")


class TestSMSWebhook:
    def test_webhook_missing_signature_header(self):
        response = client.post("/webhook/sms", json={"invalid": "data"})
        assert response.status_code == 422  # FastAPI validation error

    @patch("src.sms_handler.config.SINCH_WEBHOOK_SECRET", "test-secret")
    def test_webhook_invalid_signature(self, valid_webhook_payload):
        headers = {"x-sinch-signature": "invalid-signature"}
        response = client.post(
            "/webhook/sms", json=valid_webhook_payload, headers=headers
        )
        assert response.status_code == 401

    @patch("src.sms_handler.config.SINCH_WEBHOOK_SECRET", "test-secret")
    def test_webhook_valid_signature(
        self, valid_webhook_payload, mock_redis, mock_sinch_client
    ):
        payload_str = json.dumps(valid_webhook_payload)
        signature = create_signature(payload_str, "test-secret")
        headers = {"x-sinch-signature": signature}
        mock_redis.incr.return_value = 1
        mock_redis.expire = AsyncMock()
        response = client.post("/webhook/sms", content=payload_str, headers=headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Inbound message received"

    @patch("src.sms_handler.config.SINCH_WEBHOOK_SECRET", None)
    def test_webhook_no_secret_configured(self, valid_webhook_payload):
        headers = {"x-sinch-signature": "some-signature"}
        response = client.post(
            "/webhook/sms", json=valid_webhook_payload, headers=headers
        )
        assert response.status_code == 500

    @patch("src.sms_handler.config.SINCH_WEBHOOK_SECRET", "test-secret")
    def test_webhook_invalid_payload(self):
        invalid_payload = {"invalid": "data"}
        payload_str = json.dumps(invalid_payload)
        signature = create_signature(payload_str, "test-secret")
        headers = {"x-sinch-signature": signature}
        response = client.post("/webhook/sms", content=payload_str, headers=headers)
        assert response.status_code == 400


class TestBackgroundTask:
    @pytest.mark.asyncio
    async def test_process_incoming_sms(self, mock_sinch_client):
        # Mock database and AI dependencies
        with patch("src.sms_handler.get_db") as mock_get_db:
            with patch("src.sms_handler.get_customer_by_phone") as mock_get_customer:
                with patch("src.sms_handler.create_customer") as mock_create_customer:
                    with patch(
                        "src.sms_handler.get_active_conversation"
                    ) as mock_get_conversation:
                        with patch(
                            "src.sms_handler.create_conversation"
                        ) as mock_create_conversation:
                            with patch(
                                "src.sms_handler.add_message"
                            ) as mock_add_message:
                                with patch(
                                    "src.sms_handler.get_conversation_messages"
                                ) as mock_get_messages:
                                    with patch(
                                        "src.sms_handler.generate_ai_response"
                                    ) as mock_ai_response:
                                        mock_db = AsyncMock()

                                        async def mock_get_db_gen():
                                            yield mock_db

                                        mock_get_db.return_value = mock_get_db_gen()

                                        mock_customer = AsyncMock()
                                        mock_customer.id = "customer-123"
                                        mock_get_customer.return_value = None
                                        mock_create_customer.return_value = (
                                            mock_customer
                                        )

                                        mock_conversation = AsyncMock()
                                        mock_conversation.id = "conversation-123"
                                        mock_get_conversation.return_value = None
                                        mock_create_conversation.return_value = (
                                            mock_conversation
                                        )

                                        mock_get_messages.return_value = []
                                        mock_ai_response.return_value = (
                                            "Here's a great sci-fi book recommendation!"
                                        )

                                        payload = SinchSMSWebhookPayload.model_validate(
                                            {
                                                "id": "test-id",
                                                "type": "mo_text",
                                                "from": {
                                                    "type": "number",
                                                    "endpoint": "+1234567890",
                                                },
                                                "to": {
                                                    "type": "number",
                                                    "endpoint": "+0987654321",
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
                                            to=["+1234567890"],
                                            from_="+0987654321",
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
        phone = "+15551234567"
        payload = {
            "id": "test-id",
            "type": "mo_text",
            "from": {"type": "number", "endpoint": phone},
            "to": {"type": "number", "endpoint": "+19876543210"},
            "message": "Integration test message",
            "received_at": "2024-07-17T00:00:00Z",
        }
        payload_str = json.dumps(payload)
        headers = {"x-sinch-signature": "integration-test"}

        with patch("src.sms_handler.config.SINCH_WEBHOOK_SECRET", "integration-secret"):
            with patch("src.sms_handler.verify_sinch_signature", return_value=True):
                with patch("src.sms_handler.get_redis", return_value=test_redis):
                    with patch(
                        "src.sms_handler.sinch_client.send_sms", new_callable=AsyncMock
                    ):
                        # Test real rate limiting with actual Redis
                        # First 5 requests should succeed
                        for _ in range(5):
                            response = client.post(
                                "/webhook/sms",
                                content=payload_str,
                                headers=headers,
                            )
                            assert response.status_code == 200

                        # 6th request should be rate limited
                        response = client.post(
                            "/webhook/sms", content=payload_str, headers=headers
                        )
                        assert response.status_code == 429
                        assert "Rate limit exceeded" in response.text

                        # Verify rate limit key exists and has correct value
                        rate_key = f"sms:rate:{phone}"
                        count = await test_redis.get(rate_key)
                        assert count is not None
                        assert int(count) == 6

                        # Verify TTL is set
                        ttl = await test_redis.ttl(rate_key)
                        assert ttl > 0
