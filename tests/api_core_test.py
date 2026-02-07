#!/usr/bin/env python3
import os
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SELF_TOOLS_TASK_DB", str(PROJECT_ROOT / "tmp" / "test_tasks.db"))

from backend.app import app
from tests.helpers import create_image, create_voc_xml, create_yolo_label, write_text


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def wait_for_task(client, task_id, timeout=10.0):
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        resp = client.get(f"/api/progress/{task_id}")
        if resp.status_code == 200:
            data = resp.get_json()
            last_status = data.get("status")
            if last_status in {"completed", "error", "stopped", "cancelled"}:
                return data
        time.sleep(0.1)
    raise AssertionError(f"task timeout: {task_id}, last_status={last_status}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        voc_dir = base / "voc"
        labels_dir = base / "labels"
        source_dir = base / "source"
        ref_dir = base / "ref"
        out_dir = base / "out"

        create_voc_xml(voc_dir / "img1.xml", "img1.jpg", 100, 80, class_name="cat")
        create_voc_xml(voc_dir / "img2.xml", "img2.jpg", 120, 90, class_name="dog")
        create_yolo_label(labels_dir / "img1.txt", class_id=0)

        create_image(source_dir / "a.jpg")
        create_image(source_dir / "b.png")
        write_text(ref_dir / "a.txt", "ref")

        client = app.test_client()

        # Basic page route
        resp = client.get("/")
        assert_true(resp.status_code == 200, f"GET / failed: {resp.status_code}")
        assert_true("Self Tools" in resp.get_data(as_text=True), "landing page content mismatch")

        # Missing task id
        resp = client.get("/api/progress/not-exist-task")
        data = resp.get_json()
        assert_true(resp.status_code == 404, "missing task should return 404")
        assert_true(data.get("error_code") == "ERR_TASK_NOT_FOUND", f"unexpected error code: {data}")

        # Validation error on required field
        resp = client.post("/api/scan-voc-classes", json={})
        data = resp.get_json()
        assert_true(resp.status_code == 400, "missing annotations_dir should return 400")
        assert_true(data.get("error_code") == "ERR_MISSING_FIELD", f"unexpected error payload: {data}")

        # Core sync API: scan VOC classes
        resp = client.post("/api/scan-voc-classes", json={"annotations_dir": str(voc_dir)})
        data = resp.get_json()
        assert_true(resp.status_code == 200 and data.get("success"), f"scan voc classes failed: {data}")
        class_names = {item["name"] for item in data.get("classes", [])}
        assert_true(class_names == {"cat", "dog"}, f"unexpected voc classes: {class_names}")

        # Core sync API: scan YOLO classes
        resp = client.post("/api/scan-yolo-classes", json={"label_dir": str(labels_dir)})
        data = resp.get_json()
        assert_true(resp.status_code == 200 and data.get("success"), f"scan yolo classes failed: {data}")
        assert_true(data.get("classes") == [{"id": 0, "count": 1}], f"unexpected yolo classes: {data}")

        # Core async API: match + progress lifecycle
        resp = client.post(
            "/api/match",
            json={
                "source_dir": str(source_dir),
                "reference_dir": str(ref_dir),
                "output_dir": str(out_dir),
                "copy_intersection": True,
                "copy_difference": True,
                "dry_run": False,
            },
        )
        data = resp.get_json()
        assert_true(resp.status_code in (200, 202) and data.get("success"), f"match start failed: {data}")
        task_id = data.get("task_id")
        assert_true(bool(task_id), "match task_id missing")

        task_result = wait_for_task(client, task_id, timeout=10.0)
        assert_true(task_result.get("status") == "completed", f"task not completed: {task_result}")
        result_payload = task_result.get("result", {})
        assert_true(result_payload.get("success"), f"match result failed: {result_payload}")
        assert_true(result_payload.get("matched_count") == 1, f"unexpected matched_count: {result_payload}")
        assert_true(result_payload.get("unmatched_count") == 1, f"unexpected unmatched_count: {result_payload}")
        assert_true((out_dir / "intersection" / "a.jpg").exists(), "intersection output missing")
        assert_true((out_dir / "difference" / "b.png").exists(), "difference output missing")

        # Task list + history endpoints
        list_resp = client.get("/api/tasks?limit=20")
        list_data = list_resp.get_json()
        assert_true(list_resp.status_code == 200 and list_data.get("success"), f"task list failed: {list_data}")
        task_ids = {item.get("task_id") for item in list_data.get("tasks", [])}
        assert_true(task_id in task_ids, f"task id not found in list: {task_ids}")

        history_resp = client.get(f"/api/task/{task_id}/history?limit=20")
        history_data = history_resp.get_json()
        assert_true(history_resp.status_code == 200 and history_data.get("success"), f"task history failed: {history_data}")
        events = history_data.get("events", [])
        assert_true(len(events) > 0, "task history events missing")

    print("OK: core API tests passed")


if __name__ == "__main__":
    main()
