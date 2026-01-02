# -*- coding: utf-8 -*-
"""Dynamic DAG builder for non-linear workflows (Section II.2)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from ..aa import CandidateRanking, Requirement


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskNode:
    """A node in the task graph representing a single requirement.

    Supports both single-agent and multi-agent collaborative execution.
    For collaborative tasks, multiple agents work in parallel with MsgHub
    communication, and their PRs are merged by size (largest first).

    Attributes:
        node_id (`str`):
            Unique identifier for the task (e.g., "REQ-001").
        requirement (`Requirement`):
            The requirement to be fulfilled.
        assigned_agent_ids (`list[str]`):
            List of agent IDs assigned to this task. For collaborative tasks,
            multiple agents work in parallel.
        status (`TaskStatus`):
            Current execution status.
        dependencies (`set[str]`):
            Set of node_ids that must complete before this task.
        metadata (`dict[str, str]`):
            Additional metadata (decision source, rationale, etc.).
    """

    node_id: str
    requirement: Requirement
    assigned_agent_ids: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    dependencies: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)

    # Backward compatibility: single agent assignment
    _assigned_agent_id: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Handle backward compatibility for assigned_agent_id."""
        # If _assigned_agent_id was set (old-style), migrate to list
        if self._assigned_agent_id and not self.assigned_agent_ids:
            self.assigned_agent_ids = [self._assigned_agent_id]
            self._assigned_agent_id = None

    @property
    def assigned_agent_id(self) -> str | None:
        """Get the primary assigned agent (backward compatible).

        Returns:
            `str | None`: First agent ID or None if no agents assigned.
        """
        return self.assigned_agent_ids[0] if self.assigned_agent_ids else None

    @assigned_agent_id.setter
    def assigned_agent_id(self, value: str | None) -> None:
        """Set the primary assigned agent (backward compatible).

        Args:
            value (`str | None`): Agent ID to assign.
        """
        if value:
            if not self.assigned_agent_ids:
                self.assigned_agent_ids = [value]
            else:
                self.assigned_agent_ids[0] = value
        else:
            self.assigned_agent_ids = []

    @property
    def is_collaborative(self) -> bool:
        """Check if this task requires multi-agent collaboration.

        Returns:
            `bool`: True if multiple agents are assigned.
        """
        return len(self.assigned_agent_ids) > 1

    def is_ready(self, completed_nodes: set[str]) -> bool:
        """Check if this task is ready to execute.

        Args:
            completed_nodes (`set[str]`): Set of completed node IDs.

        Returns:
            `bool`: True if all dependencies are met and status is PENDING.
        """
        return self.dependencies.issubset(completed_nodes) and self.status == TaskStatus.PENDING

    def add_agent(self, agent_id: str) -> None:
        """Add an agent to this task for collaborative execution.

        Args:
            agent_id (`str`): Agent ID to add.
        """
        if agent_id not in self.assigned_agent_ids:
            self.assigned_agent_ids.append(agent_id)


class TaskGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode) -> None:
        if node.node_id in self._nodes:
            raise ValueError(f"Duplicated node_id {node.node_id}")
        self._nodes[node.node_id] = node

    def add_dependency(self, node_id: str, dependency_id: str) -> None:
        if node_id not in self._nodes or dependency_id not in self._nodes:
            raise KeyError("Both node and dependency must exist")
        self._nodes[node_id].dependencies.add(dependency_id)

    def nodes(self) -> list[TaskNode]:
        return list(self._nodes.values())

    def get(self, node_id: str) -> TaskNode:
        return self._nodes[node_id]

    def ready_nodes(self) -> list[TaskNode]:
        completed = {
            node_id
            for node_id, node in self._nodes.items()
            if node.status == TaskStatus.COMPLETED
        }
        ready = [node for node in self._nodes.values() if node.is_ready(completed)]
        for node in ready:
            node.status = TaskStatus.READY
        return ready

    def mark_running(self, node_id: str) -> None:
        self._nodes[node_id].status = TaskStatus.RUNNING

    def mark_completed(self, node_id: str) -> None:
        self._nodes[node_id].status = TaskStatus.COMPLETED

    def mark_failed(self, node_id: str, *, reason: str | None = None) -> None:
        node = self._nodes[node_id]
        node.status = TaskStatus.FAILED
        if reason:
            node.metadata["failure_reason"] = reason

    def topological_order(self) -> list[str]:
        indegree = {node_id: 0 for node_id in self._nodes}
        for node in self._nodes.values():
            for dep in node.dependencies:
                indegree[node.node_id] += 1
        queue = deque([node_id for node_id, val in indegree.items() if val == 0])
        order: list[str] = []
        while queue:
            current = queue.popleft()
            order.append(current)
            for node in self._nodes.values():
                if current in node.dependencies:
                    indegree[node.node_id] -= 1
                    if indegree[node.node_id] == 0:
                        queue.append(node.node_id)
        if len(order) != len(self._nodes):
            raise ValueError("Graph contains cycles")
        return order


class TaskGraphBuilder:
    """Utility that assigns agents to nodes based on AA rankings.

    Supports both single-agent (backward compatible) and multi-agent team assignments.
    When team_selections is provided, uses the team composition from LLM analysis.
    """

    def __init__(
        self,
        *,
        fallback_agent_id: str | None = None,
        use_type_routing: bool = True,
    ) -> None:
        self.fallback_agent_id = fallback_agent_id
        self.use_type_routing = use_type_routing

    def build(
        self,
        requirements: dict[str, Requirement],
        rankings: dict[str, CandidateRanking],
        edges: Iterable[tuple[str, str]] | None = None,
        team_selections: dict | None = None,
    ) -> TaskGraph:
        """Build task graph with agent assignments.

        Args:
            requirements: Map of node_id to Requirement.
            rankings: Map of node_id to CandidateRanking (backward compatible).
            edges: Dependency edges as (from_node, to_node) tuples.
            team_selections: Map of node_id to TeamSelection (multi-agent).

        Returns:
            TaskGraph with assigned agents.
        """
        graph = TaskGraph()
        team_selections = team_selections or {}

        # Import routing function if type-based routing is enabled
        route_fn = None
        if self.use_type_routing:
            try:
                from agentscope.scripts._agent_market import route_requirement_to_agent
                route_fn = route_requirement_to_agent
            except ImportError:
                pass

        for node_id, requirement in requirements.items():
            # Check if we have team selection (multi-agent mode)
            team_selection = team_selections.get(node_id)

            if team_selection and team_selection.agent_ids:
                # Multi-agent mode: use team selection
                agent_ids = team_selection.agent_ids
                primary_agent = team_selection.primary_agent_id

                # Build metadata from team selection
                role_info = []
                for assignment in team_selection.assignments:
                    role_info.append(f"{assignment.role}:{assignment.agent.agent_id}")

                metadata = {
                    "selected_agent": primary_agent or "unassigned",
                    "decision_source": "team_selection",
                    "team_roles": ", ".join(role_info),
                    "collaboration_mode": team_selection.collaboration_mode.value,
                    "team_size": str(len(agent_ids)),
                }

                # Add LLM reasoning if available
                llm_analysis = getattr(team_selection, "llm_analysis", None)
                if llm_analysis:
                    reasoning = getattr(llm_analysis, "reasoning", "") or ""
                    metadata["llm_reasoning"] = reasoning[:200]

            else:
                # Single-agent mode (backward compatible)
                candidate = rankings.get(node_id)
                agent_id = candidate.profile.agent_id if candidate else self.fallback_agent_id
                rationales = []
                combined_score = None
                decision_source = "fallback"

                if candidate:
                    rationales = candidate.requirement_fit.rationales
                    combined_score = f"{candidate.combined_score:.4f}"
                    decision_source = "ranking"

                # Apply type-based routing override if available
                if route_fn and requirement:
                    req_dict = {
                        "type": getattr(requirement, "type", "") or "",
                        "category": getattr(requirement, "category", "") or "",
                        "title": getattr(requirement, "title", "") or "",
                    }
                    routed_agent = route_fn(req_dict)
                    if routed_agent:
                        agent_id = routed_agent
                        decision_source = "type_routing"
                        rationales = [
                            f"路由规则: {req_dict.get('type') or req_dict.get('category') or 'title匹配'} -> {routed_agent}"
                        ]

                agent_ids = [agent_id] if agent_id else []
                metadata = {
                    "selected_agent": agent_id or "unassigned",
                    "decision_source": decision_source,
                    "rationale": " | ".join(rationales),
                    "combined_score": combined_score or "",
                }

            node = TaskNode(
                node_id=node_id,
                requirement=requirement,
                assigned_agent_ids=agent_ids,
                metadata=metadata,
            )
            graph.add_node(node)

        for edge in edges or []:
            graph.add_dependency(edge[1], edge[0])

        graph.topological_order()
        return graph
