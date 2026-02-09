#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.parallelism_config import default_task_queue_workers, get_executor_plan


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def with_env(env_vars):
    keys = list(env_vars.keys())
    old_values = {key: os.environ.get(key) for key in keys}
    for key, value in env_vars.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)

    def restore():
        for key in keys:
            old = old_values.get(key)
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old

    return restore


def run_default_worker_case():
    restore = with_env(
        {
            "SELF_TOOLS_MAX_WORKERS": None,
            "SELF_TOOLS_RESERVED_CPUS": None,
        }
    )
    try:
        with patch("backend.parallelism_config.os.cpu_count", return_value=8):
            workers = default_task_queue_workers()
            assert_true(workers == 4, f"unexpected default queue workers: {workers}")
    finally:
        restore()


def run_forced_worker_case():
    restore = with_env({"SELF_TOOLS_MAX_WORKERS": "9"})
    try:
        with patch("backend.parallelism_config.os.cpu_count", return_value=8):
            workers = default_task_queue_workers()
            assert_true(workers == 9, f"forced queue workers ignored: {workers}")
    finally:
        restore()


def run_auto_plan_cases():
    restore = with_env(
        {
            "SELF_TOOLS_FORCE_EXECUTOR": None,
            "SELF_TOOLS_FORCE_WORKERS": None,
            "SELF_TOOLS_RESERVED_CPUS": None,
            "SELF_TOOLS_MIN_PARALLEL_ITEMS": None,
            "SELF_TOOLS_PROCESS_MIN_ITEMS": None,
            "SELF_TOOLS_MAX_POOL_WORKERS": None,
            "SELF_TOOLS_MAX_PROCESS_WORKERS": None,
            "SELF_TOOLS_MAX_THREAD_WORKERS": None,
        }
    )
    try:
        with patch("backend.parallelism_config.os.cpu_count", return_value=8):
            serial_plan = get_executor_plan(2, workload="cpu", prefer_process=True)
            assert_true(serial_plan.kind == "serial", f"small batch should be serial: {serial_plan}")

            io_plan = get_executor_plan(10, workload="io", prefer_process=False)
            assert_true(io_plan.kind == "thread", f"io batch should prefer threads: {io_plan}")
            assert_true(io_plan.workers == 10, f"unexpected io thread workers: {io_plan.workers}")

            cpu_plan = get_executor_plan(40, workload="cpu", prefer_process=True)
            assert_true(cpu_plan.kind == "process", f"large cpu batch should prefer process: {cpu_plan}")
            assert_true(cpu_plan.workers == 7, f"unexpected cpu process workers: {cpu_plan.workers}")
    finally:
        restore()


def run_forced_plan_cases():
    restore = with_env(
        {
            "SELF_TOOLS_FORCE_EXECUTOR": "thread",
            "SELF_TOOLS_FORCE_WORKERS": "3",
            "SELF_TOOLS_RESERVED_CPUS": "0",
        }
    )
    try:
        with patch("backend.parallelism_config.os.cpu_count", return_value=8):
            forced_thread = get_executor_plan(20, workload="cpu", prefer_process=True)
            assert_true(forced_thread.kind == "thread", f"force thread ignored: {forced_thread}")
            assert_true(forced_thread.workers == 3, f"force workers ignored: {forced_thread}")
    finally:
        restore()

    restore = with_env({"SELF_TOOLS_FORCE_EXECUTOR": "serial"})
    try:
        serial = get_executor_plan(100, workload="cpu", prefer_process=True)
        assert_true(serial.kind == "serial", f"force serial ignored: {serial}")
        assert_true(serial.workers == 1, f"force serial workers invalid: {serial.workers}")
    finally:
        restore()


def main():
    run_default_worker_case()
    run_forced_worker_case()
    run_auto_plan_cases()
    run_forced_plan_cases()
    print("OK: parallelism config test passed")


if __name__ == "__main__":
    main()
