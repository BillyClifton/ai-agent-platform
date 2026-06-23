from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import temporalio.client
from temporalio.client import Client, WorkflowHandle

from .config import get_settings

_temporal_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    global _temporal_client
    if _temporal_client is None:
        settings = get_settings()
        _temporal_client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
    return _temporal_client


async def start_agent_workflow(
    task_id: uuid.UUID,
    agent_name: str,
    input_text: str,
) -> WorkflowHandle:
    """Start an AgentExecutionWorkflow in Temporal and return the handle."""
    from workers.workflows import AgentExecutionWorkflow  # imported lazily

    settings = get_settings()
    client = await get_temporal_client()

    workflow_id = f"agent-task-{task_id}"
    handle = await client.start_workflow(
        AgentExecutionWorkflow.run,
        args=[str(task_id), agent_name, input_text],
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )
    return handle
