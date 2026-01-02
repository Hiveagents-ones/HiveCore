# -*- coding: utf-8 -*-
"""TaskBoard tool for agent task management.

This module provides tools for agents to manage their own tasks,
similar to Claude Code's TodoWrite functionality.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ._response import ToolResponse
from ..message import TextBlock

if TYPE_CHECKING:
    from ..ones._modular_agent import AgentTaskBoard


# Global reference to the current agent's task board
# This is set by the agent before tool execution
_current_task_board: "AgentTaskBoard | None" = None


def set_current_task_board(task_board: "AgentTaskBoard | None") -> None:
    """Set the current agent's task board for tool access."""
    global _current_task_board
    _current_task_board = task_board


def get_current_task_board() -> "AgentTaskBoard | None":
    """Get the current agent's task board."""
    return _current_task_board


def task_board_write(
    tasks: list[dict[str, str]],
) -> ToolResponse:
    """Update the agent's task board with a list of tasks.

    This tool allows the agent to track its progress on complex tasks.
    Use it to plan work, track progress, and ensure all steps are completed.

    Args:
        tasks: List of task dictionaries, each containing:
            - content: Task description (what needs to be done)
            - status: One of "pending", "in_progress", "completed"

    Returns:
        ToolResponse with the updated task board summary.

    Example:
        task_board_write([
            {"content": "Analyze requirements", "status": "completed"},
            {"content": "Create component structure", "status": "in_progress"},
            {"content": "Implement styling", "status": "pending"},
            {"content": "Write tests", "status": "pending"},
        ])
    """
    task_board = get_current_task_board()
    if task_board is None:
        return ToolResponse(
            content=[TextBlock(type="text", text="[ERROR] TaskBoard not available")],
            metadata={"error": "no_task_board"},
        )

    # Clear existing tasks and create new ones based on input
    # Find or create the main task
    if not task_board._current_task:
        task_board.create_task("Agent Task Execution")

    # Update subtasks
    current = task_board._current_task
    if current:
        # Clear existing subtasks
        current.subtasks = []

        # Add new subtasks
        for task_data in tasks:
            content = task_data.get("content", "")
            status = task_data.get("status", "pending")
            if content:
                subtask = task_board.add_subtask(content)
                if subtask:
                    subtask.status = status

    # Generate summary
    summary = task_board.get_status_summary()

    return ToolResponse(
        content=[TextBlock(type="text", text=f"Task board updated:\n{summary}")],
        metadata={
            "task_count": len(tasks),
            "completed": sum(1 for t in tasks if t.get("status") == "completed"),
            "in_progress": sum(1 for t in tasks if t.get("status") == "in_progress"),
            "pending": sum(1 for t in tasks if t.get("status") == "pending"),
        },
    )


def task_board_read() -> ToolResponse:
    """Read the current state of the agent's task board.

    Returns:
        ToolResponse with the current task board summary.
    """
    task_board = get_current_task_board()
    if task_board is None:
        return ToolResponse(
            content=[TextBlock(type="text", text="[ERROR] TaskBoard not available")],
            metadata={"error": "no_task_board"},
        )

    summary = task_board.get_status_summary()

    return ToolResponse(
        content=[TextBlock(type="text", text=summary)],
        metadata={"has_current_task": task_board._current_task is not None},
    )


# JSON schemas for tool registration
TASK_BOARD_WRITE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "task_board_write",
        "description": """Update your task board to track progress on complex tasks.

Use this tool to:
1. Plan multi-step tasks before starting
2. Track which steps are completed
3. Show progress to the user
4. Ensure no steps are forgotten

Each task should have:
- content: What needs to be done (imperative form, e.g., "Create component")
- status: "pending", "in_progress", or "completed"

Best practices:
- Break complex tasks into 3-7 subtasks
- Update status as you complete each step
- Mark current task as "in_progress"
- Only one task should be "in_progress" at a time""",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "description": "List of tasks to track",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Task description (what needs to be done)",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "Task status",
                            },
                        },
                        "required": ["content", "status"],
                    },
                },
            },
            "required": ["tasks"],
        },
    },
}

TASK_BOARD_READ_SCHEMA = {
    "type": "function",
    "function": {
        "name": "task_board_read",
        "description": "Read the current state of your task board to see progress.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}
