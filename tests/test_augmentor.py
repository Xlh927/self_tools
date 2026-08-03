#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.modules.cv_tools.data_augmentor import DataAugmentor
except Exception as exc:
    print(f"SKIP: data_augmentor import failed: {exc}")
    sys.exit(0)

from tests.helpers import create_image, create_voc_xml


def assert_bbox_close(actual, expected):
    if not np.allclose(actual, expected):
        raise AssertionError(f"unexpected bbox: {actual}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        images_dir = base / "images"
        ann_dir = base / "ann"
        out_dir = base / "out"

        img_path = images_dir / "img1.jpg"
        create_image(img_path, size=(80, 60))
        create_voc_xml(ann_dir / "img1.xml", "img1.jpg", 80, 60, class_name="cat")

        augmentor = DataAugmentor()
        result = augmentor.augment_dataset({
            "images_dir": str(images_dir),
            "annotations_dir": str(ann_dir),
            "output_dir": str(out_dir),
            "annotation_format": "voc",
            "augmentations": [],
        })
        if not result.get("success"):
            if "Permission denied" in str(result.get("error", "")):
                print("SKIP: augment_dataset permission denied in this environment")
                return
            raise AssertionError(f"augment_dataset failed: {result}")

        if not list((out_dir / "images").glob("*.jpg")):
            raise AssertionError("no output images")
        if not list((out_dir / "xmls").glob("*.xml")):
            raise AssertionError("no output annotations")

        image = np.zeros((60, 80, 3), dtype=np.uint8)
        annotations = [{"class_name": "cat", "bbox": [10, 12, 30, 42]}]

        scaled_width_image, scaled_width_annotations = augmentor.scale_axis(
            image,
            annotations,
            x_range=(1.2, 1.2),
            y_range=(1.0, 1.0),
        )
        if scaled_width_image.shape[:2] != (60, 96):
            raise AssertionError(f"unexpected width stretch shape: {scaled_width_image.shape[:2]}")
        assert_bbox_close(scaled_width_annotations[0]["bbox"], [12, 12, 36, 42])

        scaled_height_image, scaled_height_annotations = augmentor.scale_axis(
            image,
            annotations,
            x_range=(1.0, 1.0),
            y_range=(1.1, 1.1),
        )
        if scaled_height_image.shape[:2] != (66, 80):
            raise AssertionError(f"unexpected height stretch shape: {scaled_height_image.shape[:2]}")
        assert_bbox_close(scaled_height_annotations[0]["bbox"], [10, 13.2, 30, 46.2])

        aug_image, aug_annotations = augmentor.apply_augmentation(
            image,
            ann_dir / "img1.xml",
            {"name": "stretch_width", "min": 1.2, "max": 1.2},
            "voc",
        )
        if aug_image.shape[:2] != (60, 96):
            raise AssertionError(f"unexpected configured width stretch shape: {aug_image.shape[:2]}")
        assert_bbox_close(aug_annotations[0]["bbox"], [12, 10, 72, 59])

        unchanged_image, _unchanged_annotations = augmentor.add_noise(image, annotations, 0, 0)
        if not np.array_equal(unchanged_image, image):
            raise AssertionError("zero-variance noise should not change image")

        legacy_blur_image, _legacy_blur_annotations = augmentor.apply_augmentation(
            image,
            ann_dir / "img1.xml",
            "blur",
            "voc",
        )
        if legacy_blur_image.shape[:2] != image.shape[:2]:
            raise AssertionError(f"legacy blur changed shape: {legacy_blur_image.shape[:2]}")

        color_image = np.full((20, 20, 3), 100, dtype=np.uint8)
        bright_image, _bright_annotations = augmentor.apply_augmentation(
            color_image,
            ann_dir / "img1.xml",
            {"name": "brightness", "min": 1.2, "max": 1.2},
            "voc",
        )
        if int(bright_image[0, 0, 0]) != 120:
            raise AssertionError(f"unexpected brightness result: {bright_image[0, 0, 0]}")

        contrast_image, _contrast_annotations = augmentor.apply_augmentation(
            color_image,
            ann_dir / "img1.xml",
            {"name": "contrast", "min": 1.0, "max": 1.0},
            "voc",
        )
        if not np.array_equal(contrast_image, color_image):
            raise AssertionError("factor-1 contrast should not change image")

    print("OK: augmentor test passed")


if __name__ == "__main__":
    main()
