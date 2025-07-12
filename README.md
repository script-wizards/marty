# Marty - AI Bookstore Chatbot

an ai chatbot that recommends books via text. powered by claude ai.

marty is a burnt-out wizard who used to do software engineering and now works at dungeon books. he's genuinely magical but completely casual about it.

## What It Does

- chat with customers about books
- give book recommendations using claude ai
- remember conversation history
- integrate with hardcover api for book data
- handle customer info and orders (eventually)
- send responses that sound like a real person texting

## Tech Stack

- python 3.13+
- fastapi with async support
- hypercorn asgi server (dual-stack ipv4/ipv6)
- claude ai for conversations
- postgresql with sqlalchemy
- hardcover api for book data
- pytest for testing
- ruff for code quality
- uv for dependency management

## Requirements

- python 3.13+
- uv (for dependency management)
- postgresql database (supabase recommended)
- anthropic api key
- hardcover api token

## Setup

### Install Dependencies
```bash
# install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# clone repository
git clone <repository-url>
cd marty

# create virtual environment and install dependencies
uv sync
```

### Environment Setup
```bash
cp .env.example .env
# edit .env with your actual credentials
```

required environment variables:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
ANTHROPIC_API_KEY=your_claude_api_key_here
HARDCOVER_API_TOKEN=Bearer your_hardcover_token_here
```

### Database Setup

production (supabase):
```bash
# apply migrations
alembic upgrade head
```

local development (sqlite):
```bash
# set sqlite in .env
DATABASE_URL=sqlite+aiosqlite:///./marty.db

# apply migrations
alembic upgrade head
```

### Verify Setup
```bash
# test database connection
python database.py

# test claude integration
python scripts/smoke_test.py
```

### Run Application
```bash
python main.py
```

server runs on http://localhost:8000 with dual-stack ipv4/ipv6 binding

## API Endpoints

### Health Check
```
GET /health
```

returns database connectivity and system status

### Chat Interface
```
POST /chat
```

request:
```json
{
  "message": "looking for a good fantasy book",
  "phone": "+1234567890"
}
```

response:
```json
{
  "response": "try the name of the wind by rothfuss, really solid fantasy. good worldbuilding and the magic system is interesting",
  "conversation_id": "uuid",
  "customer_id": "uuid"
}
```

## Development

### Interactive Testing
```bash
python scripts/chat_with_marty.py
```

### Test Suite
```bash
# run all tests
pytest

# specific test files
pytest tests/test_ai_client.py
pytest tests/test_chat_endpoint.py
pytest tests/test_database.py

# with coverage
pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# install pre-commit hooks
pre-commit install

# format code
ruff format .

# lint code
ruff check .
```

### Database Migrations
```bash
# generate migration
alembic revision --autogenerate -m "description"

# apply migrations
alembic upgrade head

# rollback
alembic downgrade -1
```

## Configuration

### Claude AI
get api key from console.anthropic.com
add to .env as ANTHROPIC_API_KEY

### Hardcover API
request access at hardcover.app/api
add token as HARDCOVER_API_TOKEN=Bearer your_token

### Environment Variables
- DATABASE_URL: postgresql connection string
- ANTHROPIC_API_KEY: claude ai api key
- HARDCOVER_API_TOKEN: book data api token
- BOOKSHOP_AFFILIATE_ID: optional affiliate links
- DEBUG: true/false
- LOG_LEVEL: INFO/DEBUG

## Architecture

### AI Layer
claude ai handles conversation intelligence and book recommendations

### Database Layer
postgresql with async sqlalchemy for data persistence
alembic for schema migrations

### API Layer
fastapi with async endpoints
hypercorn asgi server for production deployment

### Personality System
marty's personality defined in prompts/marty_system_prompt.md
casual texting style with wizard references

## Database Schema

- customers: phone numbers and basic info
- conversations: message threads with context
- messages: individual texts with direction tracking
- books: catalog from hardcover api
- inventory: stock levels and availability
- orders: purchases and fulfillment

## Current Implementation Status

implemented:
- fastapi application with async support
- claude ai integration with conversation history
- database layer with migrations
- hardcover api integration
- comprehensive test suite
- terminal chat interface

in development:
- sms webhook handler
- square api for payments
- redis caching layer
- rate limiting
- purchase flow
- inventory management

## Troubleshooting

### Database Issues
```bash
# test connection
python database.py

# check environment
echo $DATABASE_URL

# reset database
alembic downgrade base
alembic upgrade head
```

### Claude AI Issues
```bash
# test integration
python scripts/smoke_test.py

# check api key
echo $ANTHROPIC_API_KEY
```

### Test Failures
```bash
# verbose output
pytest -v

# specific test with output
pytest tests/test_database.py -v -s
```

### Debug Mode
```bash
# add to .env
DEBUG=true
LOG_LEVEL=DEBUG
```

## Contributing

1. fork repository
2. create feature branch
3. make changes
4. run tests: pytest
5. run linting: ruff check .
6. submit pull request

## License

Copyright (c) 2025 Script Wizards
All rights reserved.

This source code is proprietary and confidential.
Unauthorized copying, distribution, or use is strictly prohibited.

---

built by a burnt-out wizard who knows books
