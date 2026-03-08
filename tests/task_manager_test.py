#!/usr/bin/env python3
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["SELF_TOOLS_TASK_DB"] = str(Path(tmp) / "tasks.db")

        from backend.task_manager import TaskManager

        task_manager = TaskManager()
        entered_running_phase = threading.Event()
        allow_finish = threading.Event()

        def run_task(task_id, cancel_event, pause_event):
            progress = task_manager.make_progress_callback(task_id, cancel_event, pause_event)
            progress(1, 1, "Finishing")
            entered_running_phase.set()
            allow_finish.wait(timeout=5.0)

        task_id = task_manager.start_task(
            message="Starting test task",
            run_fn=run_task,
            max_retries=0,
        )

        deadline = time.time() + 5.0
        snapshot = None
        while time.time() < deadline:
            if entered_running_phase.is_set():
                snapshot = task_manager.get_task(task_id)
                if snapshot and snapshot.get("status") == "running":
                    break
            time.sleep(0.05)

        assert_true(snapshot is not None, "task never entered running phase")
        assert_true(snapshot.get("progress") == 99, f"running task progress should cap at 99: {snapshot}")

        allow_finish.set()

        deadline = time.time() + 5.0
        completed = None
        while time.time() < deadline:
            completed = task_manager.get_task(task_id)
            if completed and completed.get("status") == "completed":
                break
            time.sleep(0.05)

        task_manager.close()

        assert_true(completed is not None, "task completion snapshot missing")
        assert_true(completed.get("status") == "completed", f"task did not complete: {completed}")
        assert_true(completed.get("progress") == 100, f"completed task should be 100: {completed}")

    print("OK: task manager test passed")


if __name__ == "__main__":
    main()
