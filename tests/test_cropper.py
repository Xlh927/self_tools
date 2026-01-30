#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.cv_tools.image_cropper import ImageCropper
from tests.helpers import create_image


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        img_path = base / "img.jpg"
        out_dir = base / "out"
        create_image(img_path, size=(100, 80))

        cropper = ImageCropper()
        result = cropper.crop_image_sliding_window(
            image_path=str(img_path),
            output_dir=str(out_dir),
            window_width=50,
            window_height=40,
            overlap_x=0,
            overlap_y=0,
        )
        if not result.get("success"):
            raise AssertionError(f"cropper failed: {result}")
        if result.get("crops_count", 0) == 0:
            raise AssertionError("no crops produced")
        if not any(out_dir.glob("*.jpg")):
            raise AssertionError("crop files missing")

    print("OK: cropper test passed")


if __name__ == "__main__":
    main()
