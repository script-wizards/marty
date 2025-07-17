"""
ConversationManager Tool - Manages conversation state and context.

This tool handles conversation state management including:
- Loading conversations from Redis cache or database
- Adding messages to conversations
- Managing conversation context for AI processing
- Caching conversations in Redis
- Conversation expiration and summarization
"""

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
import structlog

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
from src.tools.base import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


@dataclass
class ConversationMessage:
    """Individual message in a conversation."""

    id: str
    content: str
    direction: str  # 'inbound' or 'outbound'
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Complete conversation context for AI processing."""

    customer_id: str
    phone: str
    messages: list[ConversationMessage]
    conversation_id: str
    last_activity: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class ConversationManagerTool(BaseTool):
    """
    Manages conversation state and context.

    This tool handles conversation state management including:
    - Loading conversations from Redis cache or database
    - Adding messages to conversations
    - Managing conversation context for AI processing
    - Caching conversations in Redis
    - Conversation expiration and summarization
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        super().__init__()
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None
        self.message_limit = 10  # Keep last 10 messages for context
        self.conversation_ttl = 3600  # 1 hour TTL for active conversations

    @property
    def name(self) -> str:
        return "conversation_manager"

    @property
    def description(self) -> str:
        return (
            "Manages conversation state and context. "
            "Handles loading conversations, adding messages, getting context, "
            "expiring conversations, and generating summaries."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": ["load", "add_message", "get_context", "expire", "summary"],
            },
            "phone": {
                "type": "string",
                "description": "Phone number for the conversation",
            },
            "content": {
                "type": "string",
                "description": "Message content (required for add_message action)",
            },
            "direction": {
                "type": "string",
                "description": "Message direction: 'inbound' or 'outbound' (required for add_message action)",
                "enum": ["inbound", "outbound"],
            },
            "metadata": {
                "type": "object",
                "description": "Optional metadata for the message",
            },
        }

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        action = kwargs.get("action")
        phone = kwargs.get("phone")

        if not action or not phone:
            return False

        if action == "add_message":
            content = kwargs.get("content")
            direction = kwargs.get("direction")
            return bool(content and direction and direction in ["inbound", "outbound"])

        return True

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the conversation management action."""
        if not self.validate_input(**kwargs):
            return ToolResult(
                success=False,
                data=None,
                error="Invalid parameters. Check action, phone, and required fields.",
            )

        try:
            await self._initialize_redis()

            action = kwargs["action"]
            phone = kwargs["phone"]

            if action == "load":
                context = await self._load_conversation(phone)
                return ToolResult(
                    success=True,
                    data=context,
                    metadata={"action": "load", "phone": phone},
                )

            elif action == "add_message":
                content = kwargs["content"]
                direction = kwargs["direction"]
                metadata = kwargs.get("metadata", {})

                context = await self._add_message(phone, content, direction, metadata)
                return ToolResult(
                    success=True,
                    data=context,
                    metadata={
                        "action": "add_message",
                        "phone": phone,
                        "message_count": len(context.messages),
                    },
                )

            elif action == "get_context":
                context = await self._load_conversation(phone)
                return ToolResult(
                    success=True,
                    data=context,
                    metadata={"action": "get_context", "phone": phone},
                )

            elif action == "expire":
                await self._expire_conversation(phone)
                return ToolResult(
                    success=True,
                    data={"expired": True},
                    metadata={"action": "expire", "phone": phone},
                )

            elif action == "summary":
                summary = await self._get_conversation_summary(phone)
                return ToolResult(
                    success=True,
                    data=summary,
                    metadata={"action": "summary", "phone": phone},
                )

            else:
                return ToolResult(
                    success=False, data=None, error=f"Unknown action: {action}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={
                    "error_type": type(e).__name__,
                    "action": kwargs.get("action"),
                },
            )

    async def _initialize_redis(self) -> None:
        """Initialize Redis connection if needed."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url, decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    @asynccontextmanager
    async def _get_redis(self):
        """Context manager for Redis operations."""
        if self.redis_client is None:
            await self._initialize_redis()
        if self.redis_client is None:
            raise RuntimeError("Redis client not initialized")
        try:
            yield self.redis_client
        except Exception as e:
            logger.error(f"Redis operation failed: {e}")
            raise

    async def _load_conversation(self, phone: str) -> ConversationContext | None:
        """Load conversation from Redis cache or database."""
        cache_key = f"conversation:{phone}"

        try:
            async with self._get_redis() as redis_client:
                # Try Redis cache first
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"Loading conversation from cache for {phone}")
                    return self._deserialize_conversation(json.loads(cached_data))

                # Fall back to database
                logger.info(f"Loading conversation from database for {phone}")
                return await self._load_from_database(phone)

        except Exception as e:
            logger.error(f"Failed to load conversation for {phone}: {e}")
            return None

    async def _load_from_database(self, phone: str) -> ConversationContext | None:
        """Load conversation from database."""
        try:
            async with get_db_session() as session:
                # Get customer
                customer = await get_customer_by_phone(session, phone)
                if not customer:
                    return None

                # Get active conversation
                conversation = await get_active_conversation(session, phone)
                if not conversation:
                    return None

                # Get recent messages
                messages = await get_conversation_messages(
                    session, conversation.id, limit=self.message_limit
                )

                # Convert to conversation messages
                conv_messages = []
                for msg in messages:
                    conv_msg = ConversationMessage(
                        id=str(msg.id),
                        content=msg.content,
                        direction=msg.direction,
                        timestamp=msg.timestamp,
                    )
                    conv_messages.append(conv_msg)

                context = ConversationContext(
                    customer_id=str(customer.id),
                    phone=phone,
                    messages=conv_messages,
                    conversation_id=str(conversation.id),
                    last_activity=conversation.last_message_at or datetime.now(UTC),
                    metadata=conversation.context
                    if conversation.context is not None
                    else {},
                )

                # Cache in Redis
                await self._cache_conversation(context)

                return context

        except Exception as e:
            logger.error(f"Failed to load conversation from database for {phone}: {e}")
            return None

    async def _add_message(
        self,
        phone: str,
        content: str,
        direction: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationContext:
        """Add a new message to the conversation."""
        if metadata is None:
            metadata = {}

        # Load existing conversation or create new one
        context = await self._load_conversation(phone)
        if not context:
            context = await self._create_new_conversation(phone)

        # Create new message
        message = ConversationMessage(
            id=f"msg_{datetime.now(UTC).timestamp()}",
            content=content,
            direction=direction,
            timestamp=datetime.now(UTC),
            metadata=metadata,
        )

        # Add to context
        context.messages.append(message)
        context.last_activity = datetime.now(UTC)

        # Trim to message limit
        if len(context.messages) > self.message_limit:
            context.messages = context.messages[-self.message_limit :]

        # Save to database
        await self._save_message_to_database(context, message)

        # Cache updated context
        await self._cache_conversation(context)

        logger.info(f"Added message to conversation for {phone}")
        return context

    async def _create_new_conversation(self, phone: str) -> ConversationContext:
        """Create a new conversation context."""
        async with get_db_session() as session:
            # Get or create customer
            customer = await get_customer_by_phone(session, phone)
            if not customer:
                customer = await create_customer(
                    session, CustomerCreate(phone=phone, square_customer_id=None)
                )

            # Create conversation
            conversation = await create_conversation(
                session, ConversationCreate(customer_id=customer.id, phone=phone)
            )

            context = ConversationContext(
                customer_id=str(customer.id),
                phone=phone,
                messages=[],
                conversation_id=str(conversation.id),
                last_activity=datetime.now(UTC),
            )

            logger.info(f"Created new conversation for {phone}")
            return context

    async def _save_message_to_database(
        self, context: ConversationContext, message: ConversationMessage
    ) -> None:
        """Save message to database."""
        async with get_db_session() as session:
            await add_message(
                session,
                MessageCreate(
                    conversation_id=context.conversation_id,
                    content=message.content,
                    direction=message.direction,
                ),
            )

    async def _cache_conversation(self, context: ConversationContext) -> None:
        """Cache conversation in Redis."""
        try:
            async with self._get_redis() as redis_client:
                cache_key = f"conversation:{context.phone}"
                serialized = self._serialize_conversation(context)

                await redis_client.setex(
                    cache_key, self.conversation_ttl, json.dumps(serialized)
                )

        except Exception as e:
            logger.error(f"Failed to cache conversation: {e}")
            # Don't raise - caching failure shouldn't break the flow

    def _serialize_conversation(self, context: ConversationContext) -> dict[str, Any]:
        """Serialize conversation context for Redis storage."""
        return {
            "customer_id": context.customer_id,
            "phone": context.phone,
            "messages": [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "direction": msg.direction,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in context.messages
            ],
            "conversation_id": context.conversation_id,
            "last_activity": context.last_activity.isoformat(),
            "metadata": context.metadata,
        }

    def _deserialize_conversation(self, data: dict[str, Any]) -> ConversationContext:
        """Deserialize conversation context from Redis storage."""
        messages = [
            ConversationMessage(
                id=msg["id"],
                content=msg["content"],
                direction=msg["direction"],
                timestamp=datetime.fromisoformat(msg["timestamp"]),
                metadata=msg["metadata"],
            )
            for msg in data["messages"]
        ]

        return ConversationContext(
            customer_id=data["customer_id"],
            phone=data["phone"],
            messages=messages,
            conversation_id=data["conversation_id"],
            last_activity=datetime.fromisoformat(data["last_activity"]),
            metadata=data["metadata"],
        )

    async def _expire_conversation(self, phone: str) -> None:
        """Manually expire a conversation."""
        cache_key = f"conversation:{phone}"
        try:
            async with self._get_redis() as redis_client:
                await redis_client.delete(cache_key)
            logger.info(f"Expired conversation for {phone}")
        except Exception as e:
            logger.error(f"Failed to expire conversation for {phone}: {e}")
            raise

    async def _get_conversation_summary(self, phone: str) -> dict[str, Any]:
        """Get a summary of the conversation state."""
        context = await self._load_conversation(phone)
        if not context:
            return {"exists": False}

        return {
            "exists": True,
            "message_count": len(context.messages),
            "last_activity": context.last_activity.isoformat(),
            "conversation_id": context.conversation_id,
        }

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info("Redis connection closed")
