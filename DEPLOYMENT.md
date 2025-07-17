# Deploying Marty to Railway

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Ensure your code is pushed to GitHub
3. **Environment Variables**: Prepare your production environment variables

## Deployment Steps

### 1. Connect to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link your project (run from project root)
railway link
```

### 2. Set Environment Variables

Set these required environment variables in Railway dashboard:

```bash
# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database

# AI Integration (Required)
ANTHROPIC_API_KEY=your_claude_api_key_here

# Book Data Integration (Required)
HARDCOVER_API_TOKEN=Bearer your_hardcover_api_token_here
HARDCOVER_API_URL=https://api.hardcover.app/v1/graphql
HARDCOVER_TOKEN_EXPIRY=2026-07-11T15:42:27

# SMS Provider Configuration
SINCH_API_TOKEN=your_sinch_api_token
SINCH_SERVICE_PLAN_ID=your_service_plan_id
SINCH_KEY_ID=your_sinch_key_id
SINCH_KEY_SECRET=your_sinch_key_secret
SINCH_PROJECT_ID=your_sinch_project_id

# Application Configuration
DEBUG=false
LOG_LEVEL=INFO
ENV=production

# Redis Configuration (if using Redis)
REDIS_URL=redis://your-redis-url:6379/0
```

### 3. Deploy

```bash
# Deploy to Railway
railway up

# Or deploy from Railway dashboard by connecting your GitHub repo
```

### 4. Database Setup

After deployment, run database migrations:

```bash
# Connect to Railway shell
railway shell

# Run migrations
uv run alembic upgrade head
```

### 5. Verify Deployment

Check your deployment:

```bash
# Get deployment URL
railway status

# Test health endpoint
curl https://your-app.railway.app/health
```

## Configuration Files

### railway.json
- Configures Railway deployment with internal networking
- Uses Nixpacks builder for consistent builds
- Enables internal service communication
- Defines start command and health checks

### Procfile
- Alternative deployment method
- Specifies the web process command

### runtime.txt
- Specifies Python version for Railway

## Production Considerations

### Railway Internal Networking
- Services communicate via internal network for better performance
- Database connections use internal URLs when possible
- Reduced latency and improved security

### Database
- Use Railway's managed PostgreSQL for internal networking
- Ensure connection pooling is configured
- Set up automated backups

### Environment Variables
- Never commit sensitive data to version control
- Use Railway's environment variable management
- Consider using Railway's secret management

### Monitoring
- Railway provides built-in monitoring
- Set up health checks (already configured)
- Monitor application logs

### Scaling
- Railway supports automatic scaling
- Configure resource limits as needed
- Monitor performance metrics

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check Python version compatibility
   - Verify all dependencies are in `pyproject.toml`
   - Ensure `uv sync` works locally

2. **Database Connection Issues**
   - Verify `DATABASE_URL` format
   - Check database accessibility
   - Ensure migrations are run

3. **Environment Variable Issues**
   - Verify all required variables are set
   - Check variable names and values
   - Restart deployment after variable changes

### Debug Commands

```bash
# View logs
railway logs

# Connect to shell
railway shell

# Check status
railway status

# Redeploy
railway up
```

## Security Best Practices

1. **API Keys**: Use Railway's secret management
2. **Database**: Use connection strings with proper authentication
3. **HTTPS**: Railway provides automatic HTTPS
4. **Environment**: Set `DEBUG=false` in production
5. **Logging**: Avoid logging sensitive information

## Cost Optimization

1. **Resource Limits**: Set appropriate CPU/memory limits
2. **Database**: Choose appropriate PostgreSQL plan
3. **Monitoring**: Use Railway's built-in monitoring
4. **Scaling**: Configure auto-scaling based on usage
