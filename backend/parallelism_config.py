"""
Unified concurrency policy for task queue and CV tool executors.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExecutorPlan:
    kind: str  # serial | thread | process
    workers: int


def _env_int(name: str, default: int, *, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        value = default
    else:
        try:
            value = int(str(raw).strip())
        except Exception:
            value = default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def logical_cpu_count() -> int:
    return max(1, int(os.cpu_count() or 1))


def usable_cpu_count() -> int:
    logical = logical_cpu_count()
    default_reserved = 1 if logical >= 4 else 0
    reserved = _env_int("SELF_TOOLS_RESERVED_CPUS", default_reserved, minimum=0, maximum=max(0, logical - 1))
    return max(1, logical - reserved)


def default_task_queue_workers() -> int:
    explicit = os.environ.get("SELF_TOOLS_MAX_WORKERS")
    if explicit and explicit.strip():
        try:
            return max(1, int(explicit))
        except Exception:
            pass

    # Queue workers handle independent tasks; keep moderate to avoid over-subscription.
    return max(1, min(4, usable_cpu_count()))


def _apply_worker_caps(workers: int, *, pool_kind: str, total_items: int) -> int:
    workers = max(1, min(int(total_items), int(workers)))

    global_cap = _env_int("SELF_TOOLS_MAX_POOL_WORKERS", 0, minimum=0)
    if global_cap > 0:
        workers = min(workers, global_cap)

    if pool_kind == "process":
        cap = _env_int("SELF_TOOLS_MAX_PROCESS_WORKERS", 0, minimum=0)
    else:
        cap = _env_int("SELF_TOOLS_MAX_THREAD_WORKERS", 0, minimum=0)
    if cap > 0:
        workers = min(workers, cap)

    forced = _env_int("SELF_TOOLS_FORCE_WORKERS", 0, minimum=0)
    if forced > 0:
        workers = min(total_items, max(1, forced))

    return max(1, workers)


def get_executor_plan(total_items: int, *, workload: str = "cpu", prefer_process: bool = True) -> ExecutorPlan:
    total_items = max(0, int(total_items))
    if total_items <= 1:
        return ExecutorPlan(kind="serial", workers=1)

    forced_kind = os.environ.get("SELF_TOOLS_FORCE_EXECUTOR", "auto").strip().lower()
    if forced_kind not in {"auto", "serial", "thread", "process"}:
        forced_kind = "auto"
    if forced_kind == "serial":
        return ExecutorPlan(kind="serial", workers=1)

    min_parallel_items = _env_int("SELF_TOOLS_MIN_PARALLEL_ITEMS", 4, minimum=1)
    if forced_kind == "auto" and total_items < min_parallel_items:
        return ExecutorPlan(kind="serial", workers=1)

    usable = usable_cpu_count()
    if workload == "io":
        default_workers = max(2, usable * 2)
    else:
        default_workers = usable

    process_min_items = _env_int("SELF_TOOLS_PROCESS_MIN_ITEMS", 24, minimum=1)
    use_process = (
        forced_kind == "process"
        or (
            forced_kind == "auto"
            and prefer_process
            and workload != "io"
            and total_items >= process_min_items
        )
    )

    if forced_kind == "thread":
        use_process = False

    pool_kind = "process" if use_process else "thread"
    workers = _apply_worker_caps(default_workers, pool_kind=pool_kind, total_items=total_items)

    if workers <= 1:
        return ExecutorPlan(kind="serial", workers=1)
    return ExecutorPlan(kind=pool_kind, workers=workers)

