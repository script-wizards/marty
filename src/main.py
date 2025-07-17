import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from urllib.parse import urlparse

import structlog
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from alembic.config import Config as AlembicConfig
from src.ai_client import ConversationMessage, generate_ai_response
from src.database import (
    ConversationCreate,
    CustomerCreate,
    MessageCreate,
    add_message,
    close_db,
    create_conversation,
    create_customer,
    engine,
    get_active_conversation,
    get_conversation_messages,
    get_customer_by_phone,
    get_db,
    init_db,
)
from src.sms_handler import router as sms_router


def rename_event_to_message(logger, method_name, event_dict):
    """Rename 'event' field to 'message' for Railway compatibility."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.format_exc_info,
        rename_event_to_message,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configure standard logging to work with structlog
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
)

logger = structlog.get_logger(__name__)


def validate_environment_variables() -> None:
    """Validate required environment variables on startup."""
    required_vars = [
        "ANTHROPIC_API_KEY",
        "HARDCOVER_API_TOKEN",
    ]

    # SMS-specific validation (only if SMS features are enabled)
    sms_enabled = os.getenv("SMS_MULTI_MESSAGE_ENABLED", "true").lower() == "true"
    if sms_enabled:
        sms_required_vars = [
            "SINCH_API_TOKEN",
            "SINCH_SERVICE_PLAN_ID",
            "SINCH_WEBHOOK_SECRET",
        ]
        required_vars.extend(sms_required_vars)

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    logger.info(f"Environment: {os.getenv('ENV', 'development')}")
    logger.info(f"Database URL configured: {bool(os.getenv('DATABASE_URL'))}")
    logger.info(f"Anthropic API key configured: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
    logger.info(
        f"Hardcover API key configured: {bool(os.getenv('HARDCOVER_API_TOKEN'))}"
    )
    if sms_enabled:
        logger.info(f"SMS features enabled: {bool(os.getenv('SINCH_API_TOKEN'))}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan (startup and shutdown)."""
    try:
        validate_environment_variables()
        logger.info("Environment variables validated")

        await init_db()
        logger.info("Database initialized successfully")

        logger.info("Marty chatbot started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    try:
        logger.info("Shutting down Marty chatbot...")

        await close_db()

        logger.info("Marty chatbot shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        # Don't raise during shutdown to allow graceful termination


app = FastAPI(
    title="Marty - Dungeon Books SMS Wizard",
    version="0.1.0",
    description="AI-powered SMS chatbot for book recommendations and purchases",
    lifespan=lifespan,
)

app.include_router(sms_router)


@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db), include_migrations: bool = False
):
    """Enhanced health check endpoint with database connectivity.

    Args:
        include_migrations: Whether to include migration status check (default: False)
                           Can be enabled with ?include_migrations=true
    """
    try:
        result = await db.execute(text("SELECT 1"))
        db_status = "ok" if result.fetchone() else "error"

        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./marty.db")
        try:
            parsed_url = urlparse(db_url)
            db_type = (
                parsed_url.scheme.split("+")[0] if parsed_url.scheme else "unknown"
            )
        except Exception:
            db_type = "unknown"

        response = {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "0.1.0",
            "database": {"status": db_status, "type": db_type},
            "environment": os.getenv("ENV", "development"),
        }

        if include_migrations:
            migration_status = "ok"
            try:
                alembic_cfg = AlembicConfig("alembic.ini")
                from alembic.runtime.migration import MigrationContext
                from alembic.script import ScriptDirectory

                # Use sync connection from engine for migration check
                if engine:
                    sync_engine = engine.sync_engine
                    with sync_engine.connect() as conn:
                        migration_ctx = MigrationContext.configure(conn)
                        current_rev = migration_ctx.get_current_revision()

                    script_dir = ScriptDirectory.from_config(alembic_cfg)
                    head_rev = script_dir.get_current_head()

                    if current_rev != head_rev:
                        migration_status = "pending"
                else:
                    migration_status = "unknown"
            except Exception as e:
                logger.debug(f"Could not check migration status: {e}")
                migration_status = "unknown"

            response["migrations"] = {"status": migration_status}

        return response
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": "Database connectivity failed",
                "database": {"status": "error"},
            },
        ) from e


class ChatRequest(BaseModel):
    message: str
    phone: str


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    customer_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint with Claude AI integration."""
    try:
        customer = await get_customer_by_phone(db, request.phone)
        if not customer:
            customer_data = CustomerCreate(
                phone=request.phone,
                name=None,
                email=None,
                square_customer_id=None,
            )
            customer = await create_customer(db, customer_data)

        conversation = await get_active_conversation(db, request.phone)
        if not conversation:
            conversation_data = ConversationCreate(
                customer_id=customer.id, phone=request.phone
            )
            conversation = await create_conversation(db, conversation_data)

        incoming_message = MessageCreate(
            conversation_id=conversation.id,
            direction="inbound",
            content=request.message,
        )
        await add_message(db, incoming_message)

        messages = await get_conversation_messages(db, conversation.id, limit=10)
        conversation_history = [
            ConversationMessage(
                role="user" if msg.direction == "inbound" else "assistant",
                content=msg.content,
                timestamp=msg.timestamp,
            )
            for msg in reversed(messages)  # Reverse to get chronological order
        ]

        response_text = await generate_ai_response(
            user_message=request.message,
            conversation_history=conversation_history[
                :-1
            ],  # Exclude the message we just added
            customer_context={
                "customer_id": customer.id,
                "phone": customer.phone,
                "name": customer.name,
                "current_time": datetime.now(UTC).isoformat(),
                "current_date": datetime.now(UTC).strftime("%Y-%m-%d"),
                "current_day": datetime.now(UTC).strftime("%A"),
            },
        )

        outgoing_message = MessageCreate(
            conversation_id=conversation.id, direction="outbound", content=response_text
        )
        await add_message(db, outgoing_message)

        return ChatResponse(
            response=response_text,
            conversation_id=conversation.id,
            customer_id=customer.id,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed") from e


if __name__ == "__main__":
    import asyncio
    import signal

    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    port = int(os.getenv("PORT", "8000"))
    config.bind = [f"[::]:{port}"]  # Dual-stack IPv4/IPv6 binding for Railway
    config.use_reloader = os.getenv("ENV") == "development"
    config.graceful_timeout = 30  # Allow 30 seconds for graceful shutdown

    async def shutdown_trigger():
        shutdown_event = asyncio.Event()

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            shutdown_event.set()

        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, "SIGINT"):
            signal.signal(signal.SIGINT, signal_handler)

        await shutdown_event.wait()

    async def serve_with_graceful_shutdown():
        try:
            await hypercorn.asyncio.serve(
                app, config, shutdown_trigger=shutdown_trigger
            )
        except asyncio.CancelledError:
            logger.info("Server shutdown cancelled")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

    asyncio.run(serve_with_graceful_shutdown())
