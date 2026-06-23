from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from ..database import DBSession
from ..models import Agent
from ..schemas import AgentCreate, AgentRead, AgentUpdate

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=List[AgentRead])
async def list_agents(db: DBSession) -> List[AgentRead]:
    """Return all registered agents."""
    result = await db.execute(select(Agent).order_by(Agent.name))
    return result.scalars().all()


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(body: AgentCreate, db: DBSession) -> AgentRead:
    """Register a new agent."""
    existing = await db.execute(select(Agent).where(Agent.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent '{body.name}' already exists.",
        )
    agent = Agent(**body.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: uuid.UUID, db: DBSession) -> AgentRead:
    """Get a single agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: uuid.UUID, body: AgentUpdate, db: DBSession
) -> AgentRead:
    """Update an agent's metadata."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: uuid.UUID, db: DBSession) -> None:
    """Delete an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    await db.delete(agent)
    await db.commit()
