#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.cv_tools.label_modifier import LabelModifier
from tests.helpers import write_text


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        labels_dir = base / "labels"
        out_dir = base / "out"

        write_text(labels_dir / "a.txt", "0 0.5 0.5 0.5 0.5\n1 0.1 0.1 0.2 0.2\n")
        write_text(labels_dir / "b.txt", "1 0.2 0.2 0.3 0.3\n")

        modifier = LabelModifier()
        scan = modifier.scan_classes(str(labels_dir))
        if not scan.get("success"):
            raise AssertionError(f"scan_classes failed: {scan}")

        result = modifier.modify_labels(
            label_dir=str(labels_dir),
            class_mapping={"0": 2, "1": 3},
            overwrite=False,
            output_dir=str(out_dir),
        )
        if not result.get("success"):
            raise AssertionError(f"modify_labels failed: {result}")
        if not (out_dir / "a.txt").exists():
            raise AssertionError("modified file missing")

        content = (out_dir / "a.txt").read_text(encoding="utf-8")
        if not content.startswith("2 "):
            raise AssertionError("class mapping not applied")

    print("OK: label_modifier test passed")


if __name__ == "__main__":
    main()
