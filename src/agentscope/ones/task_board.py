# -*- coding: utf-8 -*-
"""Task board implementations for project and agent level task tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .intent import AcceptanceCriteria


class TaskItemStatus(Enum):
    """Status of a single task item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskItem:
    """A single task item that can be tracked."""

    task_id: str
    description: str
    status: TaskItemStatus = TaskItemStatus.PENDING
    assigned_to: str | None = None
    parent_task_id: str | None = None  # For hierarchical tasks
    output: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = field(default_factory=dict)

    def start(self) -> None:
        """Mark task as in progress."""
        self.status = TaskItemStatus.IN_PROGRESS
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, output: str | None = None) -> None:
        """Mark task as completed."""
        self.status = TaskItemStatus.COMPLETED
        self.output = output
        self.updated_at = datetime.now(timezone.utc)

    def fail(self, error: str | None = None) -> None:
        """Mark task as failed."""
        self.status = TaskItemStatus.FAILED
        self.error = error
        self.updated_at = datetime.now(timezone.utc)

    def block(self, reason: str | None = None) -> None:
        """Mark task as blocked."""
        self.status = TaskItemStatus.BLOCKED
        self.error = reason
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class AgentTaskBoard:
    """Task board for a single agent.

    Each agent maintains its own task board that tracks:
    - Current tasks assigned to this agent
    - Task status and outputs
    - Subtasks created by this agent
    """

    agent_id: str
    agent_name: str
    role: str = ""
    tasks: dict[str, TaskItem] = field(default_factory=dict)
    current_task_id: str | None = None
    status: str = "idle"  # idle, working, blocked, completed

    def add_task(self, task: TaskItem) -> None:
        """Add a task to this agent's board."""
        task.assigned_to = self.agent_id
        self.tasks[task.task_id] = task

    def start_task(self, task_id: str) -> None:
        """Start working on a task."""
        if task_id in self.tasks:
            self.tasks[task_id].start()
            self.current_task_id = task_id
            self.status = "working"

    def complete_task(self, task_id: str, output: str | None = None) -> None:
        """Mark a task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id].complete(output)
            if self.current_task_id == task_id:
                self.current_task_id = None
                # Check if there are more pending tasks
                pending = self.get_pending_tasks()
                self.status = "idle" if not pending else "working"

    def fail_task(self, task_id: str, error: str | None = None) -> None:
        """Mark a task as failed."""
        if task_id in self.tasks:
            self.tasks[task_id].fail(error)
            if self.current_task_id == task_id:
                self.current_task_id = None
                self.status = "blocked"

    def get_pending_tasks(self) -> list[TaskItem]:
        """Get all pending tasks."""
        return [
            t for t in self.tasks.values()
            if t.status == TaskItemStatus.PENDING
        ]

    def get_completed_tasks(self) -> list[TaskItem]:
        """Get all completed tasks."""
        return [
            t for t in self.tasks.values()
            if t.status == TaskItemStatus.COMPLETED
        ]

    def completion_rate(self) -> float:
        """Calculate task completion rate."""
        if not self.tasks:
            return 0.0
        completed = len(self.get_completed_tasks())
        return completed / len(self.tasks)

    def to_summary(self) -> str:
        """Generate a summary of this agent's task board."""
        lines = [f"## {self.agent_name} ({self.role})"]
        lines.append(f"状态: {self.status}")
        lines.append(f"任务完成率: {self.completion_rate():.0%}")
        lines.append("")

        if self.current_task_id and self.current_task_id in self.tasks:
            current = self.tasks[self.current_task_id]
            lines.append(f"当前任务: {current.description}")
            lines.append("")

        pending = self.get_pending_tasks()
        if pending:
            lines.append("待处理任务:")
            for t in pending[:5]:  # Show max 5
                lines.append(f"  - {t.description}")

        completed = self.get_completed_tasks()
        if completed:
            lines.append("已完成任务:")
            for t in completed[-3:]:  # Show last 3
                lines.append(f"  ✓ {t.description}")

        return "\n".join(lines)


@dataclass
class ProjectTaskBoard:
    """Project-level task board that tracks overall project progress.

    This is the "master" task board that contains:
    - Acceptance criteria from the initial requirement
    - Global tasks derived from the acceptance criteria
    - References to agent task boards
    - Overall completion metrics
    """

    project_id: str
    acceptance_criteria: "AcceptanceCriteria | None" = None
    global_tasks: dict[str, TaskItem] = field(default_factory=dict)
    agent_boards: dict[str, AgentTaskBoard] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def set_acceptance_criteria(self, criteria: "AcceptanceCriteria") -> None:
        """Set the acceptance criteria for this project."""
        self.acceptance_criteria = criteria
        self.updated_at = datetime.now(timezone.utc)

    def add_global_task(self, task: TaskItem) -> None:
        """Add a global task to the project board."""
        self.global_tasks[task.task_id] = task
        self.updated_at = datetime.now(timezone.utc)

    def get_or_create_agent_board(
        self,
        agent_id: str,
        agent_name: str = "",
        role: str = "",
    ) -> AgentTaskBoard:
        """Get or create an agent's task board."""
        if agent_id not in self.agent_boards:
            self.agent_boards[agent_id] = AgentTaskBoard(
                agent_id=agent_id,
                agent_name=agent_name or agent_id,
                role=role,
            )
        return self.agent_boards[agent_id]

    def assign_task_to_agent(
        self,
        task: TaskItem,
        agent_id: str,
        agent_name: str = "",
        role: str = "",
    ) -> None:
        """Assign a task to an agent, creating their board if needed."""
        # Add to global tasks
        self.add_global_task(task)
        # Add to agent's board
        board = self.get_or_create_agent_board(agent_id, agent_name, role)
        board.add_task(task)

    def sync_from_task_graph(self, task_status: dict[str, str]) -> None:
        """Sync task statuses from TaskGraph execution results.

        Args:
            task_status: Dict of node_id -> status string from TaskGraph
        """
        status_map = {
            "pending": TaskItemStatus.PENDING,
            "running": TaskItemStatus.IN_PROGRESS,
            "completed": TaskItemStatus.COMPLETED,
            "failed": TaskItemStatus.FAILED,
            "blocked": TaskItemStatus.BLOCKED,
        }

        for task_id, status_str in task_status.items():
            if task_id in self.global_tasks:
                new_status = status_map.get(status_str, TaskItemStatus.PENDING)
                self.global_tasks[task_id].status = new_status
                self.global_tasks[task_id].updated_at = datetime.now(timezone.utc)

        self.updated_at = datetime.now(timezone.utc)

    def overall_completion_rate(self) -> float:
        """Calculate overall project completion rate."""
        if not self.global_tasks:
            return 0.0
        completed = sum(
            1 for t in self.global_tasks.values()
            if t.status == TaskItemStatus.COMPLETED
        )
        return completed / len(self.global_tasks)

    def get_acceptance_progress(self) -> dict[str, bool]:
        """Get progress against acceptance criteria."""
        if not self.acceptance_criteria:
            return {}

        # Map acceptance criteria metrics to completion status
        progress = {}
        criteria = self.acceptance_criteria

        # Check completion rate against metrics if defined
        completion_rate = self.overall_completion_rate()

        for metric_name, threshold in criteria.metrics.items():
            if metric_name == "quality" or metric_name == "completion":
                progress[metric_name] = completion_rate >= threshold
            else:
                # For other metrics, assume met unless we track them
                progress[metric_name] = True

        # Default quality check
        if "quality" not in progress and "completion" not in progress:
            progress["completion"] = completion_rate >= 0.9

        return progress

    def is_accepted(self) -> bool:
        """Check if all acceptance criteria are met."""
        progress = self.get_acceptance_progress()
        return all(progress.values()) if progress else False

    def to_summary(self) -> str:
        """Generate a comprehensive summary of the project task board."""
        lines = [f"# 项目任务板: {self.project_id}"]
        lines.append("")

        # Acceptance criteria
        if self.acceptance_criteria:
            lines.append("## 验收标准")
            lines.append(f"- 描述: {self.acceptance_criteria.description}")
            for metric, value in self.acceptance_criteria.metrics.items():
                lines.append(f"- {metric}: {value}")
            lines.append("")

        # Overall progress
        lines.append("## 总体进度")
        lines.append(f"- 完成率: {self.overall_completion_rate():.0%}")
        lines.append(f"- 全局任务数: {len(self.global_tasks)}")
        lines.append(f"- 参与 Agent 数: {len(self.agent_boards)}")
        lines.append("")

        # Acceptance progress
        progress = self.get_acceptance_progress()
        if progress:
            lines.append("## 验收进度")
            for criterion, met in progress.items():
                status = "✓" if met else "✗"
                lines.append(f"  {status} {criterion}")
            lines.append("")

        # Agent summaries
        if self.agent_boards:
            lines.append("## Agent 任务板")
            for agent_id, board in self.agent_boards.items():
                lines.append("")
                lines.append(board.to_summary())

        return "\n".join(lines)


@dataclass
class ProjectContext:
    """Unified project context that combines all project-level components.

    This is the main entry point for accessing project resources:
    - memory_pool: Stores execution history and agent outputs
    - knowledge_base: ResourceLibrary for tools, docs, APIs
    - task_board: ProjectTaskBoard for tracking overall progress
    """

    project_id: str
    task_board: ProjectTaskBoard = field(default_factory=lambda: ProjectTaskBoard(""))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.task_board.project_id:
            self.task_board.project_id = self.project_id
