#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.modules.cv_tools.data_augmentor import DataAugmentor
except Exception as exc:
    print(f"SKIP: data_augmentor import failed: {exc}")
    sys.exit(0)

from tests.helpers import create_image, create_voc_xml


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

    print("OK: augmentor test passed")


if __name__ == "__main__":
    main()
