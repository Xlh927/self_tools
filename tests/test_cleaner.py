#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.cv_tools.dataset_cleaner import DatasetCleaner
from tests.helpers import create_image, create_yolo_label


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        images_dir = base / "images"
        labels_dir = base / "labels"
        out_dir = base / "bg"

        create_image(images_dir / "a.jpg")
        create_image(images_dir / "b.jpg")
        create_yolo_label(labels_dir / "a.txt", class_id=0)

        cleaner = DatasetCleaner()
        dry = cleaner.clean(str(images_dir), str(labels_dir), str(out_dir), dry_run=True)
        if not dry.get("success"):
            raise AssertionError(f"cleaner dry_run failed: {dry}")
        if dry.get("unlabeled_count") != 1:
            raise AssertionError("unlabeled_count should be 1")

        result = cleaner.clean(str(images_dir), str(labels_dir), str(out_dir), dry_run=False)
        if not result.get("success"):
            raise AssertionError(f"cleaner failed: {result}")
        if not (out_dir / "b.jpg").exists():
            raise AssertionError("unlabeled image not moved")

    print("OK: cleaner test passed")


if __name__ == "__main__":
    main()
