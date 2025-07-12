import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    ConversationCreate,
    CustomerCreate,
    MessageCreate,
    add_message,
    close_db,
    create_conversation,
    create_customer,
    get_active_conversation,
    get_customer_by_phone,
    get_db,
    init_db,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan (startup and shutdown)."""
    # Startup
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


app = FastAPI(
    title="Marty - Dungeon Books RCS Wizard",
    version="0.1.0",
    description="AI-powered SMS chatbot for book recommendations and purchases",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Enhanced health check endpoint with database connectivity."""
    try:
        # Test database connectivity
        result = await db.execute(text("SELECT 1"))
        db_status = "ok" if result.fetchone() else "error"

        # Get database URL info (without credentials)
        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./marty.db")
        db_type = db_url.split("://")[0].split("+")[0] if "://" in db_url else "unknown"

        return {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "0.1.0",
            "database": {"status": db_status, "type": db_type},
            "environment": os.getenv("ENV", "development"),
        }
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


# Chat endpoint for testing
class ChatRequest(BaseModel):
    message: str
    phone: str


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    customer_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint for testing conversations."""
    try:
        # Get or create customer
        customer = await get_customer_by_phone(db, request.phone)
        if not customer:
            customer_data = CustomerCreate(
                phone=request.phone,
                first_name=None,
                last_name=None,
                email=None,
                square_customer_id=None,
            )
            customer = await create_customer(db, customer_data)

        # Get or create active conversation
        conversation = await get_active_conversation(db, request.phone)
        if not conversation:
            conversation_data = ConversationCreate(
                customer_id=customer.id, phone=request.phone
            )
            conversation = await create_conversation(db, conversation_data)

        # Add incoming message
        incoming_message = MessageCreate(
            conversation_id=conversation.id,
            direction="inbound",
            content=request.message,
        )
        await add_message(db, incoming_message)

        # For now, just echo the message (we'll add AI later)
        response_text = f"Echo: {request.message}"

        # Add outgoing message
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
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["[::]:8000"]  # Dual stack IPv4/IPv6 binding
    config.use_reloader = True

    import asyncio

    asyncio.run(hypercorn.asyncio.serve(app, config))  # type: ignore
