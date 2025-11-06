# -*- coding: utf-8 -*-
"""Dynamic DAG builder for non-linear workflows (Section II.2)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from ..aa import CandidateRanking, RoleRequirement


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskNode:
    node_id: str
    requirement: RoleRequirement
    assigned_agent_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    dependencies: set[str] = field(default_factory=set)
    metadata: dict[str, str] = field(default_factory=dict)

    def is_ready(self, completed_nodes: set[str]) -> bool:
        return self.dependencies.issubset(completed_nodes) and self.status == TaskStatus.PENDING


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
    """Utility that assigns agents to nodes based on AA rankings."""

    def __init__(self, *, fallback_agent_id: str | None = None) -> None:
        self.fallback_agent_id = fallback_agent_id

    def build(
        self,
        requirements: dict[str, RoleRequirement],
        rankings: dict[str, CandidateRanking],
        edges: Iterable[tuple[str, str]] | None = None,
    ) -> TaskGraph:
        graph = TaskGraph()
        for node_id, requirement in requirements.items():
            candidate = rankings.get(node_id)
            agent_id = candidate.profile.agent_id if candidate else self.fallback_agent_id
            rationales = []
            combined_score = None
            if candidate:
                rationales = candidate.requirement_fit.rationales
                combined_score = f"{candidate.combined_score:.4f}"
            node = TaskNode(
                node_id=node_id,
                requirement=requirement,
                assigned_agent_id=agent_id,
                metadata={
                    "selected_agent": agent_id or "unassigned",
                    "decision_source": "user_or_system" if candidate else "fallback",
                    "rationale": " | ".join(rationales),
                    "combined_score": combined_score or "",
                },
            )
            graph.add_node(node)

        for edge in edges or []:
            graph.add_dependency(edge[1], edge[0])

        graph.topological_order()
        return graph
