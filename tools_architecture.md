# Marty Tools Architecture

## Overview
Tools are external functions that Claude can invoke to augment its capabilities. Tools can be used both programmatically and by Claude's autonomous decision-making.

## Recommended Project Structure
```
marty/
├── tools/                    # All tools organized here
│   ├── __init__.py          # Tool registry and exports
│   ├── base.py              # Base tool classes and interfaces
│   ├── book/                # Book-related tools
│   │   ├── __init__.py
│   │   ├── enricher.py      # BookEnricher tool
│   │   └── recommender.py   # Future: book recommendations
│   ├── conversation/        # Conversation tools
│   │   ├── __init__.py
│   │   ├── summarizer.py    # Future: conversation summarization
│   │   └── analyzer.py      # Future: conversation analysis
│   ├── external/            # External API tools
│   │   ├── __init__.py
│   │   ├── hardcover.py     # Hardcover API tool wrapper
│   │   └── sms.py           # SMS sending tools
│   └── utils/               # Tool utilities
│       ├── __init__.py
│       ├── validation.py    # Input validation for tools
│       └── caching.py       # Tool result caching
├── tests/
│   └── tools/               # Tool tests mirror structure
│       ├── test_book_enricher.py
│       └── ...
└── ...
```

## Tool Design Principles

### 1. Tool Interface
All tools should implement a consistent interface:
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass

@dataclass
class ToolResult:
    """Standard tool result format"""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseTool(ABC):
    """Base class for all tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name for Claude"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Clear description for Claude to understand when to use this tool"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema for tool parameters"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters"""
        return True
```

### 2. Tool Registry
Central registry for all tools:
```python
# tools/__init__.py
from typing import Dict, Type, Optional, List
from .base import BaseTool
from .book.enricher import BookEnricherTool
from .external.hardcover import HardcoverTool

class ToolRegistry:
    """Central registry for all tools"""

    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._register_core_tools()

    def _register_core_tools(self):
        """Register all core tools"""
        self.register(BookEnricherTool)
        self.register(HardcoverTool)

    def register(self, tool_class: Type[BaseTool]):
        """Register a tool class"""
        tool_instance = tool_class()
        self._tools[tool_instance.name] = tool_class

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool instance by name"""
        tool_class = self._tools.get(name)
        return tool_class() if tool_class else None

    def get_claude_tools(self) -> List[Dict[str, Any]]:
        """Get all tools formatted for Claude API"""
        claude_tools = []
        for tool_class in self._tools.values():
            tool = tool_class()
            claude_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": list(tool.parameters.keys())
                }
            })
        return claude_tools

# Global registry instance
tool_registry = ToolRegistry()
```

### 3. Tool Categories

**Book Tools:**
- `BookEnricher` - Extract and validate book mentions
- `BookRecommender` - Generate personalized recommendations
- `BookSearcher` - Search books by criteria
- `BookAnalyzer` - Analyze reading patterns

**Conversation Tools:**
- `ConversationSummarizer` - Summarize long conversations
- `ConversationAnalyzer` - Extract insights from conversations
- `ContextBuilder` - Build conversation context
- `PersonalityTracker` - Track customer personality traits

**External Tools:**
- `HardcoverAPI` - Direct Hardcover API access
- `SMSSender` - Send SMS messages
- `EmailSender` - Send emails
- `WebSearcher` - Search the web

**Utility Tools:**
- `TextProcessor` - Process and clean text
- `DataValidator` - Validate data structures
- `CacheManager` - Manage cached data
- `ImageProcessor` - Process images

## Implementation Strategy

### Phase 1: Refactor BookEnricher
1. Move `book_enricher.py` to `tools/book/enricher.py`
2. Implement `BaseTool` interface
3. Update imports across codebase
4. Update tests

### Phase 2: Create Tool Registry
1. Implement `tools/base.py`
2. Implement `tools/__init__.py` with registry
3. Register BookEnricher tool

### Phase 3: Claude Integration
1. Update AI client to use tool registry
2. Implement tool calling in chat flow
3. Test Claude's autonomous tool usage

### Phase 4: Expand Tool Ecosystem
1. Build additional tools incrementally
2. Add tool composition capabilities
3. Implement tool caching and optimization

## Tool Usage Patterns

### Programmatic Usage
```python
# Direct tool usage (current pattern)
from tools import tool_registry

book_enricher = tool_registry.get_tool("book_enricher")
result = await book_enricher.execute(
    ai_response="I recommend reading Dune by Frank Herbert",
    conversation_id="conv_123"
)
```

### Claude-Directed Usage
```python
# Claude decides when to use tools
from ai_client import generate_ai_response
from tools import tool_registry

response = await generate_ai_response(
    message="What books should I read about space?",
    tools=tool_registry.get_claude_tools()
)
```

### Hybrid Usage
```python
# Combine both approaches
async def process_chat_message(message: str, phone: str):
    # Claude generates response with tools
    ai_response = await generate_ai_response(
        message=message,
        tools=tool_registry.get_claude_tools()
    )

    # Programmatically enrich if needed
    if not ai_response.tool_calls:
        enricher = tool_registry.get_tool("book_enricher")
        enriched = await enricher.execute(
            ai_response=ai_response.content
        )
        ai_response.content = enriched.data.enriched_text

    return ai_response
```

## Benefits of This Architecture

1. **Scalability** - Easy to add new tools
2. **Consistency** - All tools follow same interface
3. **Discoverability** - Central registry makes tools findable
4. **Testability** - Clear separation of concerns
5. **Flexibility** - Support both programmatic and Claude-directed usage
6. **Maintainability** - Organized structure reduces complexity

## Future Considerations

1. **Tool Composition** - Tools that call other tools
2. **Tool Pipelines** - Sequential tool execution
3. **Tool Caching** - Cache expensive tool results
4. **Tool Monitoring** - Track tool usage and performance
5. **Tool Security** - Validate tool inputs and outputs
6. **Tool Versioning** - Support multiple tool versions
