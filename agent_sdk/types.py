from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolDefinition:
    """Metadata about a tool exposed by an agent."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_async: bool = True


@dataclass
class AgentConfig:
    """Configuration used when registering an agent with the gateway."""

    name: str
    description: str = ""
    model: str = "gpt-4o"
    max_steps: int = 10
    tools: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "max_steps": self.max_steps,
            "tools": self.tools,
            **self.extra,
        }


@dataclass
class TaskResult:
    """Result returned after polling a submitted task."""

    task_id: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_done(self) -> bool:
        return self.status in ("completed", "failed", "cancelled")

    @property
    def succeeded(self) -> bool:
        return self.status == "completed"
