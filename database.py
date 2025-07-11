"""
Database module for Marty SMS Bookstore Chatbot.
Provides SQLAlchemy models, Pydantic schemas, and async database operations.
"""

import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./marty.db")

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()


# SQLAlchemy Models
class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    square_customer_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=func.now()
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="customer"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, ended, timeout
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Store conversation context and metadata
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    mentioned_books: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="conversations"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # inbound, outbound
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # SMS/RCS metadata
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, sent, delivered, failed

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    # Index for efficient queries
    __table_args__ = (
        Index("idx_conversation_timestamp", "conversation_id", "timestamp"),
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    isbn: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(200), nullable=True)
    publication_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # External IDs
    hardcover_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    bookshop_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Metadata
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    format: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # hardcover, paperback, ebook
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=func.now()
    )

    # Relationships
    inventory: Mapped[list["Inventory"]] = relationship(
        "Inventory", back_populates="book"
    )


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id"), nullable=False
    )
    location: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # store, warehouse, bookshop
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Availability
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="inventory")

    # Ensure one inventory record per book per location
    __table_args__ = (UniqueConstraint("book_id", "location", name="uq_book_location"),)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=True
    )

    # Order details
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending, confirmed, shipped, delivered, cancelled
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Square integration
    square_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, paid, failed

    # Fulfillment
    fulfillment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # pickup, shipping, digital
    shipping_address: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=func.now()
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id"), nullable=False
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    book: Mapped["Book"] = relationship("Book")


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    identifier: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # phone number or IP
    limit_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # sms, api, etc.
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Efficient lookups
    __table_args__ = (
        Index("idx_identifier_type", "identifier", "limit_type"),
        Index("idx_expires_at", "expires_at"),
    )


# Pydantic Schemas
class CustomerCreate(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=255)
    square_customer_id: str | None = Field(None, max_length=100)


class CustomerUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=255)
    square_customer_id: str | None = Field(None, max_length=100)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    square_customer_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    customer_id: str
    phone: str
    status: str = "active"
    context: dict[str, Any] | None = None
    mentioned_books: list[str] | None = None


class ConversationUpdate(BaseModel):
    status: str | None = None
    context: dict[str, Any] | None = None
    mentioned_books: list[str] | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    phone: str
    status: str
    last_message_at: datetime
    created_at: datetime
    context: dict[str, Any] | None = None
    mentioned_books: list[str] | None = None


class MessageCreate(BaseModel):
    conversation_id: str
    direction: str = Field(..., pattern="^(inbound|outbound)$")
    content: str = Field(..., min_length=1)
    message_id: str | None = None
    status: str = "pending"


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    direction: str
    content: str
    timestamp: datetime
    message_id: str | None = None
    status: str


class BookCreate(BaseModel):
    isbn: str | None = Field(None, max_length=20)
    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = Field(None, max_length=500)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    publisher: str | None = Field(None, max_length=200)
    publication_date: datetime | None = None
    hardcover_id: str | None = Field(None, max_length=100)
    bookshop_url: str | None = Field(None, max_length=500)
    genre: str | None = Field(None, max_length=100)
    format: str | None = Field(None, max_length=50)
    page_count: int | None = Field(None, ge=0)


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    author: str | None = Field(None, max_length=500)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    publisher: str | None = Field(None, max_length=200)
    publication_date: datetime | None = None
    hardcover_id: str | None = Field(None, max_length=100)
    bookshop_url: str | None = Field(None, max_length=500)
    genre: str | None = Field(None, max_length=100)
    format: str | None = Field(None, max_length=50)
    page_count: int | None = Field(None, ge=0)


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    isbn: str | None = None
    title: str
    author: str | None = None
    description: str | None = None
    price: Decimal | None = None
    publisher: str | None = None
    publication_date: datetime | None = None
    hardcover_id: str | None = None
    bookshop_url: str | None = None
    genre: str | None = None
    format: str | None = None
    page_count: int | None = None
    created_at: datetime
    updated_at: datetime


class InventoryCreate(BaseModel):
    book_id: str
    location: str = Field(..., max_length=100)
    quantity: int = Field(..., ge=0)
    reserved: int = Field(0, ge=0)
    price: Decimal | None = Field(None, ge=0)
    available: bool = True


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(None, ge=0)
    reserved: int | None = Field(None, ge=0)
    price: Decimal | None = Field(None, ge=0)
    available: bool | None = None


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    book_id: str
    location: str
    quantity: int
    reserved: int
    price: Decimal | None = None
    available: bool
    last_updated: datetime


# Database Session Management
async def get_db() -> AsyncSession:
    """Get database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
