"""
Persistent task queue with retry, concurrency control and task history.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import queue
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

TASK_TERMINAL_STATUSES = {"completed", "error", "stopped", "cancelled"}
TASK_ACTIVE_STATUSES = {"queued", "running", "paused", "retrying"}
TASK_RETENTION_LIMIT = 500


def _now() -> float:
    return time.time()


def _to_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _from_json(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


class TaskManager:
    """SQLite-backed in-process task queue."""

    def __init__(self, db_path: Optional[str] = None, max_workers: Optional[int] = None):
        root = Path.cwd()
        default_db = root / "data" / "tasks.db"
        env_db = os.environ.get("SELF_TOOLS_TASK_DB")
        self.db_path = Path(env_db) if env_db else Path(db_path) if db_path else default_db
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.max_workers = max(1, int(max_workers or os.environ.get("SELF_TOOLS_MAX_WORKERS", 2)))
        self.retry_backoff_seconds = max(1, int(os.environ.get("SELF_TOOLS_RETRY_BACKOFF", 2)))

        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()

        self._queue: "queue.PriorityQueue[tuple[int, float, str]]" = queue.PriorityQueue()
        self._shutdown = threading.Event()
        self._workers: list[threading.Thread] = []
        self._timers: Dict[str, threading.Timer] = {}

        self._controls: Dict[str, dict] = {}
        self._runners: Dict[str, Callable[[str, threading.Event, threading.Event], None]] = {}
        self._process_name = multiprocessing.current_process().name

        self._init_db()
        # Avoid mutating task lifecycle from multiprocessing child processes
        # (e.g. ProcessPoolExecutor workers importing backend.app on macOS spawn).
        if self._process_name == "MainProcess":
            self._recover_unfinished_tasks()
            self._start_workers()

    # -----------------------------
    # DB helpers
    # -----------------------------
    def _execute(self, sql: str, params: tuple = (), fetch: Optional[str] = None):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            self._conn.commit()
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            return None

    def _init_db(self) -> None:
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                result_json TEXT,
                error TEXT,
                error_code TEXT,
                attempt INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 0,
                priority INTEGER NOT NULL DEFAULT 100,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                started_at REAL,
                finished_at REAL,
                next_run_at REAL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT,
                message TEXT,
                payload_json TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        self._execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_events_task_id ON task_events(task_id)")

    def _log_event(self, task_id: str, event_type: str, status: Optional[str], message: Optional[str], payload: Optional[dict] = None) -> None:
        self._execute(
            """
            INSERT INTO task_events(task_id, event_type, status, message, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, event_type, status, message, _to_json(payload), _now()),
        )

    # -----------------------------
    # Lifecycle
    # -----------------------------
    def _start_workers(self) -> None:
        for index in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, name=f"task-worker-{index + 1}", daemon=True)
            worker.start()
            self._workers.append(worker)

    def close(self) -> None:
        self._shutdown.set()
        for timer in list(self._timers.values()):
            try:
                timer.cancel()
            except Exception:
                pass
        for worker in self._workers:
            worker.join(timeout=0.2)
        with self._lock:
            self._conn.close()

    def _recover_unfinished_tasks(self) -> None:
        rows = self._execute(
            "SELECT id, status FROM tasks WHERE status IN ('queued', 'running', 'paused', 'retrying')",
            fetch="all",
        ) or []
        for row in rows:
            task_id = row["id"]
            self._execute(
                """
                UPDATE tasks
                SET status = ?, error = ?, error_code = ?, message = ?, finished_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    "error",
                    "Task interrupted by process restart",
                    "ERR_TASK_RECOVERED",
                    "Task interrupted by process restart",
                    _now(),
                    _now(),
                    task_id,
                ),
            )
            self._log_event(
                task_id,
                event_type="recovered_as_error",
                status="error",
                message="Task interrupted by process restart",
            )

    # -----------------------------
    # Public read APIs
    # -----------------------------
    def get_task(self, task_id: str) -> Optional[dict]:
        row = self._execute("SELECT * FROM tasks WHERE id = ?", (task_id,), fetch="one")
        return self._row_to_task(row) if row else None

    def list_tasks(self, limit: int = 100, status: Optional[str] = None) -> list[dict]:
        limit = max(1, min(int(limit), 500))
        if status:
            rows = self._execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
                fetch="all",
            ) or []
        else:
            rows = self._execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                (limit,),
                fetch="all",
            ) or []
        return [self._row_to_task(row) for row in rows]

    def get_task_events(self, task_id: str, limit: int = 200) -> list[dict]:
        limit = max(1, min(int(limit), 1000))
        rows = self._execute(
            """
            SELECT event_type, status, message, payload_json, created_at
            FROM task_events
            WHERE task_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (task_id, limit),
            fetch="all",
        ) or []
        events = []
        for row in rows:
            events.append(
                {
                    "event_type": row["event_type"],
                    "status": row["status"],
                    "message": row["message"],
                    "payload": _from_json(row["payload_json"]),
                    "created_at": row["created_at"],
                }
            )
        return events

    # -----------------------------
    # Public write APIs
    # -----------------------------
    def create_task(
        self,
        message: str = "Task queued",
        status: str = "queued",
        *,
        max_retries: int = 1,
        priority: int = 100,
    ) -> tuple[str, threading.Event, threading.Event]:
        task_id = str(uuid.uuid4())
        cancel_event = threading.Event()
        pause_event = threading.Event()
        created_at = _now()
        self._controls[task_id] = {"cancel": cancel_event, "pause": pause_event}

        self._execute(
            """
            INSERT INTO tasks(
                id, status, progress, message, result_json, error, error_code,
                attempt, max_retries, priority, created_at, updated_at, next_run_at
            )
            VALUES (?, ?, 0, ?, NULL, NULL, NULL, 0, ?, ?, ?, ?, ?)
            """,
            (task_id, status, message, max(0, int(max_retries)), int(priority), created_at, created_at, created_at),
        )
        self._log_event(task_id, event_type="created", status=status, message=message)
        return task_id, cancel_event, pause_event

    def start_task(
        self,
        message: str,
        run_fn: Callable[[str, threading.Event, threading.Event], None],
        status: str = "queued",
        *,
        max_retries: int = 1,
        priority: int = 100,
    ) -> str:
        task_id, cancel_event, pause_event = self.create_task(
            message=message,
            status=status,
            max_retries=max_retries,
            priority=priority,
        )
        self._runners[task_id] = run_fn
        self._enqueue_task(task_id, priority=priority)
        return task_id

    def update_task(self, task_id: str, **fields) -> None:
        if not fields:
            return
        current = self.get_task(task_id)
        if not current:
            return

        status = fields.get("status", current["status"])
        message = fields.get("message", current.get("message"))
        progress = int(fields.get("progress", current.get("progress", 0) or 0))
        result = fields.get("result", current.get("result"))
        error = fields.get("error", current.get("error"))
        error_code = fields.get("error_code", current.get("error_code"))
        attempt = int(fields.get("attempt", current.get("attempt", 0) or 0))
        max_retries = int(fields.get("max_retries", current.get("max_retries", 0) or 0))
        next_run_at = fields.get("next_run_at", current.get("next_run_at"))
        started_at = fields.get("started_at", current.get("started_at"))
        finished_at = fields.get("finished_at", current.get("finished_at"))

        self._execute(
            """
            UPDATE tasks
            SET status = ?, progress = ?, message = ?, result_json = ?, error = ?, error_code = ?,
                attempt = ?, max_retries = ?, next_run_at = ?, started_at = ?, finished_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                progress,
                message,
                _to_json(result),
                error,
                error_code,
                attempt,
                max_retries,
                next_run_at,
                started_at,
                finished_at,
                _now(),
                task_id,
            ),
        )
        self._log_event(
            task_id,
            event_type="updated",
            status=status,
            message=message,
            payload={"progress": progress, "attempt": attempt, "max_retries": max_retries},
        )

    def finish_task(
        self,
        task_id: str,
        status: str,
        message: str,
        result: Optional[dict] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> None:
        progress = 100 if status in TASK_TERMINAL_STATUSES else 0
        self.update_task(
            task_id,
            status=status,
            progress=progress,
            message=message,
            result=result,
            error=error,
            error_code=error_code,
            finished_at=_now() if status in TASK_TERMINAL_STATUSES else None,
            next_run_at=None,
        )
        if status in TASK_TERMINAL_STATUSES:
            self._cleanup_runtime(task_id)
            self.prune_task_progress()

    def finish_task_from_exception(self, task_id: str, error: Exception, cancel_message: str = "Task cancelled") -> None:
        cancelled = str(error) == "Operation cancelled by user"
        status = "stopped" if cancelled else "error"
        message = cancel_message if cancelled else str(error)
        error_value = None if cancelled else str(error)
        error_code = "ERR_TASK_CANCELLED" if cancelled else "ERR_INTERNAL"
        self.finish_task(task_id, status=status, message=message, error=error_value, error_code=error_code)

    def pause_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task or task.get("status") in TASK_TERMINAL_STATUSES:
            return False

        controls = self._controls.get(task_id)
        if controls:
            controls["pause"].set()

        if task["status"] in {"queued", "retrying"}:
            self.update_task(task_id, status="paused", message="Task paused before execution")
        else:
            self.update_task(task_id, status="paused", message="Task paused")
        return True

    def resume_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task or task.get("status") not in {"paused", "retrying"}:
            return False

        controls = self._controls.get(task_id)
        if controls:
            controls["pause"].clear()

        if task["status"] == "paused" and task.get("started_at") is None:
            self.update_task(task_id, status="queued", message="Task resumed")
            self._enqueue_task(task_id, priority=task.get("priority", 100))
        else:
            self.update_task(task_id, status="running", message="Task resumed")
        return True

    def stop_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task or task.get("status") in TASK_TERMINAL_STATUSES:
            return False

        controls = self._controls.get(task_id)
        if controls:
            controls["cancel"].set()

        if task["status"] in {"queued", "paused", "retrying"}:
            self.finish_task(
                task_id,
                status="stopped",
                message="Task cancelled before execution",
                error_code="ERR_TASK_CANCELLED",
            )
        else:
            self.update_task(task_id, status="stopped", message="Task cancellation requested", error_code="ERR_TASK_CANCELLED")
        return True

    def retry_task_now(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task or task["status"] not in {"error", "stopped"}:
            return False
        if task_id not in self._runners:
            return False
        self.update_task(
            task_id,
            status="queued",
            progress=0,
            message="Manual retry queued",
            error=None,
            error_code=None,
            next_run_at=_now(),
        )
        self._enqueue_task(task_id, priority=task.get("priority", 100))
        return True

    # -----------------------------
    # Queue worker internals
    # -----------------------------
    def _enqueue_task(self, task_id: str, *, priority: int) -> None:
        self._queue.put((int(priority), _now(), task_id))
        self._log_event(task_id, event_type="enqueued", status="queued", message="Task enqueued")

    def _schedule_retry(self, task_id: str, delay: int, priority: int) -> None:
        def _enqueue():
            self._timers.pop(task_id, None)
            task = self.get_task(task_id)
            if not task or task["status"] != "retrying":
                return
            self.update_task(task_id, status="queued", message="Retry queued", next_run_at=_now())
            self._enqueue_task(task_id, priority=priority)

        timer = threading.Timer(delay, _enqueue)
        timer.daemon = True
        self._timers[task_id] = timer
        timer.start()

    def _worker_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                _, _, task_id = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._run_task(task_id)
            finally:
                self._queue.task_done()

    def _run_task(self, task_id: str) -> None:
        runner = self._runners.get(task_id)
        if not runner:
            task = self.get_task(task_id)
            if task and task["status"] not in TASK_TERMINAL_STATUSES:
                self.finish_task(
                    task_id,
                    status="error",
                    message="Task handler missing",
                    error="Task handler missing",
                    error_code="ERR_TASK_HANDLER_MISSING",
                )
            return

        task = self.get_task(task_id)
        if not task:
            self._cleanup_runtime(task_id)
            return
        if task["status"] in TASK_TERMINAL_STATUSES or task["status"] == "paused":
            return

        controls = self._controls.get(task_id)
        if not controls:
            cancel_event = threading.Event()
            pause_event = threading.Event()
            self._controls[task_id] = {"cancel": cancel_event, "pause": pause_event}
            controls = self._controls[task_id]

        cancel_event = controls["cancel"]
        pause_event = controls["pause"]
        attempt = int(task.get("attempt", 0) or 0) + 1
        max_retries = int(task.get("max_retries", 0) or 0)

        if cancel_event.is_set():
            self.finish_task(
                task_id,
                status="stopped",
                message="Task cancelled before execution",
                error_code="ERR_TASK_CANCELLED",
            )
            return

        self.update_task(
            task_id,
            status="running",
            message=f"Running (attempt {attempt}/{max_retries + 1})",
            started_at=task.get("started_at") or _now(),
            attempt=attempt,
            next_run_at=None,
        )

        try:
            runner(task_id, cancel_event, pause_event)
            latest = self.get_task(task_id)
            if latest and latest["status"] == "running":
                self.finish_task(task_id, status="completed", message="Task completed")
        except Exception as exc:
            if str(exc) == "Operation cancelled by user" or cancel_event.is_set():
                self.finish_task(
                    task_id,
                    status="stopped",
                    message="Task cancelled",
                    error_code="ERR_TASK_CANCELLED",
                )
                return

            if attempt <= max_retries:
                delay = self.retry_backoff_seconds * attempt
                self.update_task(
                    task_id,
                    status="retrying",
                    message=f"Attempt {attempt} failed, retry in {delay}s",
                    error=str(exc),
                    error_code="ERR_RETRY_SCHEDULED",
                    next_run_at=_now() + delay,
                )
                priority = int(task.get("priority", 100) or 100)
                self._schedule_retry(task_id, delay, priority)
                return

            self.finish_task(
                task_id,
                status="error",
                message=str(exc),
                error=str(exc),
                error_code="ERR_INTERNAL",
            )

    def make_progress_callback(self, task_id: str, cancel_event: threading.Event, pause_event: threading.Event):
        def progress_callback(current, total, message):
            if cancel_event.is_set():
                raise Exception("Operation cancelled by user")
            self.wait_if_paused(task_id, pause_event, cancel_event)
            if total > 0:
                progress = int((current / total) * 100)
                self.update_task(task_id, progress=progress, message=f"{message} ({current}/{total})")

        return progress_callback

    def wait_if_paused(self, task_id: str, pause_event: threading.Event, cancel_event: threading.Event) -> None:
        while pause_event.is_set():
            current = self.get_task(task_id) or {}
            if current.get("status") != "paused":
                self.update_task(task_id, status="paused", message="Task paused")
            time.sleep(0.2)
            if cancel_event.is_set():
                raise Exception("Operation cancelled by user")

        current = self.get_task(task_id) or {}
        if current.get("status") == "paused":
            self.update_task(task_id, status="running", message="Task resumed")

    def _cleanup_runtime(self, task_id: str) -> None:
        self._controls.pop(task_id, None)
        self._runners.pop(task_id, None)
        timer = self._timers.pop(task_id, None)
        if timer:
            try:
                timer.cancel()
            except Exception:
                pass

    def prune_task_progress(self, limit: int = TASK_RETENTION_LIMIT) -> None:
        rows = self._execute(
            """
            SELECT id FROM tasks
            WHERE status IN ('completed', 'error', 'stopped', 'cancelled')
            ORDER BY finished_at DESC
            """,
            fetch="all",
        ) or []
        if len(rows) <= limit:
            return

        obsolete = rows[limit:]
        for row in obsolete:
            task_id = row["id"]
            self._execute("DELETE FROM task_events WHERE task_id = ?", (task_id,))
            self._execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> dict:
        result = _from_json(row["result_json"])
        return {
            "task_id": row["id"],
            "status": row["status"],
            "progress": row["progress"],
            "message": row["message"],
            "result": result,
            "error": row["error"],
            "error_code": row["error_code"],
            "attempt": row["attempt"],
            "max_retries": row["max_retries"],
            "priority": row["priority"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "next_run_at": row["next_run_at"],
        }
