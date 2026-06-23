"""
MCP Gateway server built with FastMCP.

Exposes the following tools:
  - list_agents          List registered AI agents
  - run_agent            Submit a task to an agent
  - get_task_status      Poll the status of a running task
  - get_task_result      Retrieve the output of a completed task
  - list_tools           Enumerate all available MCP tools
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

mcp = FastMCP(
    "AI Agent Platform Gateway",
    instructions=(
        "This MCP server is the gateway to the AI Agent Platform. "
        "Use run_agent to start a new agent task, then poll with "
        "get_task_status until the task is completed, and retrieve "
        "the result with get_task_result."
    ),
)


# ---------------------------------------------------------------------------
# Helper – import DB session inside the tool functions to avoid circular imports
# ---------------------------------------------------------------------------

async def _db_session():
    from .database import _get_engine
    from sqlalchemy.ext.asyncio import AsyncSession

    _, factory = _get_engine()
    return factory()


# ---------------------------------------------------------------------------
# Tool: list_agents
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_agents() -> List[Dict[str, Any]]:
    """Return a list of all registered AI agents and their status."""
    from sqlalchemy import select
    from .models import Agent

    async with await _db_session() as session:
        result = await session.execute(select(Agent).order_by(Agent.name))
        agents = result.scalars().all()
        return [
            {
                "id": str(a.id),
                "name": a.name,
                "description": a.description,
                "status": a.status,
                "config": a.config,
            }
            for a in agents
        ]


# ---------------------------------------------------------------------------
# Tool: run_agent
# ---------------------------------------------------------------------------

@mcp.tool()
async def run_agent(agent_name: str, input_text: str) -> Dict[str, Any]:
    """
    Submit a task to the named agent and return the task id and workflow id.

    Args:
        agent_name: The name of the agent to run (see list_agents).
        input_text: The prompt / query to send to the agent.

    Returns:
        A dict containing ``task_id``, ``workflow_id``, and ``status``.
    """
    from sqlalchemy import select
    from .models import Agent, Task

    async with await _db_session() as session:
        result = await session.execute(
            select(Agent).where(Agent.name == agent_name, Agent.status == "active")
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return {"error": f"Agent '{agent_name}' not found or inactive."}

        task = Task(agent_id=agent.id, input_text=input_text, status="pending")
        session.add(task)
        await session.flush()

        # Start Temporal workflow
        try:
            from .temporal_client import start_agent_workflow

            handle = await start_agent_workflow(task.id, agent_name, input_text)
            task.workflow_id = handle.id
            task.run_id = handle.first_execution_run_id
            task.status = "running"
        except Exception as exc:  # noqa: BLE001
            error_detail = f"{type(exc).__name__}: {exc}"
            task.status = "failed"
            task.error_message = error_detail
            await session.commit()
            return {"error": f"Failed to start workflow: {error_detail}"}

        await session.commit()
        await session.refresh(task)

        return {
            "task_id": str(task.id),
            "workflow_id": task.workflow_id,
            "status": task.status,
        }


# ---------------------------------------------------------------------------
# Tool: get_task_status
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Return the current status of a task.

    Args:
        task_id: The UUID of the task returned by run_agent.
    """
    import uuid as _uuid
    from sqlalchemy import select
    from .models import Task

    try:
        tid = _uuid.UUID(task_id)
    except ValueError:
        return {"error": "Invalid task_id format."}

    async with await _db_session() as session:
        result = await session.execute(select(Task).where(Task.id == tid))
        task = result.scalar_one_or_none()
        if task is None:
            return {"error": f"Task '{task_id}' not found."}

        return {
            "task_id": str(task.id),
            "status": task.status,
            "agent_id": str(task.agent_id) if task.agent_id else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Tool: get_task_result
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_task_result(task_id: str) -> Dict[str, Any]:
    """
    Return the output of a completed task, including any tool calls made.

    Args:
        task_id: The UUID of the task.
    """
    import uuid as _uuid
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from .models import Task

    try:
        tid = _uuid.UUID(task_id)
    except ValueError:
        return {"error": "Invalid task_id format."}

    async with await _db_session() as session:
        result = await session.execute(
            select(Task)
            .options(selectinload(Task.tool_calls))
            .where(Task.id == tid)
        )
        task = result.scalar_one_or_none()
        if task is None:
            return {"error": f"Task '{task_id}' not found."}

        return {
            "task_id": str(task.id),
            "status": task.status,
            "output": task.output_text,
            "error": task.error_message,
            "tool_calls": [
                {
                    "tool": tc.tool_name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "duration_ms": tc.duration_ms,
                }
                for tc in task.tool_calls
            ],
        }


# ---------------------------------------------------------------------------
# Tool: list_tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_tools() -> List[Dict[str, str]]:
    """List all available MCP tools exposed by this gateway."""
    tools = await mcp.list_tools()
    return [
        {"name": t.name, "description": t.description or ""}
        for t in tools
    ]
