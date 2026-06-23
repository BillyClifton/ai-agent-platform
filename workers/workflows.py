"""
Temporal workflow definitions for the AI Agent Platform.

Workflow:
  AgentExecutionWorkflow – orchestrates the execution of a single agent task.
"""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .activities import (
        ExecuteAgentInput,
        UpdateTaskStatusInput,
        execute_agent_activity,
        update_task_status_activity,
    )


@workflow.defn
class AgentExecutionWorkflow:
    """
    Executes an AI agent task end-to-end.

    Steps:
      1. Mark the task as *running* in the database.
      2. Execute the agent logic (tools + synthesis).
      3. Mark the task as *completed* or *failed*.
    """

    @workflow.run
    async def run(
        self, task_id: str, agent_name: str, input_text: str
    ) -> str:
        retry = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
        )

        # Step 1 – mark as running
        await workflow.execute_activity(
            update_task_status_activity,
            UpdateTaskStatusInput(task_id=task_id, status="running"),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry,
        )

        # Step 2 – run agent
        try:
            result: str = await workflow.execute_activity(
                execute_agent_activity,
                ExecuteAgentInput(
                    task_id=task_id,
                    agent_name=agent_name,
                    input_text=input_text,
                ),
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
        except Exception as exc:  # noqa: BLE001
            error_message = f"{type(exc).__name__}: {exc}"
            workflow.logger.error("Agent execution failed: %s", error_message)
            await workflow.execute_activity(
                update_task_status_activity,
                UpdateTaskStatusInput(
                    task_id=task_id,
                    status="failed",
                    error_message=error_message,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry,
            )
            raise

        # Step 3 – mark as completed
        await workflow.execute_activity(
            update_task_status_activity,
            UpdateTaskStatusInput(
                task_id=task_id, status="completed", output_text=result
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry,
        )

        return result
