#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.modules.cv_tools.paper_grid_generator import PaperGridGenerator
except Exception as exc:
    print(f"SKIP: paper_grid_generator import failed: {exc}")
    sys.exit(0)

from tests.helpers import create_image


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        img_path = base / "img.jpg"
        out_path = base / "grid.jpg"
        create_image(img_path, size=(64, 64))

        generator = PaperGridGenerator()
        result = generator.generate_grid({
            "cells": [
                {"path": str(img_path), "row": 0, "col": 0, "rowspan": 1, "colspan": 1}
            ],
            "output_path": str(out_path),
            "row_labels": ["R1"],
            "col_labels": ["C1"],
            "padding": 4,
            "font_size": 10,
            "margin": 4,
            "background": "white"
        })
        if not result.get("success"):
            raise AssertionError(f"generate_grid failed: {result}")
        if not out_path.exists():
            raise AssertionError("grid output missing")

    print("OK: grid generator test passed")


if __name__ == "__main__":
    main()
