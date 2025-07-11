# Dungeon Books RCS Wizard - Implementation Checklist

## Initial Setup

### Environment & Tools

- [x] Create new GitHub repository
- [x] Set up local development environment
- [x] Install Python 3.13+
- [x] Create uv virtual environment
- [x] Initialize git repository
- [x] Create .gitignore (include .env, venv/, **pycache**)
- [ ] Create README.md with project overview

### External Services Setup

- [ ] Create Supabase account and project
- [ ] Get Supabase URL and service key
- [ ] Create Square developer account
- [ ] Get Square sandbox credentials
- [ ] Apply for Hardcover API access
- [ ] Get Hardcover API key
- [x] Register with Anthropic for Claude API
- [x] Get Claude API key
- [x] Schedule meeting with Smobi representative
- [x] Set up Bookshop.org affiliate account
- [x] Create Railway account

### Configuration

- [ ] Create .env.example file with all required variables
- [ ] Create local .env file with development credentials
- [ ] Document all environment variables in README

### Modern Python Tooling

- [x] Set up uv for dependency management
- [x] Configure pyproject.toml with all dependencies
- [x] Set up ruff for linting and formatting
- [x] Configure pre-commit hooks
- [x] Set up pytest with async support
- [x] Configure dual stack IPv4/IPv6 networking
- [x] Set up comprehensive test coverage

## Step 1: Database Foundation

### Database Schema

- [ ] Create Supabase project
- [ ] Set up Alembic for database migrations
- [ ] Create SQLAlchemy models for all tables
- [ ] Write Alembic migration for customers table
- [ ] Write Alembic migration for conversations table
- [ ] Write Alembic migration for books table
- [ ] Write Alembic migration for inventory table
- [ ] Write Alembic migration for orders table
- [ ] Write Alembic migration for rate_limits table
- [ ] Execute migrations in Supabase
- [ ] Verify all tables created correctly

### Database Module

- [ ] Create `database.py` module with SQLAlchemy (async for I/O)
- [ ] Implement database session management
- [ ] Create Pydantic models for data validation
- [ ] Set up asyncpg connection pooling with Supabase
- [ ] Implement CRUD operations for customers
- [ ] Implement CRUD operations for conversations
- [ ] Implement CRUD operations for books
- [ ] Implement CRUD operations for inventory
- [ ] Implement CRUD operations for orders
- [ ] Implement CRUD operations for rate_limits
- [ ] Add comprehensive error handling
- [ ] Add structured logging with correlation IDs
- [ ] Add type hints throughout

### Database Testing

- [ ] Create `test_database.py` with pytest
- [ ] Write tests for connection management
- [ ] Write tests for each CRUD operation
- [ ] Test error scenarios with proper handling
- [ ] Test connection pooling behavior
- [ ] Verify database operations work correctly
- [ ] Test Pydantic model validation
- [ ] Use pytest-asyncio where needed for I/O tests

## Step 2: Web Service Foundation

### FastAPI Application

- [x] Create `main.py` with FastAPI app (used FastAPI instead of Flask)
- [x] Implement configuration from environment
- [x] Create config classes for different environments
- [x] Set up FastAPI app initialization
- [x] Configure CORS if needed
- [x] Set up dual stack IPv4/IPv6 binding with Hypercorn

### Health Check

- [x] Create GET /health endpoint
- [ ] Check database connectivity
- [x] Return proper status format
- [ ] Add timestamp to response
- [x] Include version information

### Logging & Error Handling

- [x] Set up structured JSON logging (via ruff configuration)
- [ ] Implement correlation ID generation
- [x] Create error handling middleware (FastAPI built-in)
- [x] Map exceptions to HTTP status codes
- [x] Ensure no internal errors leak
- [x] Test error responses

### Deployment Config

- [x] Create requirements.txt (using pyproject.toml instead)
- [ ] Create railway.toml
- [ ] Add Procfile if needed
- [x] Configure port binding
- [x] Set up environment detection

### Web Service Testing

- [x] Create `test_health.py` (comprehensive tests)
- [x] Test health endpoint
- [x] Test error handling
- [x] Test configuration loading
- [x] Test logging output
- [ ] Verify Railway configuration

## Step 3: SMS Webhook Handler

### Webhook Endpoint

- [ ] Create `sms_handler.py` module with FastAPI dependency injection
- [ ] Implement POST /webhook/sms endpoint with Pydantic validation
- [ ] Create Pydantic models for webhook payloads
- [ ] Validate required fields with Pydantic
- [ ] Add structured logging with correlation IDs
- [ ] Set up Redis for message queuing

### Security

- [ ] Implement HMAC signature verification as FastAPI middleware
- [ ] Test with valid signatures
- [ ] Test with invalid signatures
- [ ] Handle missing signature header
- [ ] Add IP allowlist if provided by Smobi
- [ ] Add request validation with Pydantic

### Message Processing

- [ ] Store incoming messages in database
- [ ] Mark messages as pending
- [ ] Return 200 immediately (non-blocking pattern)
- [ ] Use FastAPI background tasks for message processing
- [ ] Set up Redis message queuing
- [ ] Add timestamp tracking

### Rate Limiting

- [ ] Implement Redis-based rate limiting with sliding windows
- [ ] Track per-phone number limits
- [ ] Handle rate limit exceeded
- [ ] Clean up old rate limit records automatically
- [ ] Test rate limiting logic with Redis

### Mock SMS Provider

- [ ] Create mock response function
- [ ] Log outgoing messages with structured logging
- [ ] Simulate SMS sending with delays
- [ ] Add response delay simulation
- [ ] Track sent messages in Redis

### Webhook Testing

- [ ] Create `test_sms_handler.py` with pytest
- [ ] Test valid webhook requests
- [ ] Test signature verification
- [ ] Test missing fields with Pydantic validation
- [ ] Test rate limiting with Redis
- [ ] Test database integration
- [ ] Test FastAPI background tasks

## Step 4: Square Customer Integration (Redis Caching)

### Square Client

- [ ] Create `square_client.py` module with httpx client (async for API calls)
- [ ] Implement SquareClient class
- [ ] Create Pydantic models for Square API requests/responses
- [ ] Configure Square SDK with proper patterns
- [ ] Handle environment switching (sandbox/prod)
- [ ] Add structured logging with correlation IDs
- [ ] Add OpenTelemetry tracing for API calls

### Customer Operations

- [ ] Implement search_customer_by_phone
- [ ] Implement get_customer
- [ ] Implement create_customer
- [ ] Implement get_customer_orders
- [ ] Handle Square API errors with circuit breaker pattern
- [ ] Add retry logic with exponential backoff
- [ ] Create comprehensive error handling

### Customer Sync with Redis

- [ ] Check local database first
- [ ] Search Square if not found locally
- [ ] Create local customer record
- [ ] Sync Square data to local database
- [ ] Implement Redis caching with TTL
- [ ] Use FastAPI background tasks for sync operations

### Integration

- [ ] Integrate with SMS handler using dependency injection
- [ ] Add customer lookup on message
- [ ] Store customer_id in conversation
- [ ] Handle new vs returning customers
- [ ] Update conversation with customer data
- [ ] Use Redis for customer session management

### Square Testing

- [ ] Create `test_square_client.py` with pytest
- [ ] Mock Square API responses with fixtures
- [ ] Test customer search
- [ ] Test customer creation
- [ ] Test error handling with circuit breakers
- [ ] Test Redis cache behavior
- [ ] Test OpenTelemetry tracing

## Step 5: Book Data Service (Text Processing)

### Hardcover Client

- [ ] Create `book_service.py` module with httpx client (async for API calls)
- [ ] Implement HardcoverClient class
- [ ] Create Pydantic models for book data and inventory
- [ ] Add authentication headers
- [ ] Implement search_books method
- [ ] Implement get_book_details method
- [ ] Handle API errors with circuit breaker pattern
- [ ] Add OpenTelemetry tracing for API calls

### Inventory Management

- [ ] Implement check_inventory
- [ ] Implement update_inventory
- [ ] Track store vs bookshop availability
- [ ] Generate bookshop.org affiliate links
- [ ] Use Redis for intelligent inventory caching
- [ ] Add background tasks for inventory updates

### Book Data Features

- [ ] Merge API data with inventory
- [ ] Cache book data in Redis with proper invalidation
- [ ] Extract book mentions from text using simple text processing
- [ ] Track ISBN detection with validation
- [ ] Handle fuzzy title matching (start simple, can enhance later)
- [ ] Implement text-based book matching

### Book Service Testing

- [ ] Create `test_book_service.py` with pytest
- [ ] Mock Hardcover API with fixtures
- [ ] Test book search
- [ ] Test inventory checks
- [ ] Test Redis cache behavior
- [ ] Test book mention extraction
- [ ] Test text matching functionality

## Step 6: Conversation Manager (Redis + Text Processing)

### Conversation Module

- [ ] Create `conversation_manager.py` with proper patterns
- [ ] Implement ConversationManager class
- [ ] Design message storage format with Pydantic
- [ ] Add timestamp tracking
- [ ] Include metadata structure
- [ ] Set up Redis for conversation threading

### Core Features

- [ ] Implement load_conversation
- [ ] Implement add_message
- [ ] Implement get_context
- [ ] Track mentioned books with text processing
- [ ] Handle conversation expiration with Redis TTL
- [ ] Manage conversation state with Redis

### Context Management

- [ ] Limit to 10 recent messages with efficient queries
- [ ] Implement message summarization (start simple)
- [ ] Track conversation threads with Redis
- [ ] Handle concurrent messages safely
- [ ] Add thread safety with Redis locks

### Book References

- [ ] Extract book mentions with text processing
- [ ] Create mention index for lookups
- [ ] Handle "that book" references with context
- [ ] Link to inventory operations
- [ ] Track purchase intent with simple patterns

### Conversation Testing

- [ ] Create `test_conversation_manager.py` with pytest
- [ ] Test message storage
- [ ] Test context retrieval
- [ ] Test book tracking with text processing
- [ ] Test expiration with Redis TTL
- [ ] Test concurrent access patterns

## Step 7: Claude AI Integration (Background Tasks)

### AI Client

- [ ] Create `ai_client.py` module with httpx client (async for API calls)
- [ ] Implement ClaudeClient class
- [ ] Create Pydantic models for AI requests and responses
- [ ] Configure API authentication properly
- [ ] Set up retry logic with exponential backoff
- [ ] Add timeout handling with circuit breakers
- [ ] Add OpenTelemetry tracing for AI calls

### Prompt Management

- [ ] Load base Marty prompt with template engine
- [ ] Implement context injection with Pydantic
- [ ] Add dynamic variables with type safety
- [ ] Include store hours logic
- [ ] Format customer context properly

### Response Processing

- [ ] Implement generate_response
- [ ] Parse AI responses with Pydantic models
- [ ] Extract book references with text processing
- [ ] Detect purchase intent with simple patterns
- [ ] Identify required actions with structured responses
- [ ] Use background tasks for AI processing to avoid blocking webhooks

### Error Handling

- [ ] Handle API timeouts with circuit breakers
- [ ] Implement fallback responses with personality
- [ ] Add rate limit handling with Redis
- [ ] Log all API calls with structured logging
- [ ] Track token usage with metrics
- [ ] Add response caching with Redis

### AI Testing

- [ ] Create `test_ai_client.py` with pytest
- [ ] Mock Claude API with fixtures
- [ ] Test response generation
- [ ] Test context building with Pydantic
- [ ] Test error scenarios with circuit breakers
- [ ] Test response parsing with structured data
- [ ] Test background task processing

## Step 8: Marty Personality (Modern Templates)

### Personality Module

- [ ] Create `marty_personality.py` with template engine
- [ ] Load system prompt from file
- [ ] Parse prompt structure with Pydantic
- [ ] Implement personality rules with text processing
- [ ] Add context awareness with Redis session data

### Response Features

- [ ] Implement casual texting style formatting
- [ ] Add message breaking logic with intelligent splits
- [ ] Include wizard references contextually
- [ ] Format error messages in character with fallback responses
- [ ] Handle store hours with real-time data

### Context Features

- [ ] Reference purchase history with database queries
- [ ] Remember conversation books with Redis caching
- [ ] Detect customer type with simple classification
- [ ] Add time awareness with timezone handling
- [ ] Include inventory status with real-time updates

### Message Formatting

- [ ] Implement SMS character limits with smart breaking
- [ ] Find natural break points with text processing
- [ ] Remove special formatting for SMS compatibility
- [ ] Handle multi-message responses properly
- [ ] Test message splitting with various content types

### Personality Testing

- [ ] Create `test_marty_personality.py` with pytest
- [ ] Test response style consistency
- [ ] Test message breaking with edge cases
- [ ] Test personality consistency across conversations
- [ ] Test error messages in character
- [ ] Test context awareness with data
- [ ] Test A/B personality variations

## Step 9: Purchase Flow (State Machines)

### Purchase Module

- [ ] Create `purchase_flow.py` with state machines
- [ ] Design flow state machine with Redis persistence
- [ ] Track purchase progress with structured data
- [ ] Handle flow interruptions with timeout recovery
- [ ] Add timeout handling with Redis TTL

### Intent Detection

- [ ] Identify purchase phrases with simple patterns
- [ ] Resolve book references with text matching
- [ ] Handle ambiguous references with clarification flow
- [ ] Confirm book selection with interactive prompts
- [ ] Track intent confidence with scoring

### Fulfillment

- [ ] Ask shipping vs pickup with conversation flow
- [ ] Collect shipping address with validation
- [ ] Handle pickup options with availability checks
- [ ] Process payment choice with Square API
- [ ] Create hold requests with inventory management

### Order Processing

- [ ] Create Square orders with API calls
- [ ] Generate payment links with proper expiration
- [ ] Update inventory with atomic operations
- [ ] Send confirmations with background tasks
- [ ] Handle bookshop redirects with affiliate tracking

### Purchase Testing

- [ ] Create `test_purchase_flow.py` with pytest
- [ ] Test intent detection with confidence scoring
- [ ] Test fulfillment flow with state persistence
- [ ] Test order creation
- [ ] Test error cases with recovery flows
- [ ] Test complete end-to-end flow

## Step 10: Production Features (Observability + Monitoring)

### Rate Limiting

- [ ] Create `production_utils.py` with Redis-based rate limiting
- [ ] Implement per-phone limits with sliding windows
- [ ] Add global API limits with circuit breakers
- [ ] Create backoff strategies with exponential delays
- [ ] Add circuit breakers for external APIs
- [ ] Test under load with realistic scenarios

### Enhanced Error Handling

- [ ] Catch all edge cases with comprehensive exception handling
- [ ] Add personality to errors with Marty's voice
- [ ] Implement retry logic with exponential backoff
- [ ] Add fallback responses with graceful degradation
- [ ] Log all errors with structured logging and correlation IDs

### Monitoring

- [ ] Track response times with OpenTelemetry metrics
- [ ] Monitor API success rates with custom metrics
- [ ] Add conversation metrics with business intelligence
- [ ] Track error rates with alerting thresholds
- [ ] Create metric dashboards with visualization
- [ ] Add distributed tracing for end-to-end visibility

### Performance

- [ ] Optimize database queries efficiently
- [ ] Add connection pooling with asyncpg
- [ ] Implement caching strategy with Redis
- [ ] Use async for I/O operations, sync for logic
- [ ] Profile bottlenecks with performance monitoring
- [ ] Add load balancing for horizontal scaling

### Security

- [ ] Sanitize all inputs with Pydantic validation
- [ ] Prevent SQL injection with parameterized queries
- [ ] Validate phone numbers with comprehensive checks
- [ ] Add request validation with middleware
- [ ] Test security measures with penetration testing
- [ ] Add CORS configuration for web security

### Production Testing

- [ ] Create `test_production_utils.py` with pytest
- [ ] Load test the system with realistic traffic
- [ ] Test rate limiting with burst scenarios
- [ ] Test error scenarios with chaos engineering
- [ ] Test monitoring with synthetic transactions
- [ ] Verify security measures with automated scans

## Step 11: Final Integration

### Main Flow

- [ ] Create `main_flow.py` with proper orchestration
- [ ] Wire all components with dependency injection
- [ ] Implement message flow with efficient pipelines
- [ ] Handle all paths with comprehensive error handling
- [ ] Add state management with Redis persistence

### App Integration

- [ ] Update `main.py` with modern FastAPI patterns
- [ ] Initialize all services with proper context management
- [ ] Set up dependencies with FastAPI dependency injection
- [ ] Configure background tasks with proper scheduling
- [ ] Add graceful shutdown with cleanup handlers

### Background Tasks

- [ ] Expire old conversations with Redis TTL
- [ ] Clean up cache with intelligent invalidation
- [ ] Collect metrics with OpenTelemetry
- [ ] Process pending messages with queues
- [ ] Handle retries with exponential backoff

### Configuration

- [ ] Validate all env vars with Pydantic settings
- [ ] Set production defaults with environment detection
- [ ] Add config validation on startup
- [ ] Environment detection with proper overrides
- [ ] Secret management with secure storage

### Deployment Prep

- [ ] Finalize pyproject.toml with all dependencies
- [ ] Update railway.toml with modern configuration
- [ ] Create startup script with health checks
- [ ] Add enhanced health checks with dependency monitoring
- [ ] Configure structured logging with correlation IDs

### End-to-End Testing

- [ ] Test new customer flow with realistic scenarios
- [ ] Test returning customer with conversation history
- [ ] Test complete purchase with payment integration
- [ ] Test error scenarios with chaos engineering
- [ ] Test rate limiting with burst traffic
- [ ] Test all integrations with comprehensive coverage

## Deployment & Launch

### Railway Deployment

- [ ] Create Railway project
- [ ] Configure environment variables
- [ ] Deploy initial version
- [ ] Test health endpoint
- [ ] Monitor logs
- [ ] Set up domains

### External Service Config

- [ ] Configure Smobi webhook URL
- [ ] Test SMS sending/receiving
- [ ] Verify Square integration
- [ ] Test Hardcover API
- [ ] Verify Claude responses
- [ ] Test Bookshop.org links

### Demo Preparation

- [ ] Create demo scenarios
- [ ] Prepare test phone numbers
- [ ] Stock demo inventory
- [ ] Create demo customers
- [ ] Record demo videos
- [ ] Prepare screenshots

### Documentation

- [ ] Complete README.md
- [ ] Document API endpoints
- [ ] Create deployment guide
- [ ] Write testing guide
- [ ] Document troubleshooting
- [ ] Add architecture diagram

### Launch Checklist

- [ ] All tests passing
- [ ] Production config verified
- [ ] Monitoring active
- [ ] Error handling tested
- [ ] Rate limits configured
- [ ] Demo ready
- [ ] Team trained
- [ ] Social media prepared

## Post-Launch

### Monitoring

- [ ] Watch error rates
- [ ] Monitor response times
- [ ] Check conversation quality
- [ ] Track completion rates
- [ ] Review user feedback

### Iterations

- [ ] Collect user feedback
- [ ] Refine Marty's personality
- [ ] Optimize response times
- [ ] Improve book matching
- [ ] Enhance error messages

### Future Features

- [ ] Ingram API integration
- [ ] Advanced analytics
- [ ] Voice message support
- [ ] Multi-store support
- [ ] ML recommendations
