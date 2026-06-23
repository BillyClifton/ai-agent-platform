"""
Async HTTP client for the AI Agent Platform Gateway REST API.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from .types import AgentConfig, TaskResult


class GatewayClient:
    """
    Thin async wrapper around the Gateway REST API.

    Example::

        async with GatewayClient("http://localhost:8000") as client:
            agents = await client.list_agents()
            task = await client.run_agent("research-agent", "Explain quantum computing")
            result = await client.wait_for_task(task["id"])
            print(result.output)
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "GatewayClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "Use GatewayClient as an async context manager."
            )
        return self._client

    # ─── Agents ──────────────────────────────────────────────────────────────

    async def list_agents(self) -> List[Dict[str, Any]]:
        r = await self._http().get("/api/v1/agents")
        r.raise_for_status()
        return r.json()

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        r = await self._http().get(f"/api/v1/agents/{agent_id}")
        r.raise_for_status()
        return r.json()

    async def register_agent(self, config: AgentConfig) -> Dict[str, Any]:
        payload = {
            "name": config.name,
            "description": config.description,
            "config": config.to_dict(),
        }
        r = await self._http().post("/api/v1/agents", json=payload)
        r.raise_for_status()
        return r.json()

    # ─── Tasks ───────────────────────────────────────────────────────────────

    async def run_agent(self, agent_name: str, input_text: str) -> Dict[str, Any]:
        r = await self._http().post(
            "/api/v1/tasks",
            json={"agent_name": agent_name, "input_text": input_text},
        )
        r.raise_for_status()
        return r.json()

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        r = await self._http().get(f"/api/v1/tasks/{task_id}")
        r.raise_for_status()
        return r.json()

    async def list_tasks(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status_filter:
            params["status_filter"] = status_filter
        r = await self._http().get("/api/v1/tasks", params=params)
        r.raise_for_status()
        return r.json()

    async def get_stats(self) -> Dict[str, Any]:
        r = await self._http().get("/api/v1/tasks/stats")
        r.raise_for_status()
        return r.json()

    # ─── Polling helper ───────────────────────────────────────────────────────

    async def wait_for_task(
        self,
        task_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> TaskResult:
        """Poll until the task is done (or ``timeout`` seconds elapse)."""
        elapsed = 0.0
        while elapsed < timeout:
            data = await self.get_task(task_id)
            status = data.get("status", "unknown")
            if status in ("completed", "failed", "cancelled"):
                return TaskResult(
                    task_id=task_id,
                    status=status,
                    output=data.get("output_text"),
                    error=data.get("error_message"),
                    tool_calls=data.get("tool_calls", []),
                )
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s.")
