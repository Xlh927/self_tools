"""
Serial execution policy for task orchestration and CV tool processing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutorPlan:
    kind: str  # serial
    workers: int


def logical_cpu_count() -> int:
    return 1


def usable_cpu_count() -> int:
    return 1


def default_task_queue_workers() -> int:
    return 1


def get_executor_plan(total_items: int, *, workload: str = "cpu", prefer_process: bool = True) -> ExecutorPlan:
    del total_items, workload, prefer_process
    return ExecutorPlan(kind="serial", workers=1)
