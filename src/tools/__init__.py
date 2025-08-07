"""Tool registry for all Marty tools."""

from typing import Any

from .base import BaseTool, ToolResult


class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self):
        self._tools: dict[str, type[BaseTool]] = {}
        self._register_core_tools()

    def _register_core_tools(self):
        """Register all core tools."""
        # Import and register tools here
        try:
            from .conversation.manager import ConversationManagerTool

            self.register(ConversationManagerTool)
        except ImportError as e:
            # Tool dependencies might not be available in all environments
            print(f"Warning: Could not register ConversationManagerTool: {e}")

        try:
            from .external.hardcover import HardcoverTool

            self.register(HardcoverTool)
        except ImportError as e:
            # Tool dependencies might not be available in all environments
            print(f"Warning: Could not register HardcoverTool: {e}")

        try:
            from .discord.thread_rename import ThreadRenameTool

            self.register(ThreadRenameTool)
        except ImportError as e:
            print(f"Warning: Could not register ThreadRenameTool: {e}")

        try:
            from .utils.query_optimizer import QueryOptimizerTool

            self.register(QueryOptimizerTool)
        except ImportError as e:
            print(f"Warning: Could not register QueryOptimizerTool: {e}")

    def register(self, tool_class: type[BaseTool]):
        """Register a tool class."""
        tool_instance = tool_class()
        self._tools[tool_instance.name] = tool_class

    def get_tool(self, name: str) -> BaseTool | None:
        """Get tool instance by name."""
        tool_class = self._tools.get(name)
        return tool_class() if tool_class else None

    def get_claude_tools(self) -> list[dict[str, Any]]:
        """Get all tools formatted for Claude API."""
        claude_tools = []
        for tool_class in self._tools.values():
            tool = tool_class()
            claude_tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": list(tool.parameters.keys()),
                    },
                }
            )
        return claude_tools

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())


# Global registry instance
tool_registry = ToolRegistry()

# Export main components
__all__ = ["BaseTool", "ToolResult", "ToolRegistry", "tool_registry"]
