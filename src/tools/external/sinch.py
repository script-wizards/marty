import base64
import hashlib
import hmac
from typing import Any

import httpx
import phonenumbers
from pydantic import BaseModel, ConfigDict, Field

from src.config import config


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to E-164 format without + sign for Sinch API.

    Args:
        phone: Phone number in various formats

    Returns:
        Phone number in E-164 format without + sign

    Raises:
        ValueError: If the phone number cannot be parsed or is invalid
    """
    try:
        # Try parsing with US as default region for numbers without country code
        parsed_number = phonenumbers.parse(phone, "US")

        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError(f"Invalid phone number: {phone}")

        e164_format = phonenumbers.format_number(
            parsed_number, phonenumbers.PhoneNumberFormat.E164
        )
        return e164_format[1:]  # Remove leading +

    except phonenumbers.NumberParseException as e:
        raise ValueError(f"Could not parse phone number '{phone}': {e}") from e
    except Exception as e:
        raise ValueError(f"Error normalizing phone number '{phone}': {e}") from e


def validate_phone_number(phone: str) -> bool:
    """
    Validate if a phone number is in a valid format.

    Args:
        phone: Phone number to validate

    Returns:
        True if the phone number is valid, False otherwise
    """
    try:
        parsed_number = phonenumbers.parse(phone, "US")
        return phonenumbers.is_valid_number(parsed_number)
    except phonenumbers.NumberParseException:
        return False


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

        try:
            normalized_to = [normalize_phone_number(phone) for phone in to]
            normalized_from = normalize_phone_number(from_)
        except ValueError as e:
            raise ValueError(f"Phone number validation failed: {e}") from e

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


# Singleton for app usage with lazy initialization
_sinch_client: SinchClient | None = None


def get_sinch_client() -> SinchClient:
    """
    Lazily initialize and return the SinchClient singleton.
    Raises RuntimeError if required configuration is missing.
    """
    global _sinch_client

    if _sinch_client is None:
        if not all([config.SINCH_API_TOKEN, config.SINCH_SERVICE_PLAN_ID]):
            raise RuntimeError(
                "Sinch configuration missing: SINCH_API_TOKEN and SINCH_SERVICE_PLAN_ID must be set."
            )

        _sinch_client = SinchClient(
            api_token=config.SINCH_API_TOKEN,  # type: ignore[arg-type]
            service_plan_id=config.SINCH_SERVICE_PLAN_ID,  # type: ignore[arg-type]
            api_url=config.SINCH_API_URL,
        )

    return _sinch_client  # type: ignore[return-value]
