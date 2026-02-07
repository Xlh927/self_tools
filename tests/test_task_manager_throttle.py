#!/usr/bin/env python3
import os
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.task_manager import TaskManager


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def with_env(env_vars):
    keys = list(env_vars.keys())
    old_values = {key: os.environ.get(key) for key in keys}
    for key, value in env_vars.items():
        os.environ[key] = str(value)

    def restore():
        for key in keys:
            old = old_values.get(key)
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old

    return restore


def run_delta_case(base_dir: Path):
    restore = with_env({
        "SELF_TOOLS_PROGRESS_MIN_INTERVAL_MS": "10000",
        "SELF_TOOLS_PROGRESS_MIN_DELTA": "10",
    })
    manager = None
    try:
        manager = TaskManager(db_path=str(base_dir / "delta.db"), max_workers=1)
        task_id, cancel_event, pause_event = manager.create_task(message="delta case")
        callback = manager.make_progress_callback(task_id, cancel_event, pause_event)

        callback(1, 100, "step")
        assert_true(manager.get_task(task_id)["progress"] == 1, "first progress update missing")

        callback(5, 100, "step")
        assert_true(manager.get_task(task_id)["progress"] == 1, "small delta should be throttled")

        callback(15, 100, "step")
        assert_true(manager.get_task(task_id)["progress"] == 15, "large delta should bypass throttle")

        events = manager.get_task_events(task_id, limit=100)
        updated_events = [item for item in events if item.get("event_type") == "updated"]
        assert_true(len(updated_events) == 2, f"unexpected updated event count: {len(updated_events)}")
    finally:
        if manager:
            manager.close()
        restore()


def run_interval_case(base_dir: Path):
    restore = with_env({
        "SELF_TOOLS_PROGRESS_MIN_INTERVAL_MS": "80",
        "SELF_TOOLS_PROGRESS_MIN_DELTA": "90",
    })
    manager = None
    try:
        manager = TaskManager(db_path=str(base_dir / "interval.db"), max_workers=1)
        task_id, cancel_event, pause_event = manager.create_task(message="interval case")
        callback = manager.make_progress_callback(task_id, cancel_event, pause_event)

        callback(1, 100, "step")
        assert_true(manager.get_task(task_id)["progress"] == 1, "first progress update missing")

        callback(2, 100, "step")
        assert_true(manager.get_task(task_id)["progress"] == 1, "second update should be throttled before interval")

        time.sleep(0.1)
        callback(3, 100, "step")
        assert_true(manager.get_task(task_id)["progress"] == 3, "interval-based update should pass")

        events = manager.get_task_events(task_id, limit=100)
        updated_events = [item for item in events if item.get("event_type") == "updated"]
        assert_true(len(updated_events) == 2, f"unexpected updated event count: {len(updated_events)}")
    finally:
        if manager:
            manager.close()
        restore()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp)
        run_delta_case(base_dir)
        run_interval_case(base_dir)
    print("OK: task manager progress throttle test passed")


if __name__ == "__main__":
    main()

