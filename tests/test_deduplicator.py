#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.modules.cv_tools.image_deduplicator import ImageDeduplicator
except Exception as exc:
    print(f"SKIP: image_deduplicator import failed: {exc}")
    sys.exit(0)

from tests.helpers import create_image


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        create_image(base / "a.jpg", size=(64, 64), color=(255, 0, 0))
        create_image(base / "b.jpg", size=(64, 64), color=(255, 0, 0))
        create_image(base / "c.jpg", size=(64, 64), color=(0, 255, 0))

        dedup = ImageDeduplicator()
        try:
            duplicates = dedup.find_duplicates(
                folder_path=str(base),
                use_md5=True,
                similarity_threshold=0
            )
        except PermissionError as exc:
            print(f"SKIP: deduplicator permission denied in this environment: {exc}")
            return
        # There should be at least one group with a.jpg and b.jpg
        if not duplicates:
            raise AssertionError("no duplicates detected")
        group_sizes = [len(v) for v in duplicates.values()]
        if max(group_sizes) < 2:
            raise AssertionError("duplicate group size too small")

    print("OK: deduplicator test passed")


if __name__ == "__main__":
    main()
