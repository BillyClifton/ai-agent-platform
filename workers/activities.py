"""
Temporal activity implementations.

Activities are the building-blocks executed by Temporal workers.
They can interact with external services (database, APIs, tools).
"""
from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from temporalio import activity


# ─── Input / output dataclasses ──────────────────────────────────────────────

@dataclass
class UpdateTaskStatusInput:
    task_id: str
    status: str
    output_text: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ExecuteAgentInput:
    task_id: str
    agent_name: str
    input_text: str


# ─── Database helper ─────────────────────────────────────────────────────────

async def _get_db_session():
    """Return an async SQLAlchemy session from the worker's engine."""
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    import os

    db_url = os.environ.get(
        "DATABASE_URL",
        "******localhost:5432/aiagentplatform",
    )

    engine = create_async_engine(db_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return factory()


# ─── Activities ──────────────────────────────────────────────────────────────

@activity.defn
async def update_task_status_activity(inp: UpdateTaskStatusInput) -> None:
    """Persist task status changes to the database."""
    from sqlalchemy import select

    logger = activity.logger

    try:
        tid = uuid.UUID(inp.task_id)
    except ValueError:
        logger.error("Invalid task_id: %s", inp.task_id)
        return

    async with await _get_db_session() as session:
        # Import here to avoid top-level circular deps
        from gateway.models import Task  # type: ignore[import]

        result = await session.execute(select(Task).where(Task.id == tid))
        task = result.scalar_one_or_none()
        if task is None:
            logger.warning("Task %s not found – skipping status update.", inp.task_id)
            return

        task.status = inp.status
        if inp.output_text is not None:
            task.output_text = inp.output_text
        if inp.error_message is not None:
            task.error_message = inp.error_message
        if inp.status in ("completed", "failed", "cancelled"):
            task.completed_at = datetime.now(tz=timezone.utc)

        await session.commit()
        logger.info("Task %s → %s", inp.task_id, inp.status)


@activity.defn
async def execute_agent_activity(inp: ExecuteAgentInput) -> str:
    """
    Execute an AI agent task.

    This demo implementation simulates an agent that:
      1. Selects relevant built-in tools based on the agent name.
      2. Calls each tool and records the result.
      3. Synthesises a final answer.

    In production, replace the tool stubs with real LLM calls or SDK agent loops.
    """
    from sqlalchemy import select

    logger = activity.logger
    logger.info("Executing agent '%s' for task %s", inp.agent_name, inp.task_id)

    tid = uuid.UUID(inp.task_id)

    # Simulate agent execution
    tool_results: list[Dict[str, Any]] = []

    if inp.agent_name == "research-agent":
        tool_results = await _run_research_tools(inp.input_text)
    elif inp.agent_name == "code-agent":
        tool_results = await _run_code_tools(inp.input_text)
    elif inp.agent_name == "data-agent":
        tool_results = await _run_data_tools(inp.input_text)
    else:
        tool_results = await _run_generic_tools(inp.input_text)

    # Persist tool calls
    async with await _get_db_session() as session:
        from gateway.models import ToolCall  # type: ignore[import]

        for tc in tool_results:
            session.add(
                ToolCall(
                    task_id=tid,
                    tool_name=tc["tool"],
                    arguments=tc.get("arguments", {}),
                    result={"output": tc.get("output", "")},
                    duration_ms=tc.get("duration_ms", 0),
                )
            )
        await session.commit()

    # Build final answer
    output = _synthesise(inp.agent_name, inp.input_text, tool_results)
    logger.info("Task %s completed: %d chars", inp.task_id, len(output))
    return output


# ─── Simulated tool implementations ──────────────────────────────────────────

async def _run_research_tools(query: str) -> list[Dict[str, Any]]:
    results = []

    t0 = time.time()
    await asyncio.sleep(0.3)
    results.append(
        {
            "tool": "web_search",
            "arguments": {"query": query},
            "output": (
                f"Found 5 relevant articles about '{query}'. "
                "Top results cover history, recent developments, and key concepts."
            ),
            "duration_ms": int((time.time() - t0) * 1000),
        }
    )

    t0 = time.time()
    await asyncio.sleep(0.2)
    results.append(
        {
            "tool": "summarise",
            "arguments": {"text": results[0]["output"]},
            "output": (
                f"Summary: '{query}' is a multifaceted topic with broad applications. "
                "Key themes include innovation, collaboration, and measurable impact."
            ),
            "duration_ms": int((time.time() - t0) * 1000),
        }
    )
    return results


async def _run_code_tools(prompt: str) -> list[Dict[str, Any]]:
    results = []

    t0 = time.time()
    await asyncio.sleep(0.2)
    # Generate a tiny illustrative snippet
    snippet = (
        "# Generated snippet\n"
        "def solution(data):\n"
        "    \"\"\"Processes data as requested.\"\"\"\n"
        "    result = [item for item in data if item]\n"
        "    return sorted(result)\n"
    )
    results.append(
        {
            "tool": "execute_code",
            "arguments": {"language": "python", "prompt": prompt},
            "output": snippet,
            "duration_ms": int((time.time() - t0) * 1000),
        }
    )

    t0 = time.time()
    await asyncio.sleep(0.1)
    results.append(
        {
            "tool": "lint_code",
            "arguments": {"code": snippet},
            "output": "No issues found. Code follows PEP 8.",
            "duration_ms": int((time.time() - t0) * 1000),
        }
    )
    return results


async def _run_data_tools(query: str) -> list[Dict[str, Any]]:
    results = []

    t0 = time.time()
    await asyncio.sleep(0.3)
    sample_stats = {
        "rows": random.randint(100, 10000),
        "columns": random.randint(3, 20),
        "missing_values": random.randint(0, 50),
        "numeric_columns": random.randint(2, 10),
    }
    results.append(
        {
            "tool": "analyse_data",
            "arguments": {"query": query},
            "output": json.dumps(sample_stats),
            "duration_ms": int((time.time() - t0) * 1000),
        }
    )

    t0 = time.time()
    await asyncio.sleep(0.1)
    results.append(
        {
            "tool": "plot_chart",
            "arguments": {"type": "bar", "data": sample_stats},
            "output": "Chart generated: bar chart of dataset overview.",
            "duration_ms": int((time.time() - t0) * 1000),
        }
    )
    return results


async def _run_generic_tools(query: str) -> list[Dict[str, Any]]:
    await asyncio.sleep(0.2)
    return [
        {
            "tool": "generic_process",
            "arguments": {"input": query},
            "output": f"Processed: {query[:100]}",
            "duration_ms": 200,
        }
    ]


def _synthesise(
    agent_name: str, input_text: str, tool_results: list[Dict[str, Any]]
) -> str:
    tool_summaries = "\n".join(
        f"• [{r['tool']}] {r['output']}" for r in tool_results
    )
    return (
        f"# Agent: {agent_name}\n\n"
        f"**Task:** {input_text}\n\n"
        f"## Tool Results\n{tool_summaries}\n\n"
        f"## Conclusion\n"
        f"The agent successfully processed your request using {len(tool_results)} "
        f"tool(s). The analysis is complete and the results are summarised above."
    )
