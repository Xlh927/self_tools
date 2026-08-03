#!/usr/bin/env python3
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.cv_tools.dataset_generator import DatasetGenerator
from tests.helpers import create_image, create_voc_xml, create_yolo_label, write_text


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

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        images_dir = base / "images"
        labels_dir = base / "labels"
        out_dir = base / "out"

        img_path = images_dir / "wide.png"
        create_image(img_path, size=(300, 100))
        create_yolo_label(labels_dir / "wide.txt", class_id=0)
        write_text(labels_dir / "classes.txt", "obj\n")

        generator = DatasetGenerator()
        result = generator.generate_dataset({
            "annotation_format": "yolo",
            "images_dir": str(images_dir),
            "annotations_dir": str(labels_dir),
            "output_dir": str(out_dir),
            "classes": [0],
            "adaptive_window": True,
            "labeled_crop_mode": "sliding",
            "overlap_ratio": 0.3,
            "minvis": 0.3,
            "preserve_annotation_format": True,
        })
        if not result.get("success"):
            raise AssertionError(f"adaptive yolo generator failed: {result}")

        out_images = sorted((out_dir / "images").glob("*.png"))
        out_labels = sorted((out_dir / "labels").glob("*.txt"))
        if len(out_images) != 4:
            raise AssertionError(f"ordinary sliding should keep background crops, got {len(out_images)}")
        if len(out_labels) != len(out_images):
            raise AssertionError("ordinary sliding should write one label file per crop")
        if not any(label.read_text(encoding="utf-8").strip() == "" for label in out_labels):
            raise AssertionError("ordinary sliding should keep empty background labels")
        with Image.open(out_images[0]) as crop:
            if crop.size != (100, 100):
                raise AssertionError(f"adaptive crop should use image height as square side, got {crop.size}")

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        images_dir = base / "images"
        labels_dir = base / "labels"
        out_dir = base / "out"

        img_path = images_dir / "wide.jpg"
        create_image(img_path, size=(300, 100))
        create_voc_xml(labels_dir / "wide.xml", filename="wide.jpg", width=300, height=100)

        generator = DatasetGenerator()
        result = generator.generate_dataset({
            "annotation_format": "voc",
            "images_dir": str(images_dir),
            "annotations_dir": str(labels_dir),
            "output_dir": str(out_dir),
            "adaptive_window": True,
            "labeled_crop_mode": "target_center",
            "overlap_ratio": 0.3,
            "minvis": 0.3,
            "preserve_annotation_format": True,
        })
        if not result.get("success"):
            raise AssertionError(f"adaptive voc generator failed: {result}")

        out_images = sorted((out_dir / "images").glob("*.jpg"))
        out_labels = sorted((out_dir / "labels").glob("*.xml"))
        if not out_images:
            raise AssertionError("target center mode produced no images")
        if len(out_labels) != len(out_images):
            raise AssertionError("target center mode should write one VOC file per crop")
        with Image.open(out_images[0]) as crop:
            if crop.size != (100, 100):
                raise AssertionError(f"VOC adaptive crop should be square, got {crop.size}")
        root = ET.parse(out_labels[0]).getroot()
        if root.find("object") is None:
            raise AssertionError("target center VOC crop should contain an object")

    print("OK: generator test passed")


if __name__ == "__main__":
    main()
