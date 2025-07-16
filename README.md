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
- ty for type checking
- uv for dependency management
- just for command running

## Requirements

- python 3.13+
- uv (for dependency management)
- just (for command running)
- postgresql database (supabase recommended)
- anthropic api key
- hardcover api token

## Setup

### Install Dependencies
```bash
# install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# install just command runner
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin

# install GNU parallel (required for CI and fast local checks)
# Debian/Ubuntu:
sudo apt-get update && sudo apt-get install -y parallel
# macOS (with Homebrew):
brew install parallel

# clone repository
git clone <repository-url>
cd marty

# complete project setup
just setup
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

# comprehensive integration test (⚠️ makes real API calls - costs money)
python scripts/smoke_test.py
```

### Run Application

Development server with hot reload:
```bash
uv run fastapi dev main.py
```

Production server:
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

### Development Scripts

**Interactive Testing** (internal use only):
```bash
just chat
```
Terminal chat interface for testing AI responses without SMS pipeline.

**Integration Testing** (⚠️ costs money):
```bash
# enable real API calls and run smoke test
MARTY_ENABLE_REAL_API_TESTS=1 just smoke-test
```
Comprehensive test of all integrations: Claude AI, Hardcover API, and database.
Makes real API calls - use sparingly.

### Test Suite

**Unit Tests** (fast, no infrastructure):
```bash
# run unit tests only
just ci

# or manually
pytest -m "not integration"
```

**Integration Tests** (requires infrastructure):
```bash
# run all tests including integration
just test-all

# run only integration tests
just test-integration
```

**Additional Test Commands**:
```bash
# specific test files
just test-file test_ai_client.py

# with coverage
just test-cov

# verbose output
just test-verbose
```

**AI Testing**: All Claude AI calls are automatically mocked in tests to prevent costs. Real API calls only happen in smoke tests when `MARTY_ENABLE_REAL_API_TESTS=1` is set.

### Code Quality

**Pre-commit Hooks** (recommended):
```bash
# install hooks (runs linting, type checking, and unit tests)
just pre-commit-install

# run all pre-commit checks manually
just pre-commit-run
```

**Manual Code Quality**:
```bash
# format code
just format

# lint code
just lint

# type check
just check

# run all checks
just check-all
```

### Database Migrations
```bash
# generate migration
just db-revision "description"

# apply migrations
just db-migrate

# rollback
just db-rollback

# reset database
just db-reset
```

## CI/CD Infrastructure

**Available Commands**:
```bash
# show all available commands
just --list

# fast CI checks (no infrastructure)
just ci

# full CI with integration tests
just ci-full

# watch mode for development
just watch
```

**Parallelized Checks:**
- Lint, type check, and security scan (Bandit) are run in parallel for faster feedback using GNU parallel.
- GNU parallel is required for CI and pre-commit hooks. On Linux, it is auto-installed by pre-commit/CI. On macOS, install it manually with `brew install parallel`.
- If you see errors like `parallel: command not found`, install GNU parallel as above.

**Test Infrastructure**:
- Docker Compose setup for isolated testing
- PostgreSQL and Redis containers for integration tests
- Automatic infrastructure management with `just test-all`
- CI-ready with proper test isolation

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
just test-db

# check environment
echo $DATABASE_URL

# reset database
just db-reset
```

### Claude AI Issues
```bash
# test integration (⚠️ costs money)
MARTY_ENABLE_REAL_API_TESTS=1 just smoke-test

# check api key
echo $ANTHROPIC_API_KEY
```

### GNU parallel Not Found
If you see errors about `parallel: command not found` during CI or local runs, install GNU parallel:
- **Debian/Ubuntu:** `sudo apt-get update && sudo apt-get install -y parallel`
- **macOS (Homebrew):** `brew install parallel`

### Test Failures
```bash
# run unit tests only (fast)
just ci

# verbose output
just test-verbose

# specific test with output
just test-file test_database.py

# check if integration tests need infrastructure
just test-integration
```

### CI/CD Issues
```bash
# check pre-commit setup
just pre-commit-run

# verify all quality checks pass
just check-all

# full CI pipeline
just ci-full
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
4. run quality checks: `just check-all`
5. run tests: `just ci`
6. commit (pre-commit hooks run automatically)
7. submit pull request

**Development Workflow**:
- Use `just ci` for fast feedback during development
- Use `just test-all` for comprehensive testing before commits
- Pre-commit hooks enforce code quality automatically

## License

Copyright (c) 2025 Script Wizards
All rights reserved.

This source code is proprietary and confidential.
Unauthorized copying, distribution, or use is strictly prohibited.
