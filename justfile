# Marty - AI Bookstore Chatbot Justfile
# Just is a command runner: https://github.com/casey/just

# Default recipe - show available commands
default:
    @just --list

# Dependency Management
install:
    # Install all dependencies using uv
    uv sync

install-dev:
    # Install dependencies including development tools
    uv sync --group dev

add package:
    # Add a production dependency
    uv add {{package}}

add-dev package:
    # Add a development dependency
    uv add --group dev {{package}}

# Development Server
dev:
    # Start development server with hot reload
    uv run fastapi dev main.py

run:
    # Start production server
    python main.py

# Testing
test:
    # Run all tests
    pytest

test-verbose:
    # Run tests with verbose output
    pytest -v

test-file file:
    # Run specific test file
    pytest tests/{{file}}

test-cov:
    # Run tests with coverage report
    pytest --cov=. --cov-report=html

# Code Quality
format:
    # Format code with ruff
    ruff format .

lint:
    # Lint code with ruff
    ruff check .

lint-fix:
    # Auto-fix linting issues
    ruff check --fix .

check:
    # Run format and lint checks
    just format
    just lint

# Database Operations
db-migrate:
    # Apply database migrations
    alembic upgrade head

db-rollback:
    # Rollback last migration
    alembic downgrade -1

db-reset:
    # Reset database to base and reapply all migrations
    alembic downgrade base
    alembic upgrade head

db-revision message:
    # Generate new migration
    alembic revision --autogenerate -m "{{message}}"

# Development Scripts
chat:
    # Start interactive chat with Marty (internal testing)
    python scripts/chat_with_marty.py

smoke-test:
    # Run comprehensive integration test (⚠️ costs money)
    python scripts/smoke_test.py

test-db:
    # Test database connection
    python database.py

# Setup and Installation
setup:
    # Complete project setup
    @echo "Setting up Marty project..."
    just install-dev
    @echo "Installing pre-commit hooks..."
    pre-commit install
    @echo "Setup complete! Don't forget to:"
    @echo "1. Copy .env.example to .env"
    @echo "2. Add your API keys to .env"
    @echo "3. Run 'just db-migrate' to setup database"

setup-env:
    # Create .env file from example
    cp .env.example .env
    @echo "Created .env file. Please edit with your API keys."

# Pre-commit
pre-commit-install:
    # Install pre-commit hooks
    pre-commit install

pre-commit-run:
    # Run pre-commit on all files
    pre-commit run --all-files

# Cleanup
clean:
    # Clean up generated files
    rm -rf .pytest_cache
    rm -rf .ruff_cache
    rm -rf htmlcov
    rm -rf .coverage
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete

# Health Checks
health:
    # Check system health
    @echo "Testing database connection..."
    just test-db
    @echo "Running basic tests..."
    just test

# Help
help:
    # Show detailed help for all commands
    @echo "Marty - AI Bookstore Chatbot"
    @echo ""
    @echo "Development:"
    @echo "  just dev          - Start development server"
    @echo "  just run          - Start production server"
    @echo "  just chat         - Interactive chat testing"
    @echo ""
    @echo "Testing:"
    @echo "  just test         - Run all tests"
    @echo "  just test-cov     - Run tests with coverage"
    @echo "  just smoke-test   - Integration test (⚠️ costs money)"
    @echo ""
    @echo "Code Quality:"
    @echo "  just format       - Format code"
    @echo "  just lint         - Lint code"
    @echo "  just check        - Format and lint"
    @echo ""
    @echo "Database:"
    @echo "  just db-migrate   - Apply migrations"
    @echo "  just db-reset     - Reset database"
    @echo "  just db-revision  - Create new migration"
    @echo ""
    @echo "Dependencies:"
    @echo "  just install      - Install dependencies"
    @echo "  just install-dev  - Install with dev tools"
    @echo "  just add          - Add production dependency"
    @echo "  just add-dev      - Add development dependency"
