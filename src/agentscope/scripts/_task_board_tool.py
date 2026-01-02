# -*- coding: utf-8 -*-
"""Task board tool for Agent tool calls.

This module provides a tool function that allows agents to update their task board
through tool calls, with observability event notifications.
"""
from __future__ import annotations

from typing import Literal

# Global task board storage (by agent_id)
_agent_task_boards: dict[str, list[dict]] = {}


TaskStatus = Literal["pending", "in_progress", "completed"]


def _notify_task_board_update(agent_id: str, tasks: list[dict]) -> None:
    """Notify observers that task board has been updated.

    Args:
        agent_id (`str`):
            The agent identifier
        tasks (`list[dict]`):
            The updated task list
    """
    try:
        from ._observability import AgentReActObserver

        observer = AgentReActObserver()
        observer.on_task_board_update(agent_id, tasks)
    except Exception:
        pass  # Observation failure should not affect main flow


def task_board_write(
    todos: list[dict],
    agent_id: str = "default",
) -> "ToolResponse":
    """Update agent's task board.

    This tool allows agents to track their progress by maintaining a task list.
    Each task has a status that can be pending, in_progress, or completed.

    Args:
        todos (`list[dict]`):
            List of tasks, each task contains:
            - content (`str`): Task description (what needs to be done)
            - status (`str`): pending | in_progress | completed
            - activeForm (`str`): Text shown when task is in progress
        agent_id (`str`, optional):
            Agent identifier. Defaults to "default".

    Returns:
        `ToolResponse`:
            Response containing the updated task board state

    Example:
        task_board_write(todos=[
            {"content": "Create data model", "status": "completed",
             "activeForm": "Creating data model"},
            {"content": "Implement API endpoints", "status": "in_progress",
             "activeForm": "Implementing API endpoints"},
            {"content": "Write tests", "status": "pending",
             "activeForm": "Writing tests"},
        ])
    """
    # Lazy import to avoid circular dependencies
    # 来源: src/agentscope/tool/_response.py:12
    from agentscope.tool import ToolResponse

    # 来源: src/agentscope/message/_message_block.py:9
    from agentscope.message import TextBlock

    # Validate and normalize tasks
    validated_tasks: list[dict] = []
    valid_statuses = {"pending", "in_progress", "completed"}

    for task in todos:
        content = task.get("content", "")
        status = task.get("status", "pending")
        active_form = task.get("activeForm", content)

        # Validate status
        if status not in valid_statuses:
            status = "pending"

        validated_tasks.append(
            {
                "content": content,
                "status": status,
                "activeForm": active_form,
            }
        )

    # Update global storage
    _agent_task_boards[agent_id] = validated_tasks

    # Notify observers
    _notify_task_board_update(agent_id, validated_tasks)

    # Build summary
    summary = _build_task_summary(validated_tasks)

    # Build response
    content_block: TextBlock = {
        "type": "text",
        "text": summary,
    }

    return ToolResponse(
        content=[content_block],
        metadata={
            "agent_id": agent_id,
            "task_count": len(validated_tasks),
            "pending": sum(1 for t in validated_tasks if t["status"] == "pending"),
            "in_progress": sum(
                1 for t in validated_tasks if t["status"] == "in_progress"
            ),
            "completed": sum(
                1 for t in validated_tasks if t["status"] == "completed"
            ),
        },
    )


def _build_task_summary(tasks: list[dict]) -> str:
    """Build a text summary of the task board.

    Args:
        tasks (`list[dict]`):
            List of task dictionaries

    Returns:
        `str`:
            Formatted task board summary
    """
    if not tasks:
        return "Task board is empty."

    status_icons = {
        "pending": "[ ]",
        "in_progress": "[>]",
        "completed": "[x]",
    }

    lines = ["Task Board Updated:"]
    lines.append("-" * 40)

    for task in tasks:
        icon = status_icons.get(task["status"], "[ ]")
        content = task["content"]
        lines.append(f"{icon} {content}")

    # Add statistics
    pending = sum(1 for t in tasks if t["status"] == "pending")
    in_progress = sum(1 for t in tasks if t["status"] == "in_progress")
    completed = sum(1 for t in tasks if t["status"] == "completed")

    lines.append("-" * 40)
    lines.append(
        f"Total: {len(tasks)} | "
        f"Pending: {pending} | "
        f"In Progress: {in_progress} | "
        f"Completed: {completed}"
    )

    return "\n".join(lines)


def get_task_board(agent_id: str = "default") -> list[dict]:
    """Get agent's current task board.

    Args:
        agent_id (`str`, optional):
            Agent identifier. Defaults to "default".

    Returns:
        `list[dict]`:
            List of tasks, each containing content, status, and activeForm
    """
    return _agent_task_boards.get(agent_id, [])


def get_task_board_summary(agent_id: str = "default") -> str:
    """Get a text summary of agent's task board.

    Args:
        agent_id (`str`, optional):
            Agent identifier. Defaults to "default".

    Returns:
        `str`:
            Formatted summary of the task board
    """
    tasks = get_task_board(agent_id)
    return _build_task_summary(tasks)


def clear_task_board(agent_id: str = "default") -> None:
    """Clear agent's task board.

    Args:
        agent_id (`str`, optional):
            Agent identifier. Defaults to "default".
    """
    if agent_id in _agent_task_boards:
        del _agent_task_boards[agent_id]
        _notify_task_board_update(agent_id, [])


def get_all_agent_ids() -> list[str]:
    """Get all agent IDs that have task boards.

    Returns:
        `list[str]`:
            List of agent IDs
    """
    return list(_agent_task_boards.keys())


__all__ = [
    "task_board_write",
    "get_task_board",
    "get_task_board_summary",
    "clear_task_board",
    "get_all_agent_ids",
]
