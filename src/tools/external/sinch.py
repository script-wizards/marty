import base64
import hashlib
import hmac
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.config import config


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
    Async Sinch SMS API client.
    """

    def __init__(
        self,
        key_id: str,
        key_secret: str,
        project_id: str,
        api_url: str = "https://us.sms.api.sinch.com",
    ) -> None:
        self.key_id = key_id
        self.key_secret = key_secret
        self.project_id = project_id
        self.api_url = api_url.rstrip("/")
        self._auth = (self.key_id, self.key_secret)

    async def send_sms(
        self, *, body: str, to: list[str], from_: str, delivery_report: str = "none"
    ) -> dict[str, Any]:
        url = f"{self.api_url}/xms/v1/{self.project_id}/batches"
        payload = {
            "body": body,
            "to": to,
            "from": from_,
            "delivery_report": delivery_report,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json=payload,
                auth=self._auth,
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()


# Singleton for app usage
if not all([config.SINCH_KEY_ID, config.SINCH_KEY_SECRET, config.SINCH_PROJECT_ID]):
    raise RuntimeError(
        "Sinch configuration missing: SINCH_KEY_ID, SINCH_KEY_SECRET, and SINCH_PROJECT_ID must be set."
    )
sinch_client = SinchClient(
    key_id=config.SINCH_KEY_ID,  # type: ignore[arg-type]
    key_secret=config.SINCH_KEY_SECRET,  # type: ignore[arg-type]
    project_id=config.SINCH_PROJECT_ID,  # type: ignore[arg-type]
    api_url=config.SINCH_API_URL,
)
