from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..database import DBSession
from ..models import Agent, Task
from ..schemas import StatsResponse, TaskCreate, TaskRead, TaskWithToolCalls
from ..temporal_client import start_agent_workflow

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=List[TaskRead])
async def list_tasks(
    db: DBSession,
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
) -> List[TaskRead]:
    """List tasks with optional status filter."""
    query = select(Task).order_by(Task.created_at.desc()).limit(limit).offset(offset)
    if status_filter:
        query = query.where(Task.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, db: DBSession) -> TaskRead:
    """Submit a new task to the specified agent."""
    result = await db.execute(
        select(Agent).where(Agent.name == body.agent_name, Agent.status == "active")
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Active agent '{body.agent_name}' not found.",
        )

    task = Task(agent_id=agent.id, input_text=body.input_text, status="pending")
    db.add(task)
    await db.flush()

    try:
        handle = await start_agent_workflow(task.id, body.agent_name, body.input_text)
        task.workflow_id = handle.id
        task.run_id = handle.first_execution_run_id
        task.status = "running"
    except Exception as exc:  # noqa: BLE001
        task.status = "failed"
        task.error_message = str(exc)

    await db.commit()
    await db.refresh(task)
    return task


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: DBSession) -> StatsResponse:
    """Return platform-wide statistics."""
    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar_one()
    active_agents = (
        await db.execute(
            select(func.count(Agent.id)).where(Agent.status == "active")
        )
    ).scalar_one()

    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar_one()
    running = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "running")
        )
    ).scalar_one()
    completed = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "completed")
        )
    ).scalar_one()
    failed = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "failed")
        )
    ).scalar_one()

    return StatsResponse(
        total_agents=total_agents,
        active_agents=active_agents,
        total_tasks=total_tasks,
        running_tasks=running,
        completed_tasks=completed,
        failed_tasks=failed,
    )


@router.get("/{task_id}", response_model=TaskWithToolCalls)
async def get_task(task_id: uuid.UUID, db: DBSession) -> TaskWithToolCalls:
    """Get a task with all of its tool calls."""
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.tool_calls))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: uuid.UUID, db: DBSession) -> None:
    """Delete a task and its tool calls."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    await db.delete(task)
    await db.commit()
