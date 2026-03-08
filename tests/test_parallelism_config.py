#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.parallelism_config import default_task_queue_workers, get_executor_plan


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    workers = default_task_queue_workers()
    assert_true(workers == 1, f"task runtime should be single-threaded: {workers}")

    for total_items in (0, 1, 2, 20, 100):
        for workload in ("cpu", "io"):
            plan = get_executor_plan(total_items, workload=workload, prefer_process=True)
            assert_true(plan.kind == "serial", f"executor must stay serial: {plan}")
            assert_true(plan.workers == 1, f"serial executor workers invalid: {plan}")

    print("OK: parallelism config test passed")


if __name__ == "__main__":
    main()
