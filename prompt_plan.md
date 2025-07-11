## Project Blueprint: Dungeon Books RCS Wizard

### Phase 1: Core Infrastructure Setup

1. **Database Schema & Connection**

    - Set up Supabase connection
    - Create database schema
    - Test database operations
2. **Basic Web Service**

    - Create Flask/FastAPI application
    - Health check endpoint
    - Basic error handling
    - Railway deployment configuration
3. **SMS Webhook Foundation**

    - Webhook endpoint structure
    - Request validation
    - Basic response mechanism

### Phase 2: External Service Integration

4. **SMS/RCS Provider Integration**

    - Webhook signature verification
    - Message parsing
    - Response sending
5. **Square API Integration**

    - Customer lookup by phone
    - Customer data caching
    - Order creation basics
6. **Book Data Integration**

    - Hardcover API connection
    - Book search functionality
    - Inventory management

### Phase 3: AI & Conversation Management

7. **Conversation State Management**

    - Message storage
    - Conversation threading
    - Context retrieval
8. **Claude AI Integration**

    - Basic prompt structure
    - Context injection
    - Response generation
9. **Marty Personality Implementation**

    - System prompt refinement
    - Dynamic context building
    - Response processing

### Phase 4: Commerce & Polish

10. **Order Processing Flow**

    - Purchase intent detection
    - Fulfillment options
    - Payment link generation
11. **Error Handling & Rate Limiting**

    - Comprehensive error responses
    - Rate limiting implementation
    - Monitoring and logging
12. **End-to-End Testing & Polish**

    - Integration testing
    - Performance optimization
    - Demo preparation

## Iterative Breakdown - Round 1

### Infrastructure (Days 1-3)

1. **Database Setup**

    - Create Supabase project
    - Define schema migrations
    - Basic CRUD operations
    - Connection pooling
2. **Web Service Skeleton**

    - Flask app structure
    - Environment configuration
    - Health monitoring
    - Structured logging
3. **SMS Integration Foundation**

    - Webhook endpoint
    - Message queue structure
    - Response framework
    - Testing harness

### External Services (Days 4-6)

4. **Customer Management**

    - Square API client
    - Customer lookup
    - JIT customer creation
    - Data synchronization
5. **Book Data Layer**

    - Hardcover API client
    - Search implementation
    - Inventory tracking
    - Cache strategy

### AI Integration (Days 7-9)

6. **Conversation Engine**

    - Message persistence
    - Context window management
    - State tracking
    - History retrieval
7. **AI Response System**

    - Claude client setup
    - Prompt engineering
    - Response parsing
    - Error handling

### Commerce (Days 10-12)

8. **Purchase Flow**

    - Intent recognition
    - Order creation
    - Payment integration
    - Fulfillment options
9. **Production Readiness**

    - Rate limiting
    - Error recovery
    - Monitoring setup
    - Performance tuning

## Iterative Breakdown - Round 2 (Smaller Steps)

### Step 1: Database Foundation

- 1.1 Supabase connection class
- 1.2 Customer table operations
- 1.3 Conversation table operations
- 1.4 Book/inventory operations
- 1.5 Integration tests

### Step 2: Web Service Core

- 2.1 Flask app initialization
- 2.2 Configuration management
- 2.3 Health check endpoint
- 2.4 Error handler middleware
- 2.5 Logging setup

### Step 3: SMS Webhook

- 3.1 Webhook route definition
- 3.2 Signature verification
- 3.3 Message parsing
- 3.4 Response queue
- 3.5 Mock SMS provider

### Step 4: Customer Service

- 4.1 Square API client wrapper
- 4.2 Customer search by phone
- 4.3 Customer creation
- 4.4 Local cache sync
- 4.5 Integration tests

### Step 5: Book Service

- 5.1 Hardcover API client
- 5.2 Book search functionality
- 5.3 Inventory management
- 5.4 Book data enrichment
- 5.5 Cache implementation

### Step 6: Conversation Manager

- 6.1 Message storage
- 6.2 Conversation threading
- 6.3 Context window extraction
- 6.4 Book mention tracking
- 6.5 Timeout handling

### Step 7: AI Integration

- 7.1 Claude client setup
- 7.2 Base prompt structure
- 7.3 Context injection
- 7.4 Response generation
- 7.5 Message splitting

### Step 8: Marty Personality

- 8.1 System prompt implementation
- 8.2 Dynamic context building
- 8.3 Response personality layer
- 8.4 Error message personality
- 8.5 Testing conversations

### Step 9: Purchase Flow

- 9.1 Intent detection
- 9.2 Book reference resolution
- 9.3 Order creation flow
- 9.4 Payment link generation
- 9.5 Fulfillment handling

### Step 10: Production Features

- 10.1 Rate limiting
- 10.2 Comprehensive error handling
- 10.3 Monitoring integration
- 10.4 Performance optimization
- 10.5 End-to-end testing

## Final Review of Step Sizing

The steps are appropriately sized because:

- Each step can be implemented in 2-4 hours
- Each step has clear testable outcomes
- Dependencies are minimized between steps
- Core functionality comes before polish
- Each step adds immediate value

---

## Code Generation Prompts

### Prompt 1: Database Foundation Setup

```text
Create a Python module for Supabase database operations for a bookstore SMS chatbot.

Requirements:
1. Create a `database.py` module with a SupabaseClient class
2. Implement connection management with connection pooling
3. Create methods for CRUD operations on these tables:
   - customers (id, phone, square_customer_id, preferences, created_at, updated_at)
   - conversations (id, customer_id, phone, messages, mentioned_books, last_activity, active)
   - books (id, isbn, title, author, publisher, metadata, created_at)
   - inventory (id, book_id, in_stock_count, source, updated_at)
   - orders (id, customer_id, book_id, status, fulfillment_type, square_order_id, total_amount, created_at)
   - rate_limits (phone, message_count, window_start)

4. Use environment variables for configuration (SUPABASE_URL, SUPABASE_SERVICE_KEY)
5. Implement proper error handling and logging
6. Create comprehensive unit tests using pytest
7. Use type hints throughout
8. Include docstrings for all methods

The module should handle connection failures gracefully and support async operations.
```

### Prompt 2: Flask Web Service Foundation

```text
Create a Flask web application foundation for an SMS chatbot service.

Requirements:
1. Create an `app.py` with Flask application factory pattern
2. Implement configuration management from environment variables:
   - PORT (default 8080)
   - ENV (development/production)
   - LOG_LEVEL
   - All API keys as env vars (but don't use them yet)
3. Create a health check endpoint at GET /health that returns:
   - Status: "healthy"
   - Timestamp
   - Database connection status (use the SupabaseClient from previous step)
4. Implement structured JSON logging with correlation IDs
5. Add error handling middleware that:
   - Catches all exceptions
   - Logs errors with full context
   - Returns appropriate HTTP status codes
   - Never exposes internal errors to clients
6. Create a basic test suite using pytest
7. Include a requirements.txt with all dependencies
8. Add Railway deployment configuration (railway.toml)

Import and use the database module from the previous step.
```

### Prompt 3: SMS Webhook Handler

```text
Extend the Flask application to handle SMS webhook requests.

Requirements:
1. Create a new module `sms_handler.py` with webhook processing logic
2. Add POST /webhook/sms endpoint that:
   - Accepts JSON payload with: from, to, message, message_type, timestamp, signature
   - Verifies webhook signature using HMAC-SHA256 (SMOBI_WEBHOOK_SECRET env var)
   - Validates required fields
   - Returns 200 OK immediately (async processing)
3. Create a simple message queue using the database:
   - Store incoming messages in conversations table
   - Mark messages as "pending" for processing
   - Include received timestamp
4. Add a mock SMS sending function that logs responses for now
5. Implement rate limiting check (10 messages/minute, 100/hour per phone)
6. Create comprehensive tests including:
   - Valid webhook requests
   - Invalid signatures
   - Missing fields
   - Rate limit scenarios
7. Update the health check to include webhook status

Use the existing database module for all data operations.
```

### Prompt 4: Square Customer Integration

```text
Create a Square API integration module for customer management.

Requirements:
1. Create `square_client.py` module with SquareClient class
2. Implement these methods:
   - search_customer_by_phone(phone: str) -> Optional[Customer]
   - get_customer(customer_id: str) -> Optional[Customer]
   - create_customer(phone: str, name: Optional[str]) -> Customer
   - get_customer_orders(customer_id: str) -> List[Order]
3. Add customer synchronization logic:
   - Check local database first
   - If not found, search Square
   - Create local record with Square data
   - Cache for 24 hours
4. Handle Square API errors gracefully:
   - Rate limiting with exponential backoff
   - Network errors
   - Invalid responses
5. Create mock Square responses for testing
6. Add integration to the SMS handler:
   - Look up customer on each message
   - Store customer_id in conversation
7. Comprehensive test coverage
8. Use environment variables: SQUARE_ACCESS_TOKEN, SQUARE_APPLICATION_ID, SQUARE_ENVIRONMENT

Integrate with existing database and SMS handler modules.
```

### Prompt 5: Book Data Service

```text
Create a book data service integrating Hardcover API and local inventory.

Requirements:
1. Create `book_service.py` module with BookService class
2. Implement Hardcover API client:
   - search_books(query: str, limit: int = 5) -> List[Book]
   - get_book_details(book_id: str) -> Optional[Book]
   - Handle API authentication with HARDCOVER_API_KEY
3. Add inventory management:
   - check_inventory(book_id: str) -> InventoryStatus
   - update_inventory(book_id: str, count: int, source: str)
   - get_availability(book_id: str) -> Dict (store vs bookshop.org)
4. Create book data enrichment:
   - Merge Hardcover data with local inventory
   - Generate bookshop.org affiliate links
   - Cache book data for 7 days
5. Add book mention extraction:
   - Extract ISBNs, titles, authors from text
   - Track mentioned books in conversations
6. Mock Hardcover API for testing
7. Integration tests with database
8. Error handling for API failures

Integrate with existing database module.
```

### Prompt 6: Conversation State Manager

```text
Create a conversation management system for maintaining chat context.

Requirements:
1. Create `conversation_manager.py` module
2. Implement ConversationManager class with:
   - load_conversation(phone: str) -> Conversation
   - add_message(phone: str, role: str, content: str)
   - get_context(phone: str, max_messages: int = 10) -> List[Message]
   - update_mentioned_books(phone: str, books: List[str])
   - expire_inactive_conversations(timeout_hours: int = 3)
3. Message storage format:
   - Role: "customer" or "assistant"
   - Content: message text
   - Timestamp
   - Metadata (mentioned books, intent flags)
4. Context window management:
   - Keep last 10 messages
   - Summarize older messages if needed
   - Track conversation state (active, expired)
5. Book reference tracking:
   - Extract book mentions from messages
   - Maintain quick lookup for "that book" references
   - Link to inventory checks
6. Thread safety for concurrent messages
7. Comprehensive tests for conversation flows
8. Integration with SMS handler

Use existing database module for persistence.
```

### Prompt 7: Claude AI Integration

```text
Create Claude API integration for generating responses.

Requirements:
1. Create `ai_client.py` module with ClaudeClient class
2. Implement core methods:
   - generate_response(message: str, context: Dict) -> str
   - create_system_prompt(base_prompt: str, dynamic_context: Dict) -> str
   - parse_response(response: str) -> ParsedResponse
3. System prompt structure:
   - Load base Marty prompt from file
   - Inject dynamic context (customer info, history, inventory)
   - Include current time and store status
4. Response processing:
   - Extract book references
   - Detect purchase intent
   - Identify required actions (search, order, etc.)
5. Error handling:
   - API timeouts (30 second limit)
   - Rate limiting
   - Fallback responses
6. Message formatting:
   - Split long responses for SMS
   - Preserve Marty's personality
   - Natural conversation breaks
7. Mock Claude API for testing
8. Integration with conversation manager
9. Use CLAUDE_API_KEY from environment

Test with various conversation scenarios.
```

### Prompt 8: Marty Personality Layer

```text
Implement Marty's personality and response processing system.

Requirements:
1. Create `marty_personality.py` module
2. Load and process Marty's system prompt:
   - Parse the markdown prompt file
   - Build dynamic context injection
   - Handle conversation state awareness
3. Response personality features:
   - Lowercase casual texting style
   - Natural message breaking (2-3 messages)
   - Wizard references when appropriate
   - Error messages in character
4. Context awareness:
   - Reference customer purchase history naturally
   - Remember books mentioned in conversation
   - Time-based responses (store hours)
   - Returning vs new customer detection
5. Special response handlers:
   - Book recommendations formatting
   - Purchase flow responses
   - Out of stock responses
   - Error responses in character
6. Message formatting rules:
   - Max 150 chars for SMS
   - Natural break points
   - No special formatting
7. Comprehensive personality tests
8. Integration with AI client

Build on the AI client from previous step.
```

### Prompt 9: Purchase Flow Implementation

```text
Implement the complete purchase flow from intent to order creation.

Requirements:
1. Create `purchase_flow.py` module
2. Purchase intent detection:
   - Identify phrases like "I'll take it", "buy that", etc.
   - Resolve book references from conversation
   - Confirm which book if multiple mentioned
3. Fulfillment flow:
   - Ask "ship it or picking up?"
   - Handle shipping address collection
   - Process pickup with payment options
   - Create hold requests
4. Square order creation:
   - Build order with book details
   - Generate payment links
   - Handle different fulfillment types
   - Update order status
5. Inventory updates:
   - Decrement store inventory
   - Handle bookshop.org redirects
   - Track order source
6. Response generation:
   - Natural conversation flow
   - Clear next steps
   - Payment link delivery
7. Error handling:
   - Payment failures
   - Out of stock scenarios
   - Address validation
8. Integration with all previous modules
9. End-to-end purchase tests

This ties together Square, inventory, conversation, and AI modules.
```

### Prompt 10: Production Features

```text
Add production-ready features for monitoring, rate limiting, and error handling.

Requirements:
1. Create `production_utils.py` module
2. Comprehensive rate limiting:
   - Per-phone number limits (10/min, 100/hour)
   - Global API rate limits
   - Backoff strategies
   - Database-backed tracking
3. Advanced error handling:
   - Catch all edge cases
   - Personality-appropriate error messages
   - Automatic retry logic
   - Circuit breakers for external APIs
4. Monitoring and metrics:
   - Response time tracking
   - API call success rates
   - Conversation metrics
   - Error rate monitoring
5. Performance optimizations:
   - Connection pooling
   - Response caching
   - Async processing where beneficial
   - Database query optimization
6. Security enhancements:
   - Input sanitization
   - SQL injection prevention
   - Rate limit bypass prevention
7. Operational features:
   - Graceful shutdown
   - Health check improvements
   - Debug mode for testing
8. Configuration validation on startup
9. Comprehensive integration tests
10. Load testing scenarios

This completes the production-ready system by enhancing all previous modules.
```

### Prompt 11: End-to-End Integration

```text
Create the final integration layer that wires all components together.

Requirements:
1. Update `app.py` to integrate all modules:
   - Initialize all services on startup
   - Wire dependencies correctly
   - Set up background tasks
2. Create `main_flow.py` that orchestrates:
   - Receive SMS → Load customer → Process with AI → Send response
   - Handle all edge cases
   - Coordinate between all services
3. Configuration management:
   - Validate all environment variables
   - Set appropriate defaults
   - Environment-specific settings
4. Background tasks:
   - Conversation expiration
   - Cache cleanup
   - Metric collection
5. Deployment readiness:
   - Update requirements.txt with all dependencies
   - Finalize railway.toml
   - Add startup scripts
   - Include migration scripts
6. Comprehensive end-to-end tests:
   - New customer full flow
   - Returning customer with history
   - Complete purchase flow
   - Error scenarios
   - Rate limiting behavior
7. Demo data setup:
   - Sample customers
   - Book inventory
   - Conversation history
8. Documentation:
   - API documentation
   - Deployment guide
   - Testing guide

This creates the complete, production-ready Dungeon Books RCS Wizard system.
```
