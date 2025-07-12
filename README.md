# Marty - SMS Bookstore Chatbot 🤖📚

AI-powered SMS chatbot for book recommendations and store management.

## Features

- 📱 SMS-based book recommendations
- 📖 Integration with Hardcover API for book data
- 🛒 Order management and inventory tracking
- 💬 Conversation history and context
- 🔍 Smart book search and recommendations

## Quick Start

### 1. Database Setup

#### Option A: Supabase (Recommended for Production)

1. **Create a Supabase project:**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and password

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   ```

3. **Initialize the database:**
   ```bash
   python database.py
   ```

#### Option B: SQLite (Development)

For local development, you can use SQLite:
```bash
DATABASE_URL=sqlite+aiosqlite:///./marty.db
```

### 2. Test Database Connection

Run the database test script:
```bash
python database.py
```

You should see output like:
```
🔍 Testing Marty Database Connection...
📋 Database URL: postgresql+asyncpg://postgres:***@db.your-project.supabase.co:5432/postgres
🏗️  Supabase Project: your-project-ref
✅ Database connection successful. Server time: 2024-01-01 12:00:00
🚀 Initializing database tables...
✅ Database tables created successfully
✅ Database setup complete!
```

### 3. Configure External Services

Edit your `.env` file with:

```env
# Hardcover API (for book data)
HARDCOVER_API_TOKEN=Bearer your_token_here

# Sinch SMS (for messaging)
SINCH_SERVICE_PLAN_ID=your_service_plan_id
SINCH_API_TOKEN=your_api_token

# Optional: Bookshop affiliate
BOOKSHOP_AFFILIATE_ID=your_affiliate_id
```

### 4. Run the Application

```bash
python main.py
```

## Database Schema

The application uses the following main tables:

- **customers** - Customer information and phone numbers
- **conversations** - SMS conversation threads
- **messages** - Individual SMS messages
- **books** - Book catalog with metadata
- **inventory** - Stock levels and availability
- **orders** - Purchase orders and fulfillment
- **order_items** - Individual items in orders

## Supabase Configuration

### Connection Pooling

The application is configured with optimal connection pooling for Supabase:

- **Pool size**: 20 connections
- **Pool recycle**: 5 minutes
- **Pre-ping**: Enabled for connection health checks
- **JIT disabled**: For better connection stability

### Performance Optimizations

- Async PostgreSQL driver (`asyncpg`)
- Proper indexing on frequently queried columns
- Connection pooling with health checks
- Automatic rollback on errors

### Monitoring

Use the built-in database utilities:

```python
from database import test_db_connection, is_supabase_url, get_supabase_project_ref

# Test connection
await test_db_connection()

# Check if using Supabase
if is_supabase_url(DATABASE_URL):
    project_ref = get_supabase_project_ref(DATABASE_URL)
    print(f"Supabase project: {project_ref}")
```

## Development

### Database Migrations

The application uses Alembic for database migrations:

```bash
# Generate migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head
```

### Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Troubleshooting

### Common Supabase Issues

1. **Connection timeout**: Check your internet connection and Supabase project status
2. **Authentication failed**: Verify your password and project URL
3. **SSL errors**: Ensure you're using `postgresql+asyncpg://` protocol

### Debug Mode

Enable debug mode in your `.env`:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Then check database logs by setting `echo=True` in the database engine configuration.

## License

MIT License - see LICENSE file for details.
