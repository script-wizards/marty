# Dungeon Books SMS Wizard - Implementation Checklist

## Initial Setup

### Environment & Tools

- [x] Create new GitHub repository
- [x] Set up local development environment
- [x] Install Python 3.13+
- [x] Create uv virtual environment
- [x] Initialize git repository
- [x] Create .gitignore (include .env, venv/, **pycache**)
- [x] Create README.md with project overview

### External Services Setup

- [x] Create Supabase account and project
- [x] Get Supabase URL and service key
- [ ] Create Square developer account
- [ ] Get Square sandbox credentials
- [x] Apply for Hardcover API access
- [x] Get Hardcover API key
- [x] Register with Anthropic for Claude API
- [x] Get Claude API key
- [x] Set up Sinch account and get credentials
- [x] Configure Sinch webhook URL
- [x] Get Sinch API Token and Service Plan ID
- [x] Set up Bookshop.org affiliate account
- [x] Create Railway account

### Configuration

- [x] Create .env.example file with all required variables
- [x] Create local .env file with development credentials
- [x] Document all environment variables in README

### Modern Python Tooling

- [x] Set up uv for dependency management
- [x] Configure pyproject.toml with all dependencies
- [x] Set up ruff for linting and formatting
- [x] Configure pre-commit hooks
- [x] Set up pytest with async support
- [x] Configure dual stack IPv4/IPv6 networking
- [x] Set up comprehensive test coverage
- [x] Add GraphQL dependencies (gql, aiohttp, httpx)
- [x] Add async SQLite support (aiosqlite)
- [x] Create API exploration utilities
- [x] Add comprehensive Hardcover API documentation

## Step 1: Database Foundation

### Database Schema

- [x] Create Supabase project
- [x] Set up Alembic for database migrations
- [x] Create SQLAlchemy models for all tables
- [x] Write Alembic migration for customers table
- [x] Write Alembic migration for conversations table
- [x] Write Alembic migration for books table
- [x] Write Alembic migration for inventory table
- [x] Write Alembic migration for orders table
- [x] Write Alembic migration for rate_limits table
- [ ] Execute migrations in Supabase
- [x] Verify all tables created correctly

### Database Module

- [x] Create `database.py` module with SQLAlchemy (async for I/O)
- [x] Implement database session management
- [x] Create Pydantic models for data validation
- [x] Set up asyncpg connection pooling with Supabase
- [x] Implement CRUD operations for customers
- [x] Implement CRUD operations for conversations
- [x] Implement CRUD operations for books
- [x] Implement CRUD operations for inventory
- [x] Implement CRUD operations for orders
- [x] Implement CRUD operations for rate_limits
- [x] Add comprehensive error handling
- [x] Add structured logging with correlation IDs
- [x] Add type hints throughout

### Database Testing

- [x] Create `test_database.py` with pytest
- [x] Write tests for connection management
- [x] Write tests for each CRUD operation
- [x] Test error scenarios with proper handling
- [x] Test connection pooling behavior
- [x] Verify database operations work correctly
- [x] Test Pydantic model validation
- [x] Use pytest-asyncio where needed for I/O tests

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
- [x] Check database connectivity
- [x] Return proper status format
- [x] Add timestamp to response
- [x] Include version information

### Logging & Error Handling

- [x] Set up structured JSON logging (via ruff configuration)
- [~] Implement correlation ID generation
- [x] Create error handling middleware (FastAPI built-in)
- [x] Map exceptions to HTTP status codes
- [x] Ensure no internal errors leak
- [x] Test error responses

### Deployment Config

- [x] Create pyproject.toml
- [~] Create railway.toml
- [~] Add Procfile if needed
- [x] Configure port binding
- [x] Set up environment detection

### Web Service Testing

- [x] Create `test_health.py` (comprehensive tests)
- [x] Test health endpoint
- [x] Test error handling
- [x] Test configuration loading
- [x] Test logging output
- [~] Verify Railway configuration

## Step 3: SMS Webhook Handler

### Webhook Endpoint

- [x] Create `sms_handler.py` module with FastAPI dependency injection
- [x] Implement POST /webhook/sms endpoint with Pydantic validation
- [x] Create Pydantic models for webhook payloads
- [x] Validate required fields with Pydantic
- [x] Add structured logging with correlation IDs
- [x] Set up Redis for message queuing

### Security

- [x] Implement HMAC signature verification as FastAPI middleware
- [x] Add timestamp validation for replay attack protection
- [x] Test with valid signatures
- [x] Test with invalid signatures
- [x] Handle missing signature header
- [x] Add request validation with Pydantic
- [x] Implement configurable signature age limits (5-minute window)

### Message Processing

- [x] Store incoming messages in database
- [x] Mark messages as pending
- [x] Return 200 immediately (non-blocking pattern)
- [x] Use FastAPI background tasks for message processing
- [x] Set up Redis message queuing
- [x] Add timestamp tracking

### Rate Limiting

- [x] Implement Redis-based rate limiting with sliding windows
- [x] Implement Redis connection pooling for performance
- [x] Track per-phone number limits
- [x] Add burst protection (separate hourly limits)
- [x] Handle rate limit exceeded with Marty's voice
- [x] Clean up old rate limit records automatically
- [x] Test rate limiting logic with Redis
- [x] Make rate limits configurable via environment variables

### SMS Provider Integration

- [x] Choose SMS provider (Sinch selected)
- [x] Implement Sinch SMS sending client with Bearer token auth
- [x] Create mock Sinch response function for testing
- [x] Log outgoing messages with structured logging
- [x] Add phone number validation and normalization
- [x] Implement configurable default region for phone parsing
- [x] Add GSM-7 character set validation and filtering
- [x] Implement multi-message SMS splitting for natural conversation flow
- [x] Add message delays between SMS sends for realistic texting
- [x] Track sent messages in Redis
- [ ] Consider parallel SMS sending for better performance while maintaining careful rate limiting
- [ ] Add retry logic for failed SMS sends with exponential backoff

### Webhook Testing

- [x] Create `test_sms_handler.py` with pytest
- [x] Test valid webhook requests
- [x] Test signature verification with timestamp validation
- [x] Test missing fields with Pydantic validation
- [x] Test rate limiting with Redis (both regular and burst limits)
- [x] Test database integration
- [x] Test FastAPI background tasks
- [x] Test phone number normalization and validation
- [x] Test GSM-7 character filtering
- [x] Test multi-message SMS splitting
- [x] Add integration tests with real Redis
- [x] Test error messages in Marty's voice

### SMS Enhancements Completed

- [x] Unified signature verification API (removed redundant functions)
- [x] Added timestamp validation for replay attack protection
- [x] Configurable signature age limits (5-minute window default)
- [x] Enhanced error messages in Marty's voice
- [x] Implemented Redis connection pooling
- [x] Configurable rate limiting (regular + burst protection)
- [x] Environment variable configuration for all limits
- [x] Efficient Redis key management with TTL
- [x] Multi-message SMS splitting for natural conversation flow
- [x] GSM-7 character validation and filtering
- [x] Phone number normalization with configurable regions
- [x] Message delays between SMS sends for realistic texting
- [x] Comprehensive test coverage (unit + integration)
- [x] Fixed event loop conflicts in async tests
- [x] Clean API design with proper type hints
- [x] Removed verbose comments and improved readability
- [x] Fast CI tests (unit tests with mocks)
- [x] Full CI tests (integration tests with real Redis)
- [x] Separate test markers for different test types
- [x] Async test client for proper Redis integration testing

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

- [x] Create `book_service.py` module with httpx client (async for API calls)
- [x] Implement HardcoverClient class
- [x] Create Pydantic models for book data and inventory
- [x] Add authentication headers
- [x] Implement search_books method
- [x] Implement get_book_details method
- [x] Handle API errors with circuit breaker pattern
- [x] Add OpenTelemetry tracing for API calls

### Inventory Management

- [~] Implement check_inventory
- [~] Implement update_inventory
- [~] Track store vs bookshop availability
- [~] Generate bookshop.org affiliate links
- [~] Use Redis for intelligent inventory caching
- [~] Add background tasks for inventory updates

### Book Data Features

- [~] Merge API data with inventory
- [~] Cache book data in Redis with proper invalidation
- [~] Extract book mentions from text using simple text processing
- [~] Track ISBN detection with validation
- [~] Handle fuzzy title matching (start simple, can enhance later)
- [~] Implement text-based book matching

### Book Service Testing

- [x] Create `test_book_service.py` with pytest
- [x] Mock Hardcover API with fixtures
- [x] Test book search
- [x] Test inventory checks
- [x] Test Redis cache behavior
- [x] Test book mention extraction
- [x] Test text matching functionality

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

- [x] Create `ai_client.py` module with httpx client (async for API calls)
- [x] Implement ClaudeClient class
- [x] Create Pydantic models for AI requests and responses
- [x] Configure API authentication properly
- [x] Set up retry logic with exponential backoff
- [x] Add timeout handling with circuit breakers
- [x] Add OpenTelemetry tracing for AI calls

### Prompt Management

- [x] Load base Marty prompt with template engine
- [x] Implement context injection with Pydantic
- [x] Add dynamic variables with type safety
- [x] Include store hours logic
- [x] Format customer context properly

### Response Processing

- [x] Implement generate_response
- [x] Parse AI responses with Pydantic models
- [x] Extract book references with text processing
- [x] Detect purchase intent with simple patterns
- [x] Identify required actions with structured responses
- [x] Use background tasks for AI processing to avoid blocking webhooks

### Error Handling

- [x] Handle API timeouts with circuit breakers
- [x] Implement fallback responses with personality
- [x] Add rate limit handling with Redis
- [x] Log all API calls with structured logging
- [x] Track token usage with metrics
- [x] Add response caching with Redis
- [ ] Add circuit breaker pattern for external API calls (Sinch, AI responses) to improve resilience
- [x] Add comprehensive error handling for all edge cases with personality-driven responses

### AI Testing

- [x] Create `test_ai_client.py` with pytest
- [x] Mock Claude API with fixtures
- [x] Test response generation
- [x] Test context building with Pydantic
- [x] Test error scenarios with circuit breakers
- [x] Test response parsing with structured data
- [x] Test background task processing

## Step 8: Marty Personality

### Personality Module

- [x] Create `marty_personality.py` with template engine
- [x] Load system prompt from file
- [x] Parse prompt structure with Pydantic
- [x] Implement personality rules with text processing
- [x] Add context awareness with Redis session data

### Response Features

- [x] Implement casual texting style formatting
- [x] Add message breaking logic with intelligent splits
- [x] Include wizard references contextually
- [x] Format error messages in character with fallback responses
- [x] Handle store hours with real-time data

### Context Features

- [x] Reference purchase history with database queries
- [x] Remember conversation books with Redis caching
- [x] Detect customer type with simple classification
- [x] Add time awareness with timezone handling
- [x] Include inventory status with real-time updates

### Message Formatting

- [x] Implement SMS character limits with smart breaking
- [x] Find natural break points with text processing
- [x] Remove special formatting for SMS compatibility
- [x] Handle multi-message responses properly
- [x] Test message splitting with various content types
- [ ] Improve error message localization for international users

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
- [ ] Add circuit breaker monitoring and metrics for external service health

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

- [x] Create `main_flow.py` with proper orchestration
- [x] Wire all components with dependency injection
- [x] Implement message flow with efficient pipelines
- [x] Handle all paths with comprehensive error handling
- [x] Add state management with Redis persistence
- [x] Integrate SMS webhook handler with AI processing
- [x] Implement multi-message SMS responses
- [x] Add rate limiting and security to message flow

### App Integration

- [x] Update `main.py` with modern FastAPI patterns
- [x] Initialize all services with proper context management
- [x] Set up dependencies with FastAPI dependency injection
- [x] Configure background tasks with proper scheduling
- [x] Add graceful shutdown with cleanup handlers

### Background Tasks

- [~] Expire old conversations with Redis TTL
- [~] Clean up cache with intelligent invalidation
- [~] Collect metrics with OpenTelemetry
- [~] Process pending messages with queues
- [~] Handle retries with exponential backoff

### Configuration

- [~] Validate all env vars with Pydantic settings
- [~] Set production defaults with environment detection
- [~] Add config validation on startup
- [~] Environment detection with proper overrides
- [~] Secret management with secure storage

### Deployment Prep

- [x] Finalize pyproject.toml with all dependencies
- [~] Update railway.toml with modern configuration
- [~] Create startup script with health checks
- [~] Add enhanced health checks with dependency monitoring
- [~] Configure structured logging with correlation IDs

### End-to-End Testing

- [x] Test new customer flow with realistic scenarios
- [x] Test returning customer with conversation history
- [x] Test SMS webhook processing with real messages
- [x] Test multi-message SMS responses
- [x] Test rate limiting with burst scenarios
- [x] Test signature verification and replay protection
- [x] Test phone number validation and normalization
- [x] Test GSM-7 character filtering
- [x] Test error messages in Marty's voice
- [~] Test complete purchase with payment integration
- [~] Test error scenarios with chaos engineering
- [x] Test all integrations with comprehensive coverage

## Deployment & Launch

### Railway Deployment

- [ ] Create Railway project
- [ ] Configure environment variables
- [ ] Deploy initial version
- [ ] Test health endpoint
- [ ] Monitor logs
- [ ] Set up domains

### External Service Config

- [ ] Configure SMS provider webhook URL
- [ ] Test SMS sending/receiving
- [ ] Verify Square integration
- [ ] Test Hardcover API
- [x] Verify Claude responses
- [ ] Test Bookshop.org links

### Demo Preparation

- [ ] Create demo scenarios
- [ ] Prepare test phone numbers
- [ ] Stock demo inventory
- [ ] Create demo customers
- [ ] Record demo videos
- [ ] Prepare screenshots

### Documentation

- [x] Complete README.md
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

### Code Quality Improvements

- [ ] Extract hard-coded conversation history limit=10 in main.py to named constant or configuration value

### Future Features

- [ ] Ingram API integration
- [ ] Advanced analytics
- [ ] Voice message support
- [ ] Multi-store support
- [ ] ML recommendations
