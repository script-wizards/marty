# Marty - Dungeon Books RCS Wizard

An AI-powered SMS/RCS chatbot for book recommendations and purchases, built with FastAPI and SQLAlchemy.

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+** (required)
- **uv** package manager

### Development Environment Setup

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd marty
   ```

2. **Install uv (if not already installed)**

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Create virtual environment and install dependencies**

   ```bash
   uv venv
   uv sync --dev
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. **Initialize the database**

   ```bash
   uv run alembic upgrade head
   ```

6. **Run the development server**

   ```bash
   uv run python main.py
   ```

The API will be available at `http://localhost:8000`

## 🛠️ Development

### Project Structure

```text
marty/
├── alembic/              # Database migrations
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── tests/                # Test suite
├── config.py            # Configuration management
├── crud.py              # Database operations
├── database.py          # Database models and setup
├── hardcover_client.py  # Hardcover API integration
├── main.py              # FastAPI application
└── pyproject.toml       # Project configuration
```

### Key Dependencies

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM with async support
- **Alembic** - Database migrations
- **aiosqlite** - Async SQLite driver
- **Pydantic** - Data validation
- **Hypercorn** - ASGI server

### Development Commands

```bash
# Run the application
uv run python main.py

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Run linting and formatting
uv run ruff check .
uv run ruff format .

# Run all pre-commit hooks
uv run pre-commit run --all-files

# Database migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head

# Health check
curl http://localhost:8000/health
```

### Code Quality

This project uses:

- **Ruff** for linting and formatting
- **Pre-commit hooks** for automated code quality checks
- **Pytest** for testing with async support

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./marty.db

# Hardcover API (for book data)
HARDCOVER_API_TOKEN=your_token_here
HARDCOVER_API_URL=https://api.hardcover.app/v1/graphql
HARDCOVER_TOKEN_EXPIRY=2026-07-11T15:42:27

# Sinch SMS (for sending messages)
SINCH_SERVICE_PLAN_ID=your_service_plan_id
SINCH_API_TOKEN=your_api_token
SINCH_API_URL=https://us.sms.api.sinch.com

# Optional integrations
BOOKSTORE_API_URL=your_bookstore_api_url
BOOKSTORE_API_KEY=your_bookstore_api_key
BOOKSHOP_AFFILIATE_ID=your_affiliate_id
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_database.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=. --cov-report=html
```

### Test Structure

- `tests/test_database.py` - Database operations
- `tests/test_hardcover.py` - Hardcover API integration
- `tests/test_health.py` - Health check endpoint

## 📊 API Endpoints

### Health Check

```bash
GET /health
```

Returns application status and database connectivity.

## 🔧 Configuration

The application uses a centralized configuration system in `config.py`:

- Environment-based configuration
- Hardcover API token validation
- Database URL management
- Service integration settings

## 🚀 Deployment

### Production Setup

1. Set production environment variables
2. Use PostgreSQL instead of SQLite for production
3. Configure proper logging
4. Set up monitoring and health checks

### Docker (Future)

Docker support will be added for containerized deployment.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and pre-commit hooks
5. Submit a pull request

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "Add your feature"

# Push and create PR
git push origin feature/your-feature-name
```

## 📝 License

Copyright (c) 2025 Dungeon Books
All rights reserved.

This source code is proprietary and confidential.
Unauthorized copying, distribution, or use is strictly prohibited.

## 🆘 Support

For issues and questions:

- Check the documentation in `docs/`
- Review existing issues
- Create a new issue with detailed information
