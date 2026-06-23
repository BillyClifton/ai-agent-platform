"""
Temporal worker entry point.

Registers workflows and activities, then polls the task queue.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Ensure the project root is on sys.path so that `gateway` is importable
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import execute_agent_activity, update_task_status_activity
from .workflows import AgentExecutionWorkflow

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    temporal_host = os.environ.get("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", "agent-tasks")

    logger.info("Connecting to Temporal at %s …", temporal_host)
    client = await Client.connect(temporal_host, namespace=temporal_namespace)
    logger.info("Connected. Starting worker on queue '%s' …", task_queue)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[AgentExecutionWorkflow],
        activities=[update_task_status_activity, execute_agent_activity],
    ):
        logger.info("Worker running. Ctrl-C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped.")
