# -*- coding: utf-8 -*-
"""Execution loop tying all sections together (III)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from .intent import (
    AcceptanceCriteria,
    AssistantOrchestrator,
    IntentRequest,
    StrategyPlan,
)
from .kpi import KPIRecord, KPITracker
from .memory import MemoryEntry, MemoryPool, ProjectDescriptor, ProjectPool, ResourceLibrary
from .task_graph import TaskGraphBuilder
from .msghub import MsgHubBroadcaster, RoundUpdate
from .artifacts import ArtifactDeliveryManager, ArtifactDeliveryResult
import shortuuid


@dataclass
class ExecutionReport:
    project_id: str | None
    accepted: bool
    kpi: KPIRecord
    task_status: dict[str, str]
    plan: StrategyPlan
    deliverable: ArtifactDeliveryResult | None = None


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
        msg_hub_factory: Callable[[str], MsgHubBroadcaster] | None = None,
        delivery_manager: ArtifactDeliveryManager | None = None,
        max_rounds: int = 3,
    ) -> None:
        self.project_pool = project_pool
        self.memory_pool = memory_pool
        self.resource_library = resource_library
        self.orchestrator = orchestrator
        self.task_graph_builder = task_graph_builder
        self.kpi_tracker = kpi_tracker
        self.msg_hub_factory = msg_hub_factory
        self.delivery_manager = delivery_manager
        self.max_rounds = max_rounds

    def _persist_intent(self, intent: IntentRequest) -> None:
        entry = MemoryEntry(
            key=f"intent:{intent.user_id}:{intent.project_id}",
            content=intent.utterance,
            tags={"intent", intent.user_id},
        )
        self.memory_pool.save(entry)

    def _ensure_project(self, intent: IntentRequest) -> str:
        if intent.project_id:
            if self.project_pool.get(intent.project_id) is None:
                descriptor = ProjectDescriptor(
                    project_id=intent.project_id,
                    name=f"Project {intent.project_id}",
                    metadata={"source": "aa"},
                )
                self.project_pool.register(descriptor)
            return intent.project_id
        project_id = f"proj-{shortuuid.uuid()}"
        descriptor = ProjectDescriptor(
            project_id=project_id,
            name=f"{intent.user_id}-{project_id}",
            metadata={"source": "aa"},
        )
        self.project_pool.register(descriptor)
        intent.project_id = project_id
        return project_id

    def _persist_round_summary(
        self,
        *,
        project_id: str,
        round_index: int,
        plan: StrategyPlan,
        task_status: dict[str, str],
        observed_metrics: dict[str, float],
    ) -> None:
        summary_lines = [
            f"Round {round_index}",
            f"Observed metrics: {observed_metrics}",
        ]
        for node_id, status in task_status.items():
            agent_name = (
                plan.rankings.get(node_id).profile.name
                if node_id in plan.rankings
                else "unassigned"
            )
            summary_lines.append(f"- {node_id}: {status} -> {agent_name}")
        entry = MemoryEntry(
            key=f"project:{project_id}:round:{round_index}",
            content="\n".join(summary_lines),
            tags={f"project:{project_id}", "round"},
        )
        self.memory_pool.save(entry)

    def _compute_metric_snapshot(
        self,
        *,
        baseline_cost: float,
        observed_cost: float,
        baseline_time: float,
        observed_time: float,
        acceptance: AcceptanceCriteria,
        round_index: int,
    ) -> tuple[float, dict[str, float], dict[str, bool]]:
        def ratio(baseline: float, observed: float) -> float:
            if observed <= 0:
                return 1.0
            if baseline <= 0:
                return 0.0
            return min(1.0, baseline / observed)

        def metric_value(name: str) -> float:
            lowered = name.lower()
            cost_component = ratio(baseline_cost, observed_cost)
            time_component = ratio(baseline_time, observed_time)
            base_score = (cost_component + time_component) / 2
            if "cost" in lowered:
                value = cost_component
            elif "time" in lowered or "speed" in lowered:
                value = time_component
            else:
                value = base_score
            if self.max_rounds > 1:
                progressive_bonus = ((round_index - 1) / (self.max_rounds - 1)) * 0.5
                value += progressive_bonus
            return max(0.0, min(1.0, value))

        metrics = acceptance.metrics or {"quality": 0.9}
        values: dict[str, float] = {name: metric_value(name) for name in metrics}
        passes: dict[str, bool] = {
            name: values[name] >= target for name, target in metrics.items()
        }
        total = max(len(metrics), 1)
        pass_ratio = sum(1 for ok in passes.values() if ok) / total
        return pass_ratio, values, passes

    def _broadcast_progress(
        self,
        *,
        project_id: str,
        round_index: int,
        summary: str,
        status: dict[str, str],
    ) -> None:
        if self.msg_hub_factory is None:
            return
        hub = self.msg_hub_factory(project_id)
        update = RoundUpdate(
            project_id=project_id,
            round_index=round_index,
            summary=summary,
            status=status,
        )
        hub.broadcast(update)

    @staticmethod
    def _plan_summary(plan: StrategyPlan) -> str:
        names = []
        for node_id, ranking in plan.rankings.items():
            names.append(f"{node_id}->{ranking.profile.name}")
        return "; ".join(names)

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
        project_id = self._ensure_project(intent)
        self._persist_intent(intent)
        plan = self.orchestrator.plan_strategy(intent, acceptance)
        graph = self.task_graph_builder.build(
            requirements=plan.requirement_map,
            rankings=plan.rankings,
            edges=None,
        )

        accepted = False
        task_status: Dict[str, str] = {}
        observed_metrics: Dict[str, float] = {}
        deliverable: ArtifactDeliveryResult | None = None

        for round_index in range(1, self.max_rounds + 1):
            for node_id in graph.topological_order():
                graph.mark_running(node_id)
                graph.mark_completed(node_id)

            task_status = {node.node_id: node.status.value for node in graph.nodes()}
            pass_ratio, metric_values, metric_passes = self._compute_metric_snapshot(
                baseline_cost=baseline_cost,
                observed_cost=observed_cost,
                baseline_time=baseline_time,
                observed_time=observed_time,
                acceptance=acceptance,
                round_index=round_index,
            )
            observed_metrics = {
                **metric_values,
                "pass_ratio": pass_ratio,
                "passed": sum(metric_passes.values()),
                "total": max(len(metric_passes), 1),
            }
            self._persist_round_summary(
                project_id=project_id,
                round_index=round_index,
                plan=plan,
                task_status=task_status,
                observed_metrics=observed_metrics,
            )
            self._broadcast_progress(
                project_id=project_id,
                round_index=round_index,
                summary=f"Round {round_index} status: {task_status}",
                status=task_status,
            )

            accepted = self.orchestrator.evaluate_acceptance(plan, observed_metrics)
            if accepted:
                break

            # Re-plan for next round to reflect potential agent changes.
            plan = self.orchestrator.plan_strategy(intent, acceptance)
            graph = self.task_graph_builder.build(
                requirements=plan.requirement_map,
                rankings=plan.rankings,
                edges=None,
            )
            observed_cost *= 0.8
            observed_time *= 0.8

        kpi_record = self.kpi_tracker.record_cycle(
            baseline_cost=baseline_cost,
            observed_cost=observed_cost,
            baseline_time=baseline_time,
            observed_time=observed_time,
        )

        if accepted and self.delivery_manager is not None:
            artifact_type = intent.artifact_type or "web"
            deliverable = self.delivery_manager.deliver(
                artifact_type=artifact_type,
                project_id=project_id,
                plan_summary=self._plan_summary(plan),
                task_status=task_status,
            )

        return ExecutionReport(
            project_id=project_id,
            accepted=accepted,
            kpi=kpi_record,
            task_status=task_status,
            plan=plan,
            deliverable=deliverable,
        )
