## Project Blueprint: Dungeon Books RCS Wizard

### Phase 1: Core Infrastructure Setup

1. **Modern Python Foundation**

    - FastAPI application with async support
    - Hypercorn ASGI server with dual stack IPv4/IPv6
    - uv for dependency management
    - pyproject.toml configuration
    - Ruff linting and formatting
    - Pre-commit hooks
    - Pytest with async support
    - Comprehensive test coverage

2. **Database Schema & Connection**

    - Set up Supabase connection with async SQLAlchemy
    - Create database schema with Alembic migrations
    - Implement Pydantic models for validation
    - Add async connection pooling
3. **Production Web Service**

    - FastAPI application with proper structure
    - Health check endpoint with database connectivity
    - Error handling middleware
    - Structured logging with correlation IDs
    - Railway deployment configuration
    - Environment variable validation

### Phase 2: External Service Integration

4. **SMS/RCS Provider Integration**

    - Webhook signature verification
    - Message parsing with Pydantic
    - Response sending with background tasks
5. **Square API Integration**

    - Customer lookup by phone (async API calls)
    - Customer data caching with Redis
    - Order creation with proper error handling
6. **Book Data Integration**

    - Hardcover API connection (async API calls)
    - Book search functionality with caching
    - Inventory management with updates

### Phase 3: AI & Conversation Management

7. **Conversation State Management**

    - Message storage with database
    - Conversation threading with Redis
    - Context retrieval with efficient queries
8. **Claude AI Integration**

    - Claude client with proper timeout handling (async API calls)
    - Context injection with Pydantic models
    - Response generation with background tasks
9. **Marty Personality Implementation**

    - System prompt refinement with dynamic context
    - Response processing with personality layer
    - Message formatting for SMS constraints

### Phase 4: Commerce & Polish

10. **Order Processing Flow**

    - Purchase intent detection with LLM
    - Fulfillment options with async processing
    - Payment link generation with Square
11. **Production Features**

    - Rate limiting with Redis
    - Comprehensive error handling
    - Monitoring and metrics with structured logging
12. **End-to-End Testing & Polish**

    - Integration testing with test containers
    - Performance optimization with async patterns
    - Demo preparation with realistic data

## Updated Iterative Breakdown

### Step 1: Database Foundation

- 1.1 SQLAlchemy setup with Supabase (async for I/O, sync for logic)
- 1.2 Pydantic models for all data structures
- 1.3 Alembic migrations for schema management
- 1.4 Connection pooling with asyncpg
- 1.5 Integration tests with test database

### Step 2: Production Web Service Enhancement

- 2.1 FastAPI app with modern structure
- 2.2 Configuration management with pyproject.toml
- 2.3 Health check endpoint
- 2.4 Environment variable validation on startup
- 2.5 Railway deployment configuration

### Step 3: SMS Webhook with Background Tasks

- 3.1 FastAPI webhook route with Pydantic validation
- 3.2 HMAC signature verification middleware
- 3.3 Background task queue with FastAPI
- 3.4 Redis for message queueing
- 3.5 Mock SMS provider for testing

### Step 4: Customer Service

- 4.1 Square API client with httpx (async for API calls)
- 4.2 Customer search with Redis caching
- 4.3 Customer creation with proper error handling
- 4.4 Background sync with Square data
- 4.5 Integration tests with mocked Square API

### Step 5: Book Service with Modern Caching

- 5.1 Hardcover API client (async for API calls)
- 5.2 Book search with Redis caching
- 5.3 Inventory management with updates
- 5.4 Book data enrichment with background tasks
- 5.5 Cache invalidation strategies

### Step 6: Conversation Manager with Redis

- 6.1 Message storage with database (async I/O)
- 6.2 Conversation threading with Redis
- 6.3 Context window management with efficient queries
- 6.4 Book mention tracking with text processing
- 6.5 Timeout handling with Redis TTL

### Step 7: AI Integration

- 7.1 Claude client setup with proper timeouts (async for API calls)
- 7.2 Pydantic models for AI requests/responses
- 7.3 Context injection with efficient serialization
- 7.4 Response generation with background tasks
- 7.5 Message splitting with intelligent breaks

### Step 8: Marty Personality with Modern Patterns

- 8.1 System prompt management with template engine
- 8.2 Dynamic context building with Pydantic
- 8.3 Response personality layer with text processing
- 8.4 Error message personality with fallback responses
- 8.5 A/B testing framework for personality tweaks

### Step 9: Purchase Flow with State Management

- 9.1 Intent detection with LLM and confidence scoring
- 9.2 Book reference resolution with vector search
- 9.3 Order creation flow with state machines
- 9.4 Payment link generation with Square async API
- 9.5 Fulfillment handling with background tasks

### Step 10: Production Features with Monitoring

- 10.1 Rate limiting with Redis and sliding windows
- 10.2 Comprehensive error handling with structured logging
- 10.3 Monitoring integration with OpenTelemetry
- 10.4 Performance optimization (async for I/O, sync for logic)
- 10.5 End-to-end testing with realistic scenarios

## Technology Stack Updates

### Core Stack
- **Web Framework**: FastAPI (async, modern, fast)
- **ASGI Server**: Hypercorn (dual stack IPv4/IPv6)
- **Database**: Supabase + async SQLAlchemy
- **Caching**: Redis for session/cache management
- **Dependency Management**: uv + pyproject.toml
- **Code Quality**: ruff + pre-commit hooks
- **Testing**: pytest + pytest-asyncio
- **Deployment**: Railway with modern configuration

### Modern Patterns
- **Async where it helps**: External APIs, database I/O, webhooks
- **Sync for simplicity**: Business logic, data processing, formatting
- **Pydantic models**: Data validation and serialization
- **Background tasks**: FastAPI background tasks for non-blocking operations
- **Structured logging**: JSON logs with correlation IDs
- **Circuit breakers**: Resilient external API calls
- **Observability**: OpenTelemetry for monitoring

---

## Updated Code Generation Prompts

### Prompt 1: Database Foundation

```text
Create a modern database layer for a FastAPI bookstore SMS chatbot using SQLAlchemy and Pydantic.

Requirements:
1. Create a `database.py` module with SQLAlchemy setup (async for I/O operations)
2. Use Pydantic models for data validation and serialization
3. Implement Alembic migrations for schema management
4. Create these tables using SQLAlchemy models:
   - customers (id, phone, square_customer_id, preferences, created_at, updated_at)
   - conversations (id, customer_id, phone, messages, mentioned_books, last_activity, active)
   - books (id, isbn, title, author, publisher, metadata, created_at)
   - inventory (id, book_id, in_stock_count, source, updated_at)
   - orders (id, customer_id, book_id, status, fulfillment_type, square_order_id, total_amount, created_at)
   - rate_limits (phone, message_count, window_start)

5. Implement CRUD operations (async for database I/O, sync for data processing)
6. Use connection pooling with asyncpg and Supabase
7. Add comprehensive tests with pytest and pytest-asyncio
8. Include proper logging with correlation IDs
9. Use environment variables: SUPABASE_URL, SUPABASE_SERVICE_KEY
10. Add type hints and docstrings throughout

Build on the existing FastAPI application structure we have.
```

### Prompt 2: SMS Webhook with Background Tasks

```text
Extend the FastAPI application to handle SMS webhooks efficiently.

Requirements:
1. Create `sms_handler.py` module with FastAPI dependency injection
2. Add POST /webhook/sms endpoint using Pydantic models for validation
3. Implement HMAC signature verification as FastAPI middleware
4. Use FastAPI background tasks for non-blocking message processing
5. Integrate with Redis for message queuing and rate limiting
6. Create comprehensive Pydantic models for:
   - Webhook payloads
   - Message validation
   - Response formats
7. Add structured logging with correlation IDs
8. Implement rate limiting with Redis sliding windows
9. Create mock SMS provider for testing
10. Use pytest and pytest-asyncio for comprehensive testing
11. Environment variables: SMOBI_WEBHOOK_SECRET, REDIS_URL
12. Add proper OpenTelemetry tracing

Build on the existing FastAPI app with database integration.
```

### Prompt 3: Square Integration

```text
Create a modern Square API integration with proper error handling and caching.

Requirements:
1. Create `square_client.py` module using httpx (async for API calls)
2. Implement Pydantic models for Square API requests/responses
3. Add these methods:
   - search_customer_by_phone(phone: str) -> Optional[CustomerModel]
   - create_customer(customer_data: CreateCustomerModel) -> CustomerModel
   - get_customer_orders(customer_id: str) -> List[OrderModel]
4. Use Redis for customer data caching with TTL
5. Implement circuit breaker pattern for resilient API calls
6. Add comprehensive error handling with retry logic
7. Use FastAPI background tasks for data synchronization
8. Add proper logging with correlation IDs and metrics
9. Create mock Square responses for testing
10. Use pytest with proper fixtures (async tests where needed)
11. Environment variables: SQUARE_ACCESS_TOKEN, SQUARE_APPLICATION_ID, SQUARE_ENVIRONMENT
12. Add OpenTelemetry tracing for API calls

Integrate with existing database and FastAPI structure.
```

### Prompt 4: Book Data Service

```text
Create a modern book data service with intelligent caching and text processing.

Requirements:
1. Create `book_service.py` module with Hardcover API client (async for API calls)
2. Implement Pydantic models for book data and inventory
3. Add these methods:
   - search_books(query: str, limit: int = 5) -> List[BookModel]
   - get_book_details(book_id: str) -> Optional[BookModel]
   - check_inventory(book_id: str) -> InventoryModel
   - extract_book_mentions(text: str) -> List[BookReference]
4. Use Redis for intelligent caching with proper invalidation
5. Implement text processing for book matching (start simple, can add ML later)
6. Add background tasks for inventory updates
7. Create bookshop.org affiliate link generation
8. Use httpx with proper timeout handling
9. Add comprehensive error handling and fallback responses
10. Create mock Hardcover API for testing
11. Use pytest with realistic test data (async tests where needed)
12. Environment variables: HARDCOVER_API_KEY, BOOKSHOP_AFFILIATE_ID
13. Add OpenTelemetry metrics and tracing

Integrate with existing database and caching infrastructure.
```

### Prompt 5: AI Integration

```text
Create a modern Claude AI integration with proper context management and background processing.

Requirements:
1. Create `ai_client.py` module with Claude client (async for API calls)
2. Implement Pydantic models for AI requests and responses
3. Add these methods:
   - generate_response(context: ConversationContext) -> AIResponse
   - build_system_prompt(customer: CustomerModel, context: Dict) -> str
   - parse_ai_response(response: str) -> ParsedResponse
4. Use background tasks for AI processing to avoid blocking webhooks
5. Implement intelligent context window management
6. Add response caching with Redis for similar queries
7. Create fallback responses for AI failures
8. Use structured logging with AI metrics
9. Add proper timeout handling and circuit breakers
10. Create mock Claude API for testing
11. Use pytest with conversation scenarios (async tests where needed)
12. Environment variables: CLAUDE_API_KEY, CLAUDE_MODEL
13. Add OpenTelemetry tracing for AI calls
14. Keep response processing simple initially

Build on existing conversation management and caching infrastructure.
```

### Prompt 6: Production Features with Monitoring

```text
Add comprehensive production features to the FastAPI application with modern observability.

Requirements:
1. Create `production_features.py` module with production utilities
2. Implement Redis-based rate limiting with sliding windows
3. Add comprehensive error handling with structured logging
4. Create health check enhancements:
   - Database connectivity
   - Redis connectivity
   - External API health
   - System metrics
5. Add OpenTelemetry integration:
   - Distributed tracing
   - Metrics collection
   - Custom spans for business logic
6. Implement graceful shutdown handling
7. Add environment variable validation on startup
8. Create middleware for:
   - Request correlation IDs
   - Response time tracking
   - Error rate monitoring
9. Use pytest for production feature testing (async where needed)
10. Add load testing scenarios with realistic data
11. Create deployment configuration for Railway
12. Add security enhancements:
    - Input validation
    - Rate limit bypass prevention
    - CORS configuration

Complete the production-ready FastAPI application with pragmatic patterns.
```
