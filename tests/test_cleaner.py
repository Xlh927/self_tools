#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.cv_tools.dataset_cleaner import DatasetCleaner
from tests.helpers import create_image, create_yolo_label, write_text


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        images_dir = base / "images"
        labels_dir = base / "labels"
        out_dir = base / "bg"

        create_image(images_dir / "a.jpg")
        create_image(images_dir / "b.jpg")
        create_image(images_dir / "c.jpg")
        create_yolo_label(labels_dir / "a.txt", class_id=0)
        write_text(labels_dir / "c.txt", "")

        cleaner = DatasetCleaner()
        dry = cleaner.clean(str(images_dir), str(labels_dir), str(out_dir), dry_run=True)
        if not dry.get("success"):
            raise AssertionError(f"cleaner dry_run failed: {dry}")
        if dry.get("unlabeled_count") != 2:
            raise AssertionError("unlabeled_count should include missing and empty labels")

        result = cleaner.clean(str(images_dir), str(labels_dir), str(out_dir), dry_run=False)
        if not result.get("success"):
            raise AssertionError(f"cleaner failed: {result}")
        if not (out_dir / "b.jpg").exists():
            raise AssertionError("unlabeled image not moved")
        if not (out_dir / "c.jpg").exists():
            raise AssertionError("empty-label image not moved")
        if not (out_dir / "c.txt").exists():
            raise AssertionError("empty label not moved")

    print("OK: cleaner test passed")


if __name__ == "__main__":
    main()
