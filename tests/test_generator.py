#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.cv_tools.dataset_generator import DatasetGenerator
from tests.helpers import create_image, create_yolo_label, write_text


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        images_dir = base / "images"
        labels_dir = base / "labels"
        out_dir = base / "out"

        img_path = images_dir / "img1.jpg"
        create_image(img_path, size=(100, 100))
        create_yolo_label(labels_dir / "img1.txt", class_id=0)
        write_text(labels_dir / "classes.txt", "obj\n")

        generator = DatasetGenerator()
        result = generator.generate_dataset({
            "annotation_format": "yolo",
            "images_dir": str(images_dir),
            "annotations_dir": str(labels_dir),
            "output_dir": str(out_dir),
            "classes": [0],
            "window_width": 100,
            "window_height": 100,
            "stride_x": 100,
            "stride_y": 100,
            "overlap_threshold": 0,
        })
        if not result.get("success"):
            raise AssertionError(f"generator failed: {result}")

        out_images = list((out_dir / "images").glob("*.jpg"))
        out_labels = list((out_dir / "labels").glob("*.txt"))
        if not out_images:
            raise AssertionError("no generated images")
        if not out_labels:
            raise AssertionError("no generated labels")
        if not (out_dir / "classes.txt").exists():
            raise AssertionError("classes.txt missing")

    print("OK: generator test passed")


if __name__ == "__main__":
    main()
