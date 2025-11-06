# -*- coding: utf-8 -*-
"""Execution loop tying all sections together (III)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .intent import (
    AcceptanceCriteria,
    AssistantOrchestrator,
    IntentRequest,
    StrategyPlan,
)
from .kpi import KPIRecord, KPITracker
from .memory import MemoryEntry, MemoryPool, ProjectPool, ResourceLibrary
from .task_graph import TaskGraphBuilder


@dataclass
class ExecutionReport:
    project_id: str | None
    accepted: bool
    kpi: KPIRecord
    task_status: dict[str, str]
    plan: StrategyPlan


class ExecutionLoop:
    def __init__(
        self,
        *,
        project_pool: ProjectPool,
        memory_pool: MemoryPool,
        resource_library: ResourceLibrary,
        orchestrator: AssistantOrchestrator,
        task_graph_builder: TaskGraphBuilder,
        kpi_tracker: KPITracker,
        msg_hub_factory: Callable[..., object] | None = None,
    ) -> None:
        self.project_pool = project_pool
        self.memory_pool = memory_pool
        self.resource_library = resource_library
        self.orchestrator = orchestrator
        self.task_graph_builder = task_graph_builder
        self.kpi_tracker = kpi_tracker
        self.msg_hub_factory = msg_hub_factory

    def _persist_intent(self, intent: IntentRequest) -> None:
        entry = MemoryEntry(
            key=f"intent:{intent.user_id}:{intent.project_id}",
            content=intent.utterance,
            tags={"intent", intent.user_id},
        )
        self.memory_pool.save(entry)

    def run_cycle(
        self,
        intent: IntentRequest,
        acceptance: AcceptanceCriteria,
        *,
        baseline_cost: float,
        observed_cost: float,
        baseline_time: float,
        observed_time: float,
    ) -> ExecutionReport:
        self._persist_intent(intent)
        plan = self.orchestrator.plan_strategy(intent, acceptance)
        graph = self.task_graph_builder.build(
            requirements=plan.requirement_map,
            rankings=plan.rankings,
            edges=None,
        )

        for node_id in graph.topological_order():
            graph.mark_running(node_id)
            graph.mark_completed(node_id)

        observed_metrics = {"quality": 1.0}
        accepted = self.orchestrator.evaluate_acceptance(plan, observed_metrics)

        kpi_record = self.kpi_tracker.record_cycle(
            baseline_cost=baseline_cost,
            observed_cost=observed_cost,
            baseline_time=baseline_time,
            observed_time=observed_time,
        )

        task_status = {node.node_id: node.status.value for node in graph.nodes()}

        return ExecutionReport(
            project_id=intent.project_id,
            accepted=accepted,
            kpi=kpi_record,
            task_status=task_status,
            plan=plan,
        )
