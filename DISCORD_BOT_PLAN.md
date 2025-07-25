# Marty Discord Bot Implementation Plan

## Overview
Adapt Marty (AI bookstore assistant) to work as a Discord bot while maintaining existing SMS functionality. This allows testing the conversational AI while waiting for 10DLC SMS approval.

## Architecture Approach

### Option 1: Unified FastAPI Service (Recommended)
- Keep existing FastAPI application as main service
- Add Discord webhook endpoint alongside SMS webhook
- Reuse existing conversation logic, database models, and AI client
- Single deployment, shared infrastructure

### Option 2: Separate Discord Bot Service
- Create standalone Discord bot using discord.py
- Connect to same database and AI services
- More complex deployment but cleaner separation

**Recommendation: Option 1** - Leverages existing infrastructure and keeps codebase unified.

## Technical Implementation

### Required Dependencies
```python
# Add to existing requirements
discord.py>=2.5.2
```

### New Files to Create
```
src/discord_bot/
├── __init__.py
├── bot.py              # Discord bot client and event handlers
├── message_handler.py  # Process Discord messages (similar to SMS handler)
└── formatters.py       # Format responses for Discord (embeds, etc.)

scripts/
└── discord_test.py     # Testing script for Discord interactions
```

### Key Components

#### 1. Discord Bot Client (`src/discord_bot/bot.py`)
```python
import discord
from discord.ext import commands
from src.sms_handler import process_conversation  # Reuse existing logic

class MartyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def on_message(self, message):
        # Process through existing conversation logic
        # Map Discord user ID to phone number equivalent
        # Handle Discord-specific formatting
```

#### 2. Message Handler (`src/discord_bot/message_handler.py`)
```python
async def process_discord_message(user_id: str, username: str, message: str):
    # Convert Discord user to customer context
    # Reuse existing conversation processing
    # Format response for Discord
    # Handle Discord-specific features (embeds, reactions)
```

#### 3. Database Integration
- Map Discord user IDs to existing `customers` table
- Use `discord_user_id` field instead of `phone` for identification
- Reuse existing `conversations` and `messages` tables
- Update customer lookup logic to handle both SMS and Discord

### Conversation Flow Adaptations

#### Customer Identification
```python
# SMS: Use phone number
customer_id = get_customer_by_phone(phone_number)

# Discord: Use Discord user ID
customer_id = get_customer_by_discord_id(discord_user.id, discord_user.name)
```

#### Response Formatting
- **SMS**: Plain text, 160 char limit, multiple messages
- **Discord**: Rich embeds, longer messages, reactions, buttons
- Create formatter layer to adapt Marty's responses

#### Purchase Flow
- SMS: Square payment links via text
- Discord: Embedded payment links, reaction-based confirmations
- Same backend payment processing

## Integration Points

### Existing Code Reuse
1. **AI Client** (`src/ai_client.py`) - No changes needed
2. **Database Models** - Add Discord fields to existing tables
3. **Conversation Logic** - Reuse with platform-specific adapters
4. **Book Search** - Hardcover API integration works as-is
5. **Payment Processing** - Square integration unchanged

### Platform-Specific Adaptations
1. **Message Splitting**: Discord allows longer messages than SMS
2. **Rich Formatting**: Discord supports embeds, buttons, reactions
3. **User Context**: Discord provides username, avatar, server context
4. **Error Handling**: Discord-specific error responses

## Database Schema Updates

### Add Discord Support to Existing Tables
```sql
-- Add Discord fields to customers table
ALTER TABLE customers ADD COLUMN discord_user_id VARCHAR(255);
ALTER TABLE customers ADD COLUMN discord_username VARCHAR(255);
ALTER TABLE customers ADD COLUMN platform VARCHAR(50) DEFAULT 'sms'; -- 'sms', 'discord', 'both'

-- Add Discord context to conversations
ALTER TABLE conversations ADD COLUMN platform VARCHAR(50) DEFAULT 'sms';
ALTER TABLE conversations ADD COLUMN discord_channel_id VARCHAR(255);
ALTER TABLE conversations ADD COLUMN discord_guild_id VARCHAR(255);
```

## Configuration

### Environment Variables
```bash
# Add to existing .env
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_GUILD_ID=your_test_server_id  # Optional: for testing
```

### Discord Bot Setup
1. Create Discord Application at https://discord.com/developers/applications
2. Create Bot user and get token
3. Set bot permissions: Send Messages, Read Message History, Use Slash Commands
4. Generate invite link and add to test server

## Testing Strategy

### Development Testing
1. **Private Discord Server**: Create test server for development
2. **Bot Commands**: Implement debug commands for testing
3. **Conversation Flow**: Test full book recommendation and purchase flow
4. **Error Handling**: Test API failures, rate limits, etc.

### User Testing
1. **Invite Beta Users**: Add friends/customers to test server
2. **A/B Test Responses**: Compare Discord vs SMS conversation quality
3. **Feedback Collection**: Use Discord reactions/surveys for feedback

## Implementation Timeline

### Phase 1: Basic Discord Integration (1-2 days)
- [ ] Set up Discord bot application and permissions
- [ ] Create basic bot client that can receive/send messages
- [ ] Integrate with existing AI client for responses
- [ ] Basic conversation state management

### Phase 2: Feature Parity (2-3 days)
- [ ] Implement full conversation history
- [ ] Add customer identification and context
- [ ] Book search and recommendation flow
- [ ] Purchase flow with Square integration

### Phase 3: Discord-Specific Features (1-2 days)
- [ ] Rich embeds for book recommendations
- [ ] Reaction-based interactions
- [ ] Slash commands for quick actions
- [ ] Server-specific configuration

### Phase 4: Testing and Polish (1-2 days)
- [ ] Comprehensive testing with beta users
- [ ] Error handling improvements
- [ ] Performance optimization
- [ ] Documentation updates

## Success Metrics

### Technical Goals
- [ ] Discord bot responds within 3 seconds
- [ ] Conversation context maintained across sessions
- [ ] Book recommendations work identically to SMS
- [ ] Purchase flow completes successfully
- [ ] No message loss or duplicate responses

### User Experience Goals
- [ ] Natural conversation flow in Discord format
- [ ] Users prefer Discord interactions over web chat
- [ ] Successful book purchases through Discord
- [ ] Positive feedback from beta testers
- [ ] Ready to scale to larger Discord communities

## Future Enhancements

### Discord-Specific Features
- **Server Integration**: Bot works in bookstore's public Discord server
- **Book Clubs**: Create channels for book discussions
- **Reading Lists**: Collaborative lists with Discord members
- **Events**: Book launch parties, author AMAs via Discord
- **Community**: Build reading community around the bot

### Multi-Platform Strategy
- **Unified Customer Profiles**: Link SMS, Discord, web accounts
- **Cross-Platform Conversations**: Continue conversations across platforms
- **Platform-Specific Features**: Leverage best of each platform
- **Analytics**: Compare engagement across platforms

## Risk Mitigation

### Technical Risks
- **Discord API Rate Limits**: Implement proper rate limiting and queuing
- **Bot Permissions**: Handle permission changes gracefully
- **Message Threading**: Discord threading different from SMS
- **Rich Formatting**: Fallback to plain text when embeds fail

### Business Risks
- **User Adoption**: Start with small test group
- **Brand Consistency**: Maintain Marty's personality across platforms
- **Support Overhead**: Don't create too many support channels
- **Data Privacy**: Handle Discord user data properly

## Deployment Strategy

### Development Environment
- Use Discord test server for development
- Environment variables for bot tokens
- Local database for testing

### Production Considerations
- Same Railway deployment as SMS service
- Environment-based Discord server configuration
- Monitoring and logging for Discord interactions
- Graceful degradation if Discord API is down

---

This plan provides a foundation for implementing Marty as a Discord bot while maintaining all existing SMS functionality. The unified approach leverages existing infrastructure and allows for seamless multi-platform support.
