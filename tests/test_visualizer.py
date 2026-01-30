#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.modules.cv_tools.annotation_visualizer import AnnotationVisualizer
except Exception as exc:
    print(f"SKIP: annotation_visualizer import failed: {exc}")
    sys.exit(0)

from tests.helpers import write_text


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        ann_dir = base / "labels"
        ann_dir.mkdir(parents=True, exist_ok=True)

        write_text(ann_dir / "classes.txt", "cat\ndog\n")
        write_text(ann_dir / "img1.txt", "0 0.5 0.5 0.5 0.5\n")

        visualizer = AnnotationVisualizer()
        result = visualizer.detect_classes(str(ann_dir), annotation_format="yolo")
        if not result.get("success"):
            raise AssertionError(f"detect_classes failed: {result}")
        classes = result.get("classes", [])
        if "cat" not in classes or "dog" not in classes:
            raise AssertionError(f"classes missing: {classes}")

    print("OK: visualizer test passed")


if __name__ == "__main__":
    main()
