import asyncio
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
    get_db_session,
)
from src.tools.external.sinch import (
    SinchSMSResponse,
    SinchSMSWebhookPayload,
    get_sinch_client,
    verify_sinch_signature,
)

router = APIRouter()
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Configurable rate limiting
RATE_LIMIT = int(os.getenv("SMS_RATE_LIMIT", "5"))  # messages per window
RATE_LIMIT_WINDOW = int(os.getenv("SMS_RATE_LIMIT_WINDOW", "60"))  # seconds
RATE_LIMIT_BURST = int(os.getenv("SMS_RATE_LIMIT_BURST", "10"))  # burst allowance

# SMS configuration
MAX_SMS_LENGTH = 160  # Standard SMS character limit
MAX_UNICODE_LENGTH = 70  # Unicode SMS character limit

# GSM-7 basic character set (strict - no accented characters)
GSM7_BASIC = (
    "@£$¥\n\r\u0020!\"#¤%&'()*+,-./0123456789:;<=>?"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)

# Redis connection pool
_redis_pool: redis.ConnectionPool | None = None


def get_redis_pool() -> redis.ConnectionPool:
    """Get Redis connection pool with singleton pattern."""
    global _redis_pool
    if _redis_pool is None:
        try:
            _redis_pool = redis.ConnectionPool.from_url(
                REDIS_URL,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Redis connection pool: {e}"
            ) from e

    if _redis_pool is None:
        raise RuntimeError("Redis connection pool is unexpectedly None")

    return _redis_pool  # type: ignore[return-value]


async def get_redis():
    """Get Redis connection from pool."""
    pool = get_redis_pool()
    return redis.Redis(connection_pool=pool)


def is_gsm7(text: str) -> bool:
    """
    Check if the text contains only GSM-7 basic characters.
    """
    for c in text:
        if c not in GSM7_BASIC:
            return False
    return True


def gsm7_safe(text: str) -> str:
    """
    Replace non-GSM-7 characters with '?'.
    """
    return "".join(c if c in GSM7_BASIC else "?" for c in text)


def split_response_for_sms(response: str) -> list[str]:
    """
    Split AI response into multiple SMS messages for conversational style.

    Args:
        response: The full AI response text

    Returns:
        List of SMS messages, each optimized for conversational flow
    """
    if not response.strip():
        return []

    # Clean up the response
    response = response.strip()

    # If response is short enough for one SMS, return as-is
    if len(response) <= MAX_SMS_LENGTH:
        return [response]

    # Split by sentences first (natural conversation breaks)
    sentences = []
    current_sentence = ""

    for char in response:
        current_sentence += char
        if char in ".!?":
            sentences.append(current_sentence.strip())
            current_sentence = ""

    # Add any remaining text
    if current_sentence.strip():
        sentences.append(current_sentence.strip())

    # Group sentences into SMS messages
    messages = []
    current_message = ""

    for sentence in sentences:
        # If adding this sentence would exceed SMS limit
        if len(current_message + sentence) > MAX_SMS_LENGTH:
            if current_message:
                messages.append(current_message.strip())
                current_message = sentence
            else:
                # Single sentence is too long, split by words
                words = sentence.split()
                for word in words:
                    if len(current_message + " " + word) > MAX_SMS_LENGTH:
                        if current_message:
                            messages.append(current_message.strip())
                            current_message = word
                        else:
                            # Single word is too long, split it
                            while len(word) > MAX_SMS_LENGTH:
                                messages.append(word[:MAX_SMS_LENGTH])
                                word = word[MAX_SMS_LENGTH:]
                            if word:
                                current_message = word
                    else:
                        current_message += (" " + word) if current_message else word
        else:
            current_message += (" " + sentence) if current_message else sentence

    # Add the last message
    if current_message.strip():
        messages.append(current_message.strip())

    return messages


async def send_multiple_sms(
    messages: list[str], to_phone: str, from_number: str
) -> None:
    """
    Send multiple SMS messages with proper spacing for conversational flow.
    Each message is checked for GSM-7 compliance; non-GSM-7 characters are replaced with '?'.
    """
    if not messages:
        return

    for i, message in enumerate(messages):
        safe_message = message
        if not is_gsm7(message):
            logger.warning(
                f"Non-GSM-7 characters detected in SMS to {to_phone}. Replacing with '?'. Original: {message}"
            )
            safe_message = gsm7_safe(message)
        try:
            await get_sinch_client().send_sms(
                body=safe_message,
                to=[to_phone],
                from_=from_number,
            )
            logger.info(f"Sent SMS {i + 1}/{len(messages)} to {to_phone}")
            # Add small delay between messages for natural flow
            if i < len(messages) - 1:
                await asyncio.sleep(config.SMS_MESSAGE_DELAY)
        except Exception as e:
            logger.error(
                f"Failed to send SMS {i + 1}/{len(messages)} to {to_phone}: {e}"
            )
            raise


async def rate_limit(phone: str, redis) -> None:
    """
    Enhanced rate limiting with configurable limits and burst protection.

    Args:
        phone: Phone number to rate limit
        redis: Redis connection

    Raises:
        HTTPException: If rate limit is exceeded
    """
    # Regular rate limiting
    key = f"sms:rate:{phone}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, RATE_LIMIT_WINDOW)

    # Burst protection
    burst_key = f"sms:burst:{phone}"
    burst_count = await redis.incr(burst_key)
    if burst_count == 1:
        await redis.expire(burst_key, 3600)  # 1 hour window for burst

    # Check limits
    if count > RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for {phone}: {count}/{RATE_LIMIT}")
        raise HTTPException(
            status_code=429, detail="whoa slow down there, give me a sec to catch up"
        )

    if burst_count > RATE_LIMIT_BURST:
        logger.warning(
            f"Burst limit exceeded for {phone}: {burst_count}/{RATE_LIMIT_BURST}"
        )
        raise HTTPException(
            status_code=429, detail="whoa slow down there, give me a sec to catch up"
        )


async def process_incoming_sms(payload: SinchSMSWebhookPayload) -> None:
    """Process incoming SMS through Marty's AI system."""
    phone = payload.from_info["endpoint"]
    user_message = payload.message

    logger.info(f"Processing SMS from {phone}: {user_message}")

    try:
        async with get_db_session() as db:
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
                        timestamp=msg.timestamp,
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

            # Split AI response into multiple SMS messages if enabled
            if config.SMS_MULTI_MESSAGE_ENABLED:
                messages_to_send = split_response_for_sms(ai_response)
            else:
                messages_to_send = [ai_response]

            # Save each SMS message to database
            for message_text in messages_to_send:
                response_message = MessageCreate(
                    conversation_id=conversation.id,
                    direction="outbound",
                    content=message_text,
                    status="sent",
                )
                await add_message(db, response_message)

            # Send all SMS messages
            await send_multiple_sms(messages_to_send, phone, payload.to["endpoint"])

            logger.info(f"Sent {len(messages_to_send)} SMS messages to {phone}")

    except Exception as e:
        logger.error(f"Error processing SMS from {phone}: {e}")
        # Send error message in Marty's voice
        error_message = "sorry my brain's lagging, give me a moment"
        if not is_gsm7(error_message):
            error_message = gsm7_safe(error_message)

        try:
            await get_sinch_client().send_sms(
                body=error_message,
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
    x_sinch_timestamp: str = Header(..., alias="X-Sinch-Timestamp"),
    redis=Depends(get_redis),
):
    raw_body = await request.body()
    # Verify signature and timestamp
    if not config.SINCH_WEBHOOK_SECRET:
        logger.error("Sinch webhook secret not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    if not verify_sinch_signature(
        raw_body, x_sinch_signature, config.SINCH_WEBHOOK_SECRET, x_sinch_timestamp
    ):
        logger.warning("Invalid Sinch webhook signature or timestamp")
        raise HTTPException(status_code=401, detail="Invalid signature or timestamp")
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
