# -*- coding: utf-8 -*-
"""Agent execution timeline tracker."""
from __future__ import annotations

from datetime import datetime
from typing import Dict
import uuid

from ._hub import ObservabilityHub
from ._types import AgentExecution, TimelineEvent


class TimelineTracker:
    """Tracker for agent execution timelines.

    This class tracks the start and end times of agent executions,
    enabling visualization of parallel execution and performance analysis.

    Usage::

        tracker = TimelineTracker()

        # Start tracking an execution
        exec_id = tracker.start_execution(
            agent_id="agent-1",
            agent_name="MyAgent",
            node_id="task-1",
            project_id="proj-1",
            round_index=1,
        )

        # ... agent does work ...

        # End tracking
        execution = tracker.end_execution(
            execution_id=exec_id,
            content="Task completed successfully",
            success=True,
        )
    """

    def __init__(self, hub: ObservabilityHub | None = None) -> None:
        """Initialize the tracker.

        Args:
            hub (`ObservabilityHub | None`, optional):
                The observability hub to store records.
                Defaults to the singleton instance.
        """
        self.hub = hub or ObservabilityHub()
        self._active_executions: Dict[str, AgentExecution] = {}

    def start_execution(
        self,
        agent_id: str,
        agent_name: str,
        node_id: str,
        project_id: str | None,
        round_index: int,
    ) -> str:
        """Start tracking an agent execution.

        Args:
            agent_id (`str`):
                The agent ID.
            agent_name (`str`):
                Human-readable agent name.
            node_id (`str`):
                The task node ID.
            project_id (`str | None`):
                The project ID.
            round_index (`int`):
                The execution round number.

        Returns:
            `str`:
                The execution ID for later reference.
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()

        execution = AgentExecution(
            execution_id=execution_id,
            agent_id=agent_id,
            agent_name=agent_name,
            node_id=node_id,
            project_id=project_id,
            round_index=round_index,
            start_time=start_time,
            content="",
            success=False,
        )

        self._active_executions[execution_id] = execution

        # Record timeline event
        event = TimelineEvent(
            timestamp=start_time,
            event_type="agent_start",
            project_id=project_id,
            agent_id=agent_id,
            node_id=node_id,
            metadata={
                "execution_id": execution_id,
                "agent_name": agent_name,
                "round": round_index,
            },
        )
        self.hub.record_timeline_event(event)

        return execution_id

    def end_execution(
        self,
        execution_id: str,
        content: str,
        success: bool,
        error_message: str | None = None,
    ) -> AgentExecution:
        """End tracking an agent execution.

        Args:
            execution_id (`str`):
                The execution ID from start_execution.
            content (`str`):
                The execution output content.
            success (`bool`):
                Whether execution succeeded.
            error_message (`str | None`, optional):
                Error message if failed.

        Returns:
            `AgentExecution`:
                The completed execution record.

        Raises:
            KeyError:
                If execution_id is not found in active executions.
        """
        if execution_id not in self._active_executions:
            raise KeyError(
                f"Execution {execution_id} not found in active executions"
            )

        execution = self._active_executions.pop(execution_id)
        end_time = datetime.now()

        execution.end_time = end_time
        execution.duration_ms = (
            end_time - execution.start_time
        ).total_seconds() * 1000
        execution.content = content
        execution.success = success
        execution.error_message = error_message

        self.hub.record_execution(execution)

        # Record timeline event
        event = TimelineEvent(
            timestamp=end_time,
            event_type="agent_end",
            project_id=execution.project_id,
            agent_id=execution.agent_id,
            node_id=execution.node_id,
            metadata={
                "execution_id": execution_id,
                "success": success,
                "duration_ms": execution.duration_ms,
                "error": error_message,
            },
        )
        self.hub.record_timeline_event(event)

        return execution

    def update_llm_usage(
        self,
        execution_id: str,
        tokens: int,
        cost_usd: float,
    ) -> None:
        """Update LLM usage for an active execution.

        Args:
            execution_id (`str`):
                The execution ID.
            tokens (`int`):
                Number of tokens used.
            cost_usd (`float`):
                Cost in USD.
        """
        if execution_id in self._active_executions:
            execution = self._active_executions[execution_id]
            execution.llm_calls += 1
            execution.total_tokens += tokens
            execution.total_cost_usd += cost_usd

    def get_active_executions(self) -> Dict[str, AgentExecution]:
        """Get all currently active executions.

        Returns:
            `Dict[str, AgentExecution]`:
                Dictionary mapping execution_id to execution.
        """
        return dict(self._active_executions)

    def is_active(self, execution_id: str) -> bool:
        """Check if an execution is still active.

        Args:
            execution_id (`str`):
                The execution ID to check.

        Returns:
            `bool`:
                True if the execution is still active.
        """
        return execution_id in self._active_executions
