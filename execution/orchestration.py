# -*- coding: utf-8 -*-
"""Task sharding orchestration module.

This module provides functions for:
1. Topological sorting of requirements based on dependencies
2. Creating Celery workflows for parallel/sequential execution
3. Batch scheduling utilities
"""
import logging
from collections import defaultdict
from typing import Dict, List, Set

from celery import chain, chord, group

logger = logging.getLogger(__name__)


def topological_sort_requirements(
    requirements: List[Dict],
    dependencies: Dict[str, List[str]]
) -> List[List[str]]:
    """
    Topologically sort requirements by dependencies, returning batches.

    Same batch requirements are independent and can run in parallel.
    Different batches must run sequentially.

    Args:
        requirements: List of requirements [{"id": "REQ-001", ...}, ...]
        dependencies: Dependency map {"REQ-002": ["REQ-001"], ...}

    Returns:
        List of batches [["REQ-001", "REQ-004"], ["REQ-002", "REQ-003"], ...]

    Example:
        >>> reqs = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
        >>> deps = {"B": ["A"], "C": ["A"]}
        >>> topological_sort_requirements(reqs, deps)
        [["A"], ["B", "C"]]
    """
    if not requirements:
        return []

    # Build in-degree table and adjacency list
    req_ids = {req["id"] for req in requirements}
    in_degree = {req["id"]: 0 for req in requirements}
    adjacency = defaultdict(list)

    for req_id, deps in dependencies.items():
        if req_id not in req_ids:
            continue
        # Only count dependencies that exist in current requirement set
        valid_deps = [d for d in deps if d in req_ids]
        in_degree[req_id] = len(valid_deps)
        for dep in valid_deps:
            adjacency[dep].append(req_id)

    # Kahn's algorithm with batch tracking
    batches = []
    current_batch = [rid for rid, deg in in_degree.items() if deg == 0]

    while current_batch:
        batches.append(sorted(current_batch))  # Sort for deterministic ordering
        next_batch = []

        for rid in current_batch:
            for neighbor in adjacency[rid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_batch.append(neighbor)

        current_batch = next_batch

    # Check for cycles (remaining nodes with non-zero in-degree)
    remaining = [rid for rid, deg in in_degree.items() if deg > 0]
    if remaining:
        logger.warning(f"Circular dependencies detected: {remaining}")
        # Add remaining as final batch (break cycle)
        batches.append(sorted(remaining))

    return batches


def create_round_workflow(
    execution_round_id: str,
    req_id_to_exec_id: Dict[str, str],
    batches: List[List[str]],
    inner_round_number: int,
):
    """
    Create Celery workflow for one inner round of execution.

    Args:
        execution_round_id: ExecutionRound UUID
        req_id_to_exec_id: Map from requirement_id to RequirementExecution UUID
        batches: Topologically sorted batches
        inner_round_number: Current inner round number

    Returns:
        Celery workflow (chain of groups followed by aggregate)
    """
    from .tasks import execute_requirement_task, aggregate_round_task

    if not batches:
        # No tasks, skip to aggregate
        return aggregate_round_task.si(execution_round_id, inner_round_number)

    # Build batch task groups
    batch_tasks = []

    for batch_idx, batch in enumerate(batches):
        # Same batch runs in parallel (group)
        tasks = []
        for req_id in batch:
            exec_id = req_id_to_exec_id.get(req_id)
            if exec_id:
                tasks.append(execute_requirement_task.s(str(exec_id)))
            else:
                logger.warning(f"No execution ID found for requirement {req_id}")

        if tasks:
            if len(tasks) == 1:
                # Single task, no need for group
                batch_tasks.append(tasks[0])
            else:
                # Multiple tasks, use group for parallel execution
                batch_tasks.append(group(*tasks))

    if not batch_tasks:
        # All tasks filtered out
        return aggregate_round_task.si(execution_round_id, inner_round_number)

    # Chain batches: batch1 -> batch2 -> ... -> aggregate
    # Use .si() for aggregate to ignore previous results
    workflow = chain(
        *batch_tasks,
        aggregate_round_task.si(execution_round_id, inner_round_number)
    )

    return workflow


def estimate_execution_time(requirement_count: int, has_dependencies: bool) -> int:
    """
    Estimate execution time in seconds for planning.

    Args:
        requirement_count: Number of requirements
        has_dependencies: Whether there are inter-requirement dependencies

    Returns:
        Estimated seconds
    """
    # Base: 60-180 seconds per requirement
    # With dependencies: add 30% overhead for sequential batches
    base_per_req = 120  # 2 minutes average
    total = base_per_req * requirement_count

    if has_dependencies:
        total = int(total * 1.3)

    # Cap at reasonable maximum (30 minutes)
    return min(total, 1800)


def get_ready_requirements(
    execution_round_id: str,
    inner_round_number: int,
) -> List[str]:
    """
    Get requirement IDs that are ready to execute.

    A requirement is ready when:
    1. Status is 'scheduled'
    2. All dependencies have status 'completed' with is_passed=True

    Args:
        execution_round_id: ExecutionRound UUID
        inner_round_number: Current inner round number

    Returns:
        List of requirement_execution_ids ready to run
    """
    from .models import RequirementExecution

    # Get all scheduled requirements for this round
    scheduled = RequirementExecution.objects.filter(
        execution_round_id=execution_round_id,
        inner_round_number=inner_round_number,
        status='scheduled',
    )

    ready_ids = []

    for req_exec in scheduled:
        # Check if all dependencies are satisfied
        deps = req_exec.depends_on or []
        if not deps:
            # No dependencies, ready to run
            ready_ids.append(str(req_exec.id))
            continue

        # Check each dependency
        all_deps_passed = True
        for dep_id in deps:
            dep_exec = RequirementExecution.objects.filter(
                execution_round_id=execution_round_id,
                requirement_id=dep_id,
                inner_round_number__lte=inner_round_number,
                status='completed',
                is_passed=True,
            ).first()

            if not dep_exec:
                all_deps_passed = False
                break

        if all_deps_passed:
            ready_ids.append(str(req_exec.id))

    return ready_ids
