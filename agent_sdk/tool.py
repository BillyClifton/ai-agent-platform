"""
Decorator for marking a method as an MCP tool.
"""
from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Optional


def tool(
    description: Optional[str] = None,
    *,
    name: Optional[str] = None,
) -> Callable:
    """
    Decorator that marks an ``async`` method on a :class:`~agent_sdk.BaseAgent`
    subclass as an exposed MCP tool.

    Example::

        class MyAgent(BaseAgent):
            @tool(description="Reverse the given text")
            async def reverse_text(self, text: str) -> str:
                return text[::-1]
    """

    def decorator(fn: Callable) -> Callable:
        tool_name = name or fn.__name__
        tool_description = description or (fn.__doc__ or "").strip()

        if not inspect.iscoroutinefunction(fn):
            raise TypeError(
                f"@tool-decorated method '{fn.__qualname__}' must be async."
            )

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await fn(*args, **kwargs)

        # Attach metadata so BaseAgent can introspect registered tools
        wrapper._is_tool = True  # type: ignore[attr-defined]
        wrapper._tool_name = tool_name  # type: ignore[attr-defined]
        wrapper._tool_description = tool_description  # type: ignore[attr-defined]
        return wrapper

    return decorator
