"""
BaseAgent – the foundation class for all agents in the platform.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, List, Optional

from .client import GatewayClient
from .tool import tool
from .types import AgentConfig, TaskResult, ToolDefinition

logger = logging.getLogger(__name__)


class AgentMeta(type):
    """Metaclass that collects @tool-decorated methods into ``_tools``."""

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> "AgentMeta":
        tools: Dict[str, Any] = {}
        for key, value in namespace.items():
            if callable(value) and getattr(value, "_is_tool", False):
                tools[value._tool_name] = value
        # Also inherit tools from base classes
        for base in bases:
            tools.update(getattr(base, "_tools", {}))
        namespace["_tools"] = tools
        return super().__new__(mcs, name, bases, namespace)


class BaseAgent(metaclass=AgentMeta):
    """
    Base class for all AI agents.

    Subclass it, annotate async methods with :func:`~agent_sdk.tool`, then
    call :meth:`register` to publish the agent to the gateway.

    Example::

        class ResearchAgent(BaseAgent):
            name = "my-research-agent"
            description = "Researches topics and produces summaries."

            @tool(description="Search the web for a query")
            async def web_search(self, query: str) -> str:
                ...  # integrate with a real search API
                return f"Results for: {query}"

        async def main():
            agent = ResearchAgent(gateway_url="http://localhost:8000")
            await agent.register()
    """

    # Subclasses must define these
    name: str = "unnamed-agent"
    description: str = ""
    model: str = "gpt-4o"
    max_steps: int = 10

    _tools: Dict[str, Any] = {}

    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url
        self._client: Optional[GatewayClient] = None

    # ─── Tool introspection ──────────────────────────────────────────────────

    def list_tools(self) -> List[ToolDefinition]:
        """Return metadata for all registered tools."""
        definitions = []
        for tool_name, fn in self._tools.items():
            sig = inspect.signature(fn)
            params = {
                k: str(v.annotation)
                for k, v in sig.parameters.items()
                if k != "self"
            }
            definitions.append(
                ToolDefinition(
                    name=tool_name,
                    description=fn._tool_description,
                    parameters=params,
                )
            )
        return definitions

    async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Invoke a registered tool by name."""
        fn = self._tools.get(tool_name)
        if fn is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await fn(self, **kwargs)

    # ─── Gateway integration ─────────────────────────────────────────────────

    def _build_config(self) -> AgentConfig:
        return AgentConfig(
            name=self.name,
            description=self.description,
            model=self.model,
            max_steps=self.max_steps,
            tools=[td.name for td in self.list_tools()],
        )

    async def register(self) -> Dict[str, Any]:
        """Register (or update) this agent in the gateway."""
        async with GatewayClient(self.gateway_url) as client:
            try:
                response = await client.register_agent(self._build_config())
                logger.info("Agent '%s' registered: %s", self.name, response["id"])
                return response
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to register agent '%s': %s", self.name, exc)
                raise

    async def run_task(self, input_text: str, *, wait: bool = True) -> TaskResult:
        """Submit a task via the gateway and optionally wait for completion."""
        async with GatewayClient(self.gateway_url) as client:
            task_data = await client.run_agent(self.name, input_text)
            task_id = task_data["id"]
            if not wait:
                return TaskResult(task_id=task_id, status=task_data["status"])
            return await client.wait_for_task(task_id)
