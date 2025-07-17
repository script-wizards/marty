import logging
import os
from datetime import UTC, datetime

import redis.asyncio as redis
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import ValidationError

from src.ai_client import ConversationMessage, generate_ai_response
from src.config import config
from src.database import (
    ConversationCreate,
    CustomerCreate,
    MessageCreate,
    add_message,
    create_conversation,
    create_customer,
    get_active_conversation,
    get_conversation_messages,
    get_customer_by_phone,
    get_db,
)
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
    """Process incoming SMS through Marty's AI system."""
    phone = payload.from_info["endpoint"]
    user_message = payload.message

    logger.info(f"Processing SMS from {phone}: {user_message}")

    try:
        # Get database session
        async for db in get_db():
            # Get or create customer
            customer = await get_customer_by_phone(db, phone)
            if not customer:
                customer_data = CustomerCreate(phone=phone)
                customer = await create_customer(db, customer_data)
                logger.info(f"Created new customer for {phone}")

            # Get or create active conversation
            conversation = await get_active_conversation(db, phone)
            if not conversation:
                conversation_data = ConversationCreate(
                    customer_id=customer.id, phone=phone, status="active"
                )
                conversation = await create_conversation(db, conversation_data)
                logger.info(f"Created new conversation for {phone}")

            # Save the incoming message
            incoming_message = MessageCreate(
                conversation_id=conversation.id,
                direction="inbound",
                content=user_message,
                status="received",
            )
            await add_message(db, incoming_message)

            # Get recent conversation history
            recent_messages = await get_conversation_messages(
                db, conversation.id, limit=10
            )

            # Convert to ConversationMessage format (exclude the current message)
            conversation_history = []
            for msg in recent_messages[:-1]:  # Exclude the current message
                conversation_history.append(
                    ConversationMessage(
                        role="user" if msg.direction == "inbound" else "assistant",
                        content=msg.content,
                        timestamp=msg.created_at,
                    )
                )

            # Prepare customer context
            customer_context = {
                "customer_id": customer.id,
                "phone": phone,
                "name": customer.name,
                "current_time": datetime.now(UTC).strftime("%I:%M %p"),
                "current_date": datetime.now(UTC).strftime("%B %d, %Y"),
                "current_day": datetime.now(UTC).strftime("%A"),
            }

            # Generate AI response
            ai_response = await generate_ai_response(
                user_message=user_message,
                conversation_history=conversation_history,
                customer_context=customer_context,
            )

            # Save the AI response
            response_message = MessageCreate(
                conversation_id=conversation.id,
                direction="outbound",
                content=ai_response,
                status="sent",
            )
            await add_message(db, response_message)

            # Send SMS response
            await sinch_client.send_sms(
                body=ai_response,
                to=[phone],
                from_=payload.to["endpoint"],
            )

            logger.info(f"Sent AI response to {phone}")
            break  # Exit the generator loop

    except Exception as e:
        logger.error(f"Error processing SMS from {phone}: {e}")
        # Send error message to user
        try:
            await sinch_client.send_sms(
                body="Sorry, I'm having trouble processing your message right now. Please try again later! 🤖",
                to=[phone],
                from_=payload.to["endpoint"],
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")


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
