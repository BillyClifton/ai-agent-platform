"""
AI Agent Platform – Python SDK

Usage::

    from agent_sdk import BaseAgent, tool

    class MyAgent(BaseAgent):
        name = "my-agent"
        description = "Does something useful"

        @tool(description="Process some text")
        async def process(self, text: str) -> str:
            return text.upper()


    if __name__ == "__main__":
        import asyncio
        agent = MyAgent(gateway_url="http://localhost:8000")
        asyncio.run(agent.serve())
"""
from .agent import BaseAgent
from .tool import tool
from .client import GatewayClient
from .types import AgentConfig, TaskResult, ToolDefinition

__version__ = "1.0.0"
__all__ = [
    "BaseAgent",
    "tool",
    "GatewayClient",
    "AgentConfig",
    "TaskResult",
    "ToolDefinition",
]
