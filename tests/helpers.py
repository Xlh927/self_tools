#!/usr/bin/env python3
import os
from pathlib import Path
from PIL import Image


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_image(path: Path, size=(100, 100), color=(255, 0, 0)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color)
    img.save(path)


def create_voc_xml(path: Path, filename: str, width: int, height: int, class_name: str = "obj") -> None:
    xml = f"""<annotation>
  <folder>images</folder>
  <filename>{filename}</filename>
  <size>
    <width>{width}</width>
    <height>{height}</height>
    <depth>3</depth>
  </size>
  <object>
    <name>{class_name}</name>
    <bndbox>
      <xmin>10</xmin>
      <ymin>10</ymin>
      <xmax>{min(width - 1, 60)}</xmax>
      <ymax>{min(height - 1, 60)}</ymax>
    </bndbox>
  </object>
</annotation>
"""
    write_text(path, xml)


def create_yolo_label(path: Path, class_id: int = 0) -> None:
    write_text(path, f"{class_id} 0.5 0.5 0.5 0.5\n")
