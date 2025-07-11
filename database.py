"""
Database module for Marty SMS Bookstore Chatbot.
Provides SQLAlchemy models, Pydantic schemas, and async database operations.
"""

import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    Numeric,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pydantic import BaseModel, Field, ConfigDict, validator
from pydantic.types import UUID4

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
    square_customer_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=func.now()
    )

    # Relationships
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="customer"
    )
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer")


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
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Store conversation context and metadata
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    mentioned_books: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="conversations"
    )
    messages: Mapped[List["Message"]] = relationship(
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
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # SMS/RCS metadata
    message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
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
    isbn: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    publication_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # External IDs
    hardcover_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    bookshop_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # hardcover, paperback, ebook
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=func.now()
    )

    # Relationships
    inventory: Mapped[List["Inventory"]] = relationship(
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
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    # Availability
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
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
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=True
    )

    # Order details
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending, confirmed, shipped, delivered, cancelled
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Square integration
    square_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    payment_status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, paid, failed

    # Fulfillment
    fulfillment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # pickup, shipping, digital
    shipping_address: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=func.now()
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order")


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
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    square_customer_id: Optional[str] = Field(None, max_length=100)


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    square_customer_id: Optional[str] = Field(None, max_length=100)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    square_customer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    customer_id: str
    phone: str
    status: str = "active"
    context: Optional[Dict[str, Any]] = None
    mentioned_books: Optional[List[str]] = None


class ConversationUpdate(BaseModel):
    status: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    mentioned_books: Optional[List[str]] = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    phone: str
    status: str
    last_message_at: datetime
    created_at: datetime
    context: Optional[Dict[str, Any]] = None
    mentioned_books: Optional[List[str]] = None


class MessageCreate(BaseModel):
    conversation_id: str
    direction: str = Field(..., pattern="^(inbound|outbound)$")
    content: str = Field(..., min_length=1)
    message_id: Optional[str] = None
    status: str = "pending"


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    direction: str
    content: str
    timestamp: datetime
    message_id: Optional[str] = None
    status: str


class BookCreate(BaseModel):
    isbn: Optional[str] = Field(None, max_length=20)
    title: str = Field(..., min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    publisher: Optional[str] = Field(None, max_length=200)
    publication_date: Optional[datetime] = None
    hardcover_id: Optional[str] = Field(None, max_length=100)
    bookshop_url: Optional[str] = Field(None, max_length=500)
    genre: Optional[str] = Field(None, max_length=100)
    format: Optional[str] = Field(None, max_length=50)
    page_count: Optional[int] = Field(None, ge=0)


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    publisher: Optional[str] = Field(None, max_length=200)
    publication_date: Optional[datetime] = None
    hardcover_id: Optional[str] = Field(None, max_length=100)
    bookshop_url: Optional[str] = Field(None, max_length=500)
    genre: Optional[str] = Field(None, max_length=100)
    format: Optional[str] = Field(None, max_length=50)
    page_count: Optional[int] = Field(None, ge=0)


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    isbn: Optional[str] = None
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    publisher: Optional[str] = None
    publication_date: Optional[datetime] = None
    hardcover_id: Optional[str] = None
    bookshop_url: Optional[str] = None
    genre: Optional[str] = None
    format: Optional[str] = None
    page_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class InventoryCreate(BaseModel):
    book_id: str
    location: str = Field(..., max_length=100)
    quantity: int = Field(..., ge=0)
    reserved: int = Field(0, ge=0)
    price: Optional[Decimal] = Field(None, ge=0)
    available: bool = True


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    reserved: Optional[int] = Field(None, ge=0)
    price: Optional[Decimal] = Field(None, ge=0)
    available: Optional[bool] = None


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    book_id: str
    location: str
    quantity: int
    reserved: int
    price: Optional[Decimal] = None
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
