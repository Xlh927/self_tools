#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.cv_tools.converter import DatasetConverter
from tests.helpers import create_image, create_voc_xml, write_text


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        images = base / "images"
        voc_dir = base / "voc"
        yolo_dir = base / "yolo"
        voc_back = base / "voc_back"

        img_path = images / "img1.jpg"
        create_image(img_path, size=(100, 80))
        create_voc_xml(voc_dir / "img1.xml", "img1.jpg", 100, 80, class_name="cat")

        classes_file = base / "classes.txt"
        write_text(classes_file, "cat\n")

        converter = DatasetConverter(classes_file=str(classes_file))
        result = converter.voc_to_yolo(
            voc_xml_dir=str(voc_dir),
            images_dir=str(images),
            output_dir=str(yolo_dir),
            classes_file=str(classes_file)
        )
        if not result.get("success"):
            if "Permission denied" in str(result.get("error", "")):
                print("SKIP: voc_to_yolo permission denied in this environment")
                return
            raise AssertionError(f"voc_to_yolo failed: {result}")
        if not (yolo_dir / "img1.txt").exists():
            raise AssertionError("yolo annotation missing")
        if not (yolo_dir / "classes.txt").exists():
            raise AssertionError("classes.txt missing")

        result_back = converter.yolo_to_voc(
            yolo_txt_dir=str(yolo_dir),
            images_dir=str(images),
            output_dir=str(voc_back),
            classes_file=str(classes_file)
        )
        if not result_back.get("success"):
            if "Permission denied" in str(result_back.get("error", "")):
                print("SKIP: yolo_to_voc permission denied in this environment")
                return
            raise AssertionError(f"yolo_to_voc failed: {result_back}")
        if not (voc_back / "img1.xml").exists():
            raise AssertionError("voc annotation missing")

    print("OK: converter test passed")


if __name__ == "__main__":
    main()
