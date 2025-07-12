"""Base tool interface for all Marty tools."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standard tool result format."""

    success: bool
    data: Any
    error: str | None = None
    metadata: dict[str, Any] | None = None


class BaseTool(ABC):
    """Base class for all tools."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name for Claude."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Clear description for Claude to understand when to use this tool."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON schema for tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        return True

    async def _handle_errors(self, func, *args, **kwargs) -> ToolResult:
        """Helper method to handle errors consistently."""
        try:
            result = await func(*args, **kwargs)
            return ToolResult(success=True, data=result)
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"error_type": type(e).__name__},
            )
