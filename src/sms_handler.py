import logging
import os

import redis.asyncio as redis
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import ValidationError

from src.config import config
from src.tools.external.sinch import (
    SinchSMSResponse,
    SinchSMSWebhookPayload,
    sinch_client,
    verify_sinch_signature,
)

router = APIRouter()
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT = 5  # messages per window
RATE_LIMIT_WINDOW = 60  # seconds


async def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def get_signature_header(request: Request) -> str:
    sig = request.headers.get("x-sinch-signature")
    if not sig:
        raise HTTPException(status_code=400, detail="Missing Sinch signature header")
    return sig


async def rate_limit(phone: str, redis) -> None:
    key = f"sms:rate:{phone}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, RATE_LIMIT_WINDOW)
    if count > RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


async def process_incoming_sms(payload: SinchSMSWebhookPayload) -> None:
    # Echo the message back for now
    await sinch_client.send_sms(
        body=f"Echo: {payload.message}",
        to=[payload.from_info["endpoint"]],
        from_=payload.to["endpoint"],
    )
    logger.info(f"Echoed SMS to {payload.from_info['endpoint']}")


@router.post("/webhook/sms", response_model=SinchSMSResponse)
async def sms_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_sinch_signature: str = Header(...),
    redis=Depends(get_redis),
):
    raw_body = await request.body()
    # Verify signature
    if not config.SINCH_WEBHOOK_SECRET:
        logger.error("Sinch webhook secret not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    if not verify_sinch_signature(
        raw_body, x_sinch_signature, config.SINCH_WEBHOOK_SECRET
    ):
        logger.warning("Invalid Sinch webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    # Parse payload
    try:
        payload = SinchSMSWebhookPayload.model_validate_json(raw_body)
    except ValidationError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    # Rate limiting
    await rate_limit(payload.from_info["endpoint"], redis)
    # Background processing
    background_tasks.add_task(process_incoming_sms, payload)
    logger.info(f"Accepted SMS from {payload.from_info['endpoint']}")
    return SinchSMSResponse(message="Inbound message received")
