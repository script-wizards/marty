import base64
import hashlib
import hmac
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.config import config


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to E-164 format without + sign for Sinch API.

    Args:
        phone: Phone number in various formats (+1234567890, 1234567890, etc.)

    Returns:
        Phone number in E-164 format without + sign (e.g., "11234567890")
    """
    # Remove any non-digit characters except +
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

    # Remove leading + if present
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    # Remove leading 00 if present (international prefix)
    if cleaned.startswith("00"):
        cleaned = cleaned[2:]

    return cleaned


class SinchSMSWebhookPayload(BaseModel):
    """Sinch SMS webhook payload model."""

    model_config = ConfigDict(extra="allow")

    id: str
    from_info: dict[str, str] = Field(alias="from")
    to: dict[str, str]
    message: str
    received_at: str
    type: str = "mo_text"


class SinchSMSResponse(BaseModel):
    message: str


class SinchSendSMSRequest(BaseModel):
    body: str
    to: list[str]
    from_: str = Field(..., alias="from")
    delivery_report: str = "none"


class SinchSendSMSResponse(BaseModel):
    id: str
    to: list[str]
    status: str
    # Add more fields as needed


def verify_sinch_signature(request_body: bytes, signature: str, secret: str) -> bool:
    """
    Verify Sinch webhook HMAC-SHA256 signature.
    """
    mac = hmac.new(secret.encode(), msg=request_body, digestmod=hashlib.sha256)
    expected = base64.b64encode(mac.digest()).decode()
    return hmac.compare_digest(expected, signature)


class SinchClient:
    """
    Async Sinch SMS API client using Bearer token authentication.
    """

    def __init__(
        self,
        api_token: str,
        service_plan_id: str,
        api_url: str = "https://us.sms.api.sinch.com",
    ) -> None:
        self.api_token = api_token
        self.service_plan_id = service_plan_id
        self.api_url = api_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def send_sms(
        self, *, body: str, to: list[str], from_: str, delivery_report: str = "none"
    ) -> dict[str, Any]:
        """Send SMS using Sinch SMS API with Bearer token authentication."""
        url = f"{self.api_url}/xms/v1/{self.service_plan_id}/batches"

        # Normalize phone numbers to E-164 format without + sign
        normalized_to = [normalize_phone_number(phone) for phone in to]
        normalized_from = normalize_phone_number(from_)

        payload = {
            "body": body,
            "to": normalized_to,
            "from": normalized_from,
            "delivery_report": delivery_report,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json=payload,
                headers=self._headers,
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()


# Singleton for app usage
if not all([config.SINCH_API_TOKEN, config.SINCH_SERVICE_PLAN_ID]):
    raise RuntimeError(
        "Sinch configuration missing: SINCH_API_TOKEN and SINCH_SERVICE_PLAN_ID must be set."
    )

sinch_client = SinchClient(
    api_token=config.SINCH_API_TOKEN,  # type: ignore[arg-type]
    service_plan_id=config.SINCH_SERVICE_PLAN_ID,  # type: ignore[arg-type]
    api_url=config.SINCH_API_URL,
)
