from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Agent ────────────────────────────────────────────────────────────────────

class AgentBase(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class AgentRead(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


# ─── Task ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    agent_name: str
    input_text: str


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: Optional[uuid.UUID]
    workflow_id: Optional[str]
    run_id: Optional[str]
    input_text: str
    output_text: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


# ─── Tool Call ────────────────────────────────────────────────────────────────

class ToolCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: Optional[uuid.UUID]
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    duration_ms: Optional[int]
    created_at: datetime


# ─── API Responses ────────────────────────────────────────────────────────────

class TaskWithToolCalls(TaskRead):
    tool_calls: List[ToolCallRead] = []


class StatsResponse(BaseModel):
    total_agents: int
    active_agents: int
    total_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
