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
- [ ] Register with Anthropic for Claude API
- [ ] Get Claude API key
- [ ] Schedule meeting with Smobi representative
- [ ] Set up Bookshop.org affiliate account
- [ ] Create Railway account

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
- [ ] Write SQL migration for customers table
- [ ] Write SQL migration for conversations table
- [ ] Write SQL migration for books table
- [ ] Write SQL migration for inventory table
- [ ] Write SQL migration for orders table
- [ ] Write SQL migration for rate_limits table
- [ ] Execute migrations in Supabase
- [ ] Verify all tables created correctly

### Database Module

- [ ] Create `database.py` module
- [ ] Implement SupabaseClient class
- [ ] Add connection management with retries
- [ ] Implement customers table CRUD operations
- [ ] Implement conversations table CRUD operations
- [ ] Implement books table CRUD operations
- [ ] Implement inventory table CRUD operations
- [ ] Implement orders table CRUD operations
- [ ] Implement rate_limits table CRUD operations
- [ ] Add proper error handling
- [ ] Add logging for all operations
- [ ] Add type hints throughout

### Database Testing

- [ ] Create `test_database.py`
- [ ] Write tests for connection management
- [ ] Write tests for each CRUD operation
- [ ] Test error scenarios
- [ ] Test connection pooling
- [ ] Verify async operations work correctly
- [ ] Run tests with pytest

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

- [ ] Create `sms_handler.py` module
- [ ] Implement POST /webhook/sms endpoint
- [ ] Parse webhook payload
- [ ] Validate required fields
- [ ] Add request logging

### Security

- [ ] Implement HMAC signature verification
- [ ] Test with valid signatures
- [ ] Test with invalid signatures
- [ ] Handle missing signature header
- [ ] Add IP allowlist if provided by Smobi

### Message Processing

- [ ] Store incoming messages in database
- [ ] Mark messages as pending
- [ ] Return 200 immediately (async pattern)
- [ ] Create message queue structure
- [ ] Add timestamp tracking

### Rate Limiting

- [ ] Implement rate limit checking
- [ ] Track per-phone number limits
- [ ] Handle rate limit exceeded
- [ ] Clean up old rate limit records
- [ ] Test rate limiting logic

### Mock SMS Provider

- [ ] Create mock response function
- [ ] Log outgoing messages
- [ ] Simulate SMS sending
- [ ] Add response delay simulation
- [ ] Track sent messages

### Webhook Testing

- [ ] Create `test_sms_handler.py`
- [ ] Test valid webhook requests
- [ ] Test signature verification
- [ ] Test missing fields
- [ ] Test rate limiting
- [ ] Test database integration

## Step 4: Square Customer Integration

### Square Client

- [ ] Create `square_client.py` module
- [ ] Implement SquareClient class
- [ ] Configure Square SDK
- [ ] Handle environment switching (sandbox/prod)
- [ ] Add request logging

### Customer Operations

- [ ] Implement search_customer_by_phone
- [ ] Implement get_customer
- [ ] Implement create_customer
- [ ] Implement get_customer_orders
- [ ] Handle Square API errors
- [ ] Add retry logic

### Customer Sync

- [ ] Check local database first
- [ ] Search Square if not found locally
- [ ] Create local customer record
- [ ] Sync Square data to local
- [ ] Implement 24-hour cache

### Integration

- [ ] Integrate with SMS handler
- [ ] Add customer lookup on message
- [ ] Store customer_id in conversation
- [ ] Handle new vs returning customers
- [ ] Update conversation with customer data

### Square Testing

- [ ] Create `test_square_client.py`
- [ ] Mock Square API responses
- [ ] Test customer search
- [ ] Test customer creation
- [ ] Test error handling
- [ ] Test cache behavior

## Step 5: Book Data Service

### Hardcover Client

- [ ] Create `book_service.py` module
- [ ] Implement HardcoverClient class
- [ ] Add authentication headers
- [ ] Implement search_books method
- [ ] Implement get_book_details method
- [ ] Handle API errors

### Inventory Management

- [ ] Implement check_inventory
- [ ] Implement update_inventory
- [ ] Track store vs bookshop availability
- [ ] Generate affiliate links
- [ ] Add inventory cache

### Book Data Features

- [ ] Merge API data with inventory
- [ ] Cache book data for 7 days
- [ ] Extract book mentions from text
- [ ] Track ISBN detection
- [ ] Handle fuzzy title matching

### Book Service Testing

- [ ] Create `test_book_service.py`
- [ ] Mock Hardcover API
- [ ] Test book search
- [ ] Test inventory checks
- [ ] Test cache behavior
- [ ] Test mention extraction

## Step 6: Conversation Manager

### Conversation Module

- [ ] Create `conversation_manager.py`
- [ ] Implement ConversationManager class
- [ ] Design message storage format
- [ ] Add timestamp tracking
- [ ] Include metadata structure

### Core Features

- [ ] Implement load_conversation
- [ ] Implement add_message
- [ ] Implement get_context
- [ ] Track mentioned books
- [ ] Handle conversation expiration
- [ ] Manage conversation state

### Context Management

- [ ] Limit to 10 recent messages
- [ ] Implement message summarization
- [ ] Track conversation threads
- [ ] Handle concurrent messages
- [ ] Add thread safety

### Book References

- [ ] Extract book mentions
- [ ] Create mention index
- [ ] Handle "that book" references
- [ ] Link to inventory
- [ ] Track purchase intent

### Conversation Testing

- [ ] Create `test_conversation_manager.py`
- [ ] Test message storage
- [ ] Test context retrieval
- [ ] Test book tracking
- [ ] Test expiration
- [ ] Test concurrent access

## Step 7: Claude AI Integration

### AI Client

- [ ] Create `ai_client.py` module
- [ ] Implement ClaudeClient class
- [ ] Configure API authentication
- [ ] Set up retry logic
- [ ] Add timeout handling

### Prompt Management

- [ ] Load base Marty prompt
- [ ] Implement context injection
- [ ] Add dynamic variables
- [ ] Include store hours logic
- [ ] Format customer context

### Response Processing

- [ ] Implement generate_response
- [ ] Parse AI responses
- [ ] Extract book references
- [ ] Detect purchase intent
- [ ] Identify required actions

### Error Handling

- [ ] Handle API timeouts
- [ ] Implement fallback responses
- [ ] Add rate limit handling
- [ ] Log all API calls
- [ ] Track token usage

### AI Testing

- [ ] Create `test_ai_client.py`
- [ ] Mock Claude API
- [ ] Test response generation
- [ ] Test context building
- [ ] Test error scenarios
- [ ] Test response parsing

## Step 8: Marty Personality

### Personality Module

- [ ] Create `marty_personality.py`
- [ ] Load system prompt from file
- [ ] Parse prompt structure
- [ ] Implement personality rules
- [ ] Add context awareness

### Response Features

- [ ] Implement casual texting style
- [ ] Add message breaking logic
- [ ] Include wizard references
- [ ] Format error messages in character
- [ ] Handle store hours

### Context Features

- [ ] Reference purchase history
- [ ] Remember conversation books
- [ ] Detect customer type
- [ ] Add time awareness
- [ ] Include inventory status

### Message Formatting

- [ ] Implement SMS character limits
- [ ] Find natural break points
- [ ] Remove special formatting
- [ ] Handle multi-message responses
- [ ] Test message splitting

### Personality Testing

- [ ] Create `test_marty_personality.py`
- [ ] Test response style
- [ ] Test message breaking
- [ ] Test personality consistency
- [ ] Test error messages
- [ ] Test context awareness

## Step 9: Purchase Flow

### Purchase Module

- [ ] Create `purchase_flow.py`
- [ ] Design flow state machine
- [ ] Track purchase progress
- [ ] Handle flow interruptions
- [ ] Add timeout handling

### Intent Detection

- [ ] Identify purchase phrases
- [ ] Resolve book references
- [ ] Handle ambiguous references
- [ ] Confirm book selection
- [ ] Track intent confidence

### Fulfillment

- [ ] Ask shipping vs pickup
- [ ] Collect shipping address
- [ ] Handle pickup options
- [ ] Process payment choice
- [ ] Create hold requests

### Order Processing

- [ ] Create Square orders
- [ ] Generate payment links
- [ ] Update inventory
- [ ] Send confirmations
- [ ] Handle bookshop redirects

### Purchase Testing

- [ ] Create `test_purchase_flow.py`
- [ ] Test intent detection
- [ ] Test fulfillment flow
- [ ] Test order creation
- [ ] Test error cases
- [ ] Test complete flow

## Step 10: Production Features

### Rate Limiting

- [ ] Create `production_utils.py`
- [ ] Implement per-phone limits
- [ ] Add global API limits
- [ ] Create backoff strategies
- [ ] Add circuit breakers
- [ ] Test under load

### Enhanced Error Handling

- [ ] Catch all edge cases
- [ ] Add personality to errors
- [ ] Implement retry logic
- [ ] Add fallback responses
- [ ] Log all errors properly

### Monitoring

- [ ] Track response times
- [ ] Monitor API success rates
- [ ] Add conversation metrics
- [ ] Track error rates
- [ ] Create metric dashboards

### Performance

- [ ] Optimize database queries
- [ ] Add connection pooling
- [ ] Implement caching strategy
- [ ] Add async where beneficial
- [ ] Profile bottlenecks

### Security

- [ ] Sanitize all inputs
- [ ] Prevent SQL injection
- [ ] Validate phone numbers
- [ ] Add request validation
- [ ] Test security measures

### Production Testing

- [ ] Create `test_production_utils.py`
- [ ] Load test the system
- [ ] Test rate limiting
- [ ] Test error scenarios
- [ ] Test monitoring
- [ ] Verify security measures

## Step 11: Final Integration

### Main Flow

- [ ] Create `main_flow.py`
- [ ] Wire all components
- [ ] Implement message flow
- [ ] Handle all paths
- [ ] Add state management

### App Integration

- [ ] Update `app.py`
- [ ] Initialize all services
- [ ] Set up dependencies
- [ ] Configure background tasks
- [ ] Add graceful shutdown

### Background Tasks

- [ ] Expire old conversations
- [ ] Clean up cache
- [ ] Collect metrics
- [ ] Process pending messages
- [ ] Handle retries

### Configuration

- [ ] Validate all env vars
- [ ] Set production defaults
- [ ] Add config validation
- [ ] Environment detection
- [ ] Secret management

### Deployment Prep

- [ ] Finalize requirements.txt
- [ ] Update railway.toml
- [ ] Create startup script
- [ ] Add health checks
- [ ] Configure logging

### End-to-End Testing

- [ ] Test new customer flow
- [ ] Test returning customer
- [ ] Test complete purchase
- [ ] Test error scenarios
- [ ] Test rate limiting
- [ ] Test all integrations

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
