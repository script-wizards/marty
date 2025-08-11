# Dungeon Books SMS Wizard - Developer Specification

## Project Overview

**Goal:** Text-based AI book recommendation system with personality-driven commerce integration
**Timeline:** 2 weeks (hackathon scope)
**Team:** Panat (generalist/AI/infra), Christian (Python/Postgres expert)
**MVP Success:** Functional SMS bot that feels like texting a human bookseller

## Core Value Proposition

Customers text "Marty" (an AI wizard who used to work in tech) for book recommendations. Marty has access to customer purchase history, store inventory, and can facilitate purchases through conversational commerce.

## Technical Architecture

### Stack

- **Backend:** Python application on Railway
- **Database:** Supabase (PostgreSQL)
- **SMS:** Sinch SMS API
- **AI:** Claude Sonnet 4 API
- **Book Data:** Hardcover API
- **Customer/Orders:** Square API
- **Fulfillment:** Store inventory + Bookshop.org affiliate links

### Architecture Pattern

**Monolithic containerized application** - all logic in single Railway deployment for MVP simplicity

### Service Integration Flow

```
SMS Message → Railway Webhook → Customer Lookup (Square) →
Conversation Processing (Claude + Context) → Book Lookup (Hardcover/Inventory) →
Response Generation → SMS Response
```

## Database Schema (Supabase)

```sql
-- Customer data synced from Square
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    square_customer_id VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversation state and history
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    phone VARCHAR(20) NOT NULL,
    messages JSONB DEFAULT '[]', -- Array of {role, content, timestamp}
    mentioned_books JSONB DEFAULT '[]', -- Books referenced in conversation
    last_activity TIMESTAMP DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE
);

-- Book inventory and metadata
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isbn VARCHAR(20),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(300),
    publisher VARCHAR(200),
    metadata JSONB DEFAULT '{}', -- Hardcover API response
    created_at TIMESTAMP DEFAULT NOW()
);

-- Store inventory tracking
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID REFERENCES books(id),
    in_stock_count INTEGER DEFAULT 0,
    source VARCHAR(50) DEFAULT 'store', -- 'store', 'bookshop'
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Order tracking
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    book_id UUID REFERENCES books(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, paid, shipped, completed, cancelled
    fulfillment_type VARCHAR(50), -- shipping, pickup, hold
    square_order_id VARCHAR(255),
    total_amount INTEGER, -- cents
    created_at TIMESTAMP DEFAULT NOW()
);

-- Rate limiting and security
CREATE TABLE rate_limits (
    phone VARCHAR(20) PRIMARY KEY,
    message_count INTEGER DEFAULT 0,
    window_start TIMESTAMP DEFAULT NOW()
);
```

## API Integrations

### 1. SMS Provider (Sinch)

**Webhook endpoint:** `POST /webhook/sms`

```python
# Sinch webhook payload structure
{
    "body": "hey marty",
    "from": "19876543210",
    "to": "12345678900",
    "id": "message-id",
    "received_at": "2023-01-01T12:00:00Z"
}
```

### 2. Claude API

**Model:** `claude-sonnet-4-20250514`

```python
# System prompt injection with dynamic context
system_prompt = base_marty_prompt + f"""
Current customer: {customer_name or 'new customer'}
Purchase history: {purchase_history}
Recent conversation: {conversation_context}
Current time: {current_time}
Store status: {'open' if store_open else 'closed'}
"""
```

### 3. Square API

**Endpoints needed:**

- `GET /v2/customers/search` - Find customer by phone
- `GET /v2/customers/{customer_id}` - Get customer details
- `POST /v2/orders` - Create new order
- `GET /v2/catalog/list` - Get inventory (if using Square catalog)

### 4. Hardcover API

**Endpoints:**

- `GET /books/search?query={title}` - Book search
- `GET /books/{id}` - Book details

### 5. Bookshop.org

**Integration:** Affiliate links only (no API confirmed) **URL pattern:** `https://bookshop.org/shop/dungeonbooks?search={isbn}`

## Core Functionality

### 1. Webhook Handler

```python
@app.route('/webhook/sms', methods=['POST'])
async def handle_sms_webhook():
    # 1. Verify webhook signature
    # 2. Extract message data
    # 3. Rate limiting check
    # 4. Process conversation
    # 5. Send response
    # 6. Log interaction
```

### 2. Conversation Processing

```python
async def process_conversation(phone: str, message: str):
    # 1. Load/create customer record (JIT from Square)
    # 2. Load conversation context
    # 3. Check store hours
    # 4. Generate Claude response with context
    # 5. Handle book lookups if needed
    # 6. Update conversation state
    # 7. Return response
```

### 3. Customer Management (JIT Lookup)

```python
async def get_or_create_customer(phone: str):
    # 1. Check Supabase for existing customer
    # 2. If not found, search Square by phone
    # 3. Create Supabase record with Square data
    # 4. Return customer object
```

### 4. Book Recommendations

```python
async def handle_book_query(query: str, customer_context: dict):
    # 1. Search Hardcover API
    # 2. Check local inventory
    # 3. Enrich with Marty's commentary
    # 4. Store mentioned books in conversation
```

### 5. Order Processing

```python
async def handle_purchase_intent(customer_id: str, book_ref: str):
    # 1. Resolve book reference from conversation
    # 2. Check inventory/pricing
    # 3. Ask fulfillment preference (ship/pickup/hold)
    # 4. Create Square order or hold record
    # 5. Generate payment link if needed
```

## Marty AI Configuration

### System Prompt Structure

```python
BASE_PROMPT = """
You are Martinus Trismegistus (Marty), wizard mascot of Dungeon Books...
[Full prompt from previous document]
"""

DYNAMIC_CONTEXT = """
CUSTOMER CONTEXT:
- Name: {customer_name}
- Phone: {phone}
- Previous purchases: {purchase_history}
- Conversation history: {recent_messages}

CURRENT STATE:
- Time: {current_time}
- Store status: {store_status}
- Mentioned books this conversation: {mentioned_books}

INSTRUCTIONS:
- Reference customer's purchase history naturally when relevant
- Use store hours to set availability
- Remember books mentioned in this conversation for easy reference
"""
```

### Response Processing

```python
async def generate_marty_response(message: str, context: dict):
    # 1. Combine base prompt + dynamic context
    # 2. Call Claude API
    # 3. Parse response for book references
    # 4. Check for order intent
    # 5. Split into SMS-appropriate chunks
    # 6. Return message array
```

## Message Handling

### Multi-Message Responses

```python
def split_response(text: str) -> List[str]:
        return split_sms_messages(text, max_length=150)
```

### Conversation Threading

```python
# Store conversation context per phone number
CONVERSATION_TIMEOUT = 3 * 60 * 60  # 3 hours

async def update_conversation(phone: str, role: str, content: str):
    # 1. Load existing conversation
    # 2. Append new message
    # 3. Trim old messages if > 10 entries
    # 4. Update last_activity timestamp
    # 5. Extract book references for easy lookup
```

## Error Handling

### Error Response Mapping

```python
ERROR_RESPONSES = {
    'claude_api_timeout': "sorry my brain's lagging, give me a moment",
    'square_api_error': "payment spell's acting up, try again in a sec",
    'book_lookup_failed': "hmm that book might exist in another dimension, lemme double check",
    'inventory_error': "system's being weird, call the store if this keeps happening",
    'general_timeout': "glitch in the simulation, try that again",
    'rate_limited': "whoa slow down there, give me a sec to catch up"
}
```

### Error Handler

```python
async def handle_error(error_type: str, context: dict) -> str:
    # 1. Log error details
    # 2. Return in-character error message
    # 3. Flag for manual review if critical
```

## Security Implementation

### Webhook Verification

```python
def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### Rate Limiting

```python
RATE_LIMITS = {
    'messages_per_minute': 10,
    'messages_per_hour': 100
}

async def check_rate_limit(phone: str) -> bool:
    # 1. Get current window counts
    # 2. Check against limits
    # 3. Update counters
    # 4. Return allowed/denied
```

## Business Logic

### Store Hours

```python
STORE_HOURS = {
    'open_time': '10:00',
    'close_time': '22:00',  # 10pm
    'timezone': 'America/New_York'
}

def is_store_open() -> bool:
    # Check current time against business hours
```

### Fulfillment Options

```python
async def handle_purchase_flow(customer_id: str, book_id: str):
    # 1. "cool! want me to ship it or you picking up?"
    # 2. If shipping: get address, create order, send payment link
    # 3. If pickup: "want to pay now or just hold it for you?"
    # 4. Process accordingly
```

### Inventory Priority

```python
def get_book_availability(book_id: str):
    # 1. Check store inventory first
    # 2. Check bookshop.org availability
    # 3. Return options with pricing
    # 4. Prioritize store inventory in recommendations
```

## Implementation Timeline (2 Weeks)

### Week 1: Core Infrastructure (Christian Focus)

**Days 1-2:**

- Set up Railway deployment
- Configure Supabase database and schema
- Implement basic webhook handler with signature verification
- Set up rate limiting

**Days 3-4:**

- Integrate Square API for customer lookup
- Implement JIT customer creation
- Build conversation state management
- Basic Claude API integration

**Days 5-7:**

- Hardcover API integration
- Book search and inventory checking
- Message splitting and multi-message responses
- Error handling framework

### Week 2: AI Integration & Polish (Panat Focus)

**Days 8-10:**

- Refine Marty system prompt
- Implement dynamic context injection
- Conversation flow testing and optimization
- Book recommendation logic

**Days 11-12:**

- Order flow implementation
- Purchase intent handling
- Bookshop.org affiliate link generation
- End-to-end testing

**Days 13-14:**

- Demo preparation
- Social media content creation
- Performance optimization
- Bug fixes and polish

## Testing Strategy

### Manual Testing Scenarios

1. **First-time customer flow**

    - New phone number texts Marty
    - Request book recommendation
    - Purchase in-stock book
    - Verify Square integration
2. **Returning customer flow**

    - Existing customer texts
    - Marty references purchase history
    - Order out-of-stock book (bookshop.org handoff)
3. **Edge cases**

    - Rate limiting behavior
    - API failures and error responses
    - Conversation timeout and context loss
    - Off-hours messaging
4. **Conversation quality**

    - Personality consistency
    - Book recommendation accuracy
    - Natural conversation flow
    - Multi-message responses

### Testing with Real Customers

- Use existing Dungeon Books customers
- Start with 10-15 friendly customers for feedback
- Iterate on Marty's personality based on reactions
- Monitor conversation logs for improvement opportunities

## Monitoring & Admin

### Logging Strategy

```python
# Log all interactions for debugging
logger.info("SMS received", extra={
    "phone": phone,
    "message": message,
    "conversation_id": conv_id
})

logger.info("Claude response", extra={
    "phone": phone,
    "response": response,
    "token_count": tokens,
    "response_time": elapsed
})
```

### Admin Interface (MVP)

- **Supabase Dashboard:** View all conversations, customers, orders
- **Railway Logs:** Real-time conversation monitoring
- **Manual intervention:** Direct database access for edge cases

## Deployment Configuration

### Railway Setup

```yaml
# railway.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "python app.py"
healthcheckPath = "/health"

[env]
CLAUDE_API_KEY = "sk-ant-..."
SQUARE_ACCESS_TOKEN = "EAAAl..."
SQUARE_APPLICATION_ID = "sandbox-sq0idb-..."
HARDCOVER_API_KEY = "hc_..."
SUPABASE_URL = "https://..."
SUPABASE_ANON_KEY = "eyJhbGc..."
SINCH_WEBHOOK_SECRET = "webhook_secret"
```

### Environment Variables

```bash
# AI Service
CLAUDE_API_KEY=sk-ant-...

# SMS Provider
SINCH_API_TOKEN=your_sinch_api_token
SINCH_SERVICE_PLAN_ID=your_service_plan_id
SINCH_WEBHOOK_SECRET=webhook_secret

# Square Integration
SQUARE_ACCESS_TOKEN=EAAAl...
SQUARE_APPLICATION_ID=sandbox-sq0idb...
SQUARE_ENVIRONMENT=sandbox  # or production

# Book Data
HARDCOVER_API_KEY=hc_...

# Database
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...

# Business Config
BOOKSHOP_AFFILIATE_ID=dungeonbooks
STORE_TIMEZONE=America/New_York
```

## Key Integration Points

### Sinch Integration (Pending)

- Confirm webhook payload format
- Set up phone number provisioning
- Test SMS detection
- Configure message delivery options

### Square Integration Requirements

- Customer search by phone number
- Order creation and management
- Payment link generation
- Inventory tracking (if using Square catalog)

### Bookshop.org Integration

- Confirm affiliate program setup
- Test link generation with ISBNs
- Verify attribution tracking

## Success Metrics

### Technical Goals

- [ ] Functional SMS bidirectional communication
- [ ] Sub-30 second response times for recommendations
- [ ] Conversation context maintained across sessions
- [ ] End-to-end purchase flow working
- [ ] Error handling doesn't break character

### Business Goals

- [ ] 10+ customers successfully use the system
- [ ] 3+ actual purchases through Marty
- [ ] Positive social media reactions
- [ ] Demo-ready conversation screenshots
- [ ] Viral potential validated

## Post-MVP Roadmap

### Immediate Improvements (Weeks 3-4)

- Ingram API integration for broader inventory
- Advanced conversation analytics
- Customer preference learning
- Payment processing optimization

### Long-term Features (Months 2-3)

- Multi-store licensing
- Advanced recommendation ML
- Voice message support
- Library partnership integration

## Risk Mitigation

### Technical Risks

- **Claude API reliability:** Implement retry logic and fallback responses
- **SMS provider issues:** Have backup provider ready
- **Rate limiting:** Monitor usage and adjust limits proactively

### Business Risks

- **Customer adoption:** Start with existing customer base
- **Conversation quality:** Extensive testing with real users
- **Order fulfillment:** Keep manual oversight during MVP

## Contact & Support

### Development Team

- **Panat:** AI integration, infrastructure, prompt engineering
- **Christian:** Backend development, database design, API integrations

### External Dependencies

- **Sinch:** SMS 10DLC Registration
- **Square support:** API troubleshooting
- **Hardcover:** Book data API access

---

This specification provides complete implementation guidance for a 2-week MVP while maintaining flexibility for future enhancements. Focus on core functionality first, polish second, and prioritize user experience over feature completeness.
