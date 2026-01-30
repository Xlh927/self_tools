#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path

# Allow imports from project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.cv_tools.image_matcher import ImageMatcher
from backend.modules.cv_tools.dataset_splitter import DatasetSplitter


def write_file(path: Path, content: bytes = b""):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


def test_image_matcher():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source_dir = base / "source"
        ref_dir = base / "ref"
        out_dir = base / "out"

        write_file(source_dir / "a.jpg")
        write_file(source_dir / "b.png")
        write_file(ref_dir / "a.txt")

        matcher = ImageMatcher()
        result = matcher.match_and_copy(
            source_dir=str(source_dir),
            reference_dir=str(ref_dir),
            output_dir=str(out_dir),
            copy_intersection=True,
            copy_difference=True,
            dry_run=False,
        )

        if not result.get("success"):
            raise AssertionError(f"matcher failed: {result}")

        intersection = out_dir / "intersection" / "a.jpg"
        difference = out_dir / "difference" / "b.png"

        if not intersection.exists():
            raise AssertionError("intersection file missing")
        if not difference.exists():
            raise AssertionError("difference file missing")


def test_dataset_splitter():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        images_dir = base / "images"
        labels_dir = base / "labels"
        out_dir = base / "split"

        # Create 10 labeled images + labels
        for i in range(10):
            write_file(images_dir / f"img_{i}.jpg")
            write_file(labels_dir / f"img_{i}.txt", b"0 0.5 0.5 1.0 1.0\n")

        splitter = DatasetSplitter()
        result = splitter.split_dataset({
            "format": "yolo",
            "images_dir": str(images_dir),
            "annotations_dir": str(labels_dir),
            "output_dir": str(out_dir),
            "train_ratio": 60,
            "val_ratio": 20,
            "test_ratio": 20,
            "use_background": False,
            "random_seed": 123,
        })

        if not result.get("success"):
            raise AssertionError(f"splitter failed: {result}")

        if result.get("train_count") != 6:
            raise AssertionError(f"train_count unexpected: {result.get('train_count')}")
        if result.get("val_count") != 2:
            raise AssertionError(f"val_count unexpected: {result.get('val_count')}")
        if result.get("test_count") != 2:
            raise AssertionError(f"test_count unexpected: {result.get('test_count')}")


def main():
    test_image_matcher()
    test_dataset_splitter()
    print("OK: smoke tests passed")


if __name__ == "__main__":
    main()
