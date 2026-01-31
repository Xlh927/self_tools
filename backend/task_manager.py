"""
Task management utilities for long-running background jobs.
Centralizes task progress, controls, and lifecycle helpers.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, Optional, Tuple

# Global dictionaries shared across app endpoints and tasks
# Format: {task_id: {'status': 'running'|'paused'|'stopped'|'error'|'completed', 'progress': 0-100, 'message': '', 'result': None}}
TASK_PROGRESS: Dict[str, dict] = {}

# Format: {task_id: {'cancel': Event, 'pause': Event}}
TASK_CONTROLS: Dict[str, dict] = {}

# Legacy events map (kept for backward compatibility)
TASK_EVENTS: Dict[str, threading.Event] = {}

TASK_RETENTION_LIMIT = 200
TASK_COMPLETED_STATUSES = {'completed', 'error', 'stopped', 'cancelled'}


def prune_task_progress(limit: int = TASK_RETENTION_LIMIT) -> None:
    """Drop oldest completed tasks to avoid unbounded growth."""
    if len(TASK_PROGRESS) <= limit:
        return
    completed = [
        (task_id, task.get('finished_at'))
        for task_id, task in TASK_PROGRESS.items()
        if task.get('status') in TASK_COMPLETED_STATUSES and task.get('finished_at')
    ]
    if len(completed) <= limit:
        return
    completed.sort(key=lambda item: item[1])
    for task_id, _ in completed[:-limit]:
        TASK_PROGRESS.pop(task_id, None)


class TaskManager:
    """Manage task lifecycle and shared progress state."""

    def create_task(self, message: str = 'Starting...', status: str = 'running') -> Tuple[str, threading.Event, threading.Event]:
        task_id = str(uuid.uuid4())
        TASK_PROGRESS[task_id] = {
            'status': status,
            'progress': 0,
            'message': message,
            'result': None
        }

        cancel_event = threading.Event()
        pause_event = threading.Event()
        TASK_CONTROLS[task_id] = {
            'cancel': cancel_event,
            'pause': pause_event
        }
        # Keep legacy mapping in sync for existing endpoints
        TASK_EVENTS[task_id] = cancel_event
        return task_id, cancel_event, pause_event

    def get_task(self, task_id: str) -> Optional[dict]:
        return TASK_PROGRESS.get(task_id)

    def update_task(self, task_id: str, **fields) -> None:
        if task_id in TASK_PROGRESS:
            TASK_PROGRESS[task_id].update(fields)

    def finish_task(self, task_id: str, status: str, message: str, result: Optional[dict] = None, error: Optional[str] = None, error_code: Optional[str] = None) -> None:
        payload = {
            'status': status,
            'progress': 100,
            'message': message,
            'finished_at': time.time()
        }
        if result is not None:
            payload['result'] = result
        if error is not None:
            payload['error'] = error
        if error_code is not None:
            payload['error_code'] = error_code
        self.update_task(task_id, **payload)

    def finish_task_from_exception(self, task_id: str, error: Exception, cancel_message: str = 'Task cancelled') -> None:
        cancelled = str(error) == 'Operation cancelled by user'
        status = 'stopped' if cancelled else 'error'
        message = cancel_message if cancelled else str(error)
        error_value = str(error) if status == 'error' else None
        error_code = 'ERR_TASK_CANCELLED' if cancelled else 'ERR_INTERNAL'
        self.finish_task(task_id, status=status, message=message, error=error_value, error_code=error_code)

    def make_progress_callback(self, task_id: str, cancel_event: threading.Event, pause_event: threading.Event):
        def progress_callback(current, total, message):
            if cancel_event.is_set():
                raise Exception('Operation cancelled by user')
            self.wait_if_paused(task_id, pause_event, cancel_event)
            if total > 0:
                progress = int((current / total) * 100)
                self.update_task(
                    task_id,
                    progress=progress,
                    message=f"{message} ({current}/{total})"
                )

        return progress_callback

    def start_task(self, message: str, run_fn, status: str = 'running') -> str:
        task_id, cancel_event, pause_event = self.create_task(message=message, status=status)

        def runner():
            try:
                run_fn(task_id, cancel_event, pause_event)
            except Exception as e:
                self.finish_task_from_exception(task_id, e)
            finally:
                self.cleanup_task(task_id)

        thread = threading.Thread(target=runner)
        thread.start()
        return task_id

    def pause_task(self, task_id: str) -> bool:
        controls = TASK_CONTROLS.get(task_id)
        if not controls or 'pause' not in controls:
            return False
        controls['pause'].set()
        self.update_task(task_id, status='paused')
        return True

    def resume_task(self, task_id: str) -> bool:
        controls = TASK_CONTROLS.get(task_id)
        if not controls or 'pause' not in controls:
            return False
        controls['pause'].clear()
        self.update_task(task_id, status='running')
        return True

    def stop_task(self, task_id: str) -> bool:
        controls = TASK_CONTROLS.get(task_id)
        if not controls or 'cancel' not in controls:
            return False
        controls['cancel'].set()
        self.update_task(task_id, status='stopped')
        return True

    def wait_if_paused(self, task_id: str, pause_event: threading.Event, cancel_event: threading.Event) -> None:
        while pause_event.is_set():
            current = TASK_PROGRESS.get(task_id, {})
            if current.get('status') != 'paused':
                self.update_task(task_id, status='paused', message='Task paused')
            time.sleep(0.5)
            if cancel_event.is_set():
                raise Exception('Operation cancelled by user')

        if TASK_PROGRESS.get(task_id, {}).get('status') == 'paused':
            self.update_task(task_id, status='running')

    def cleanup_task(self, task_id: str) -> None:
        TASK_CONTROLS.pop(task_id, None)
        TASK_EVENTS.pop(task_id, None)
        prune_task_progress()
