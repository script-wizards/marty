"""Discord thread rename tool."""

from typing import Any

from ..base import BaseTool, ToolResult


class ThreadRenameTool(BaseTool):
    """Tool to rename Discord threads."""

    @property
    def name(self) -> str:
        return "rename_thread"

    @property
    def description(self) -> str:
        return "Rename the current Discord thread to better reflect the conversation topic. Use when the conversation has developed a clear topic (like specific book recommendations, genre discussions, etc.)"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "thread_name": {
                "type": "string",
                "description": "The new thread name (max 50 chars). Use formats like 'sci-fi recs', 'discussion: book title', 'fantasy suggestions'. Keep it short and casual.",
                "maxLength": 50,
            }
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute thread rename."""
        thread_name = kwargs.get("thread_name", "").strip()

        if not thread_name:
            return ToolResult(
                success=False, data={}, error="Thread name cannot be empty"
            )

        if len(thread_name) > 50:
            return ToolResult(
                success=False,
                data={},
                error="Thread name must be 50 characters or less",
            )

        # Return the thread name for the bot to process
        return ToolResult(
            success=True,
            data={"thread_name": thread_name},
            metadata={"action": "rename_thread"},
        )
