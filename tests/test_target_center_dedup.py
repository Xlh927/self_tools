#!/usr/bin/env python3
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.modules.cv_tools.dataset_generator import Annotation, DatasetGenerator


class TargetCenterDedupTest(unittest.TestCase):
    def setUp(self):
        self.generator = DatasetGenerator()
        self.a = Annotation(0, 'a', (1490, 20, 1510, 40))
        self.b = Annotation(1, 'b', (1500, 60, 1520, 80))

    def windows(self, annotations, minvis=1):
        return self.generator._generate_target_center_windows(
            annotations, 3000, 1000, 1000, 400, minvis)

    def test_dense_targets_share_three_views(self):
        single = self.windows([self.a])
        dense = self.windows([self.a, self.b])
        self.assertEqual(len(single), 3)
        self.assertEqual(dense, single)
        for window in dense:
            labels = self.generator._annotations_for_window([self.a, self.b], window, 1)
            self.assertEqual({label.class_name for label in labels}, {'a', 'b'})

    def test_separate_targets_keep_their_views(self):
        far = Annotation(1, 'far', (2090, 60, 2110, 80))
        self.assertEqual(len(self.windows([self.a, far])), 6)

    def test_newly_visible_target_prevents_suppression(self):
        extra = Annotation(2, 'extra', (1605, 20, 1608, 40))
        windows = self.windows([self.a, self.b, extra])
        self.assertIn((610, 0, 1610, 1000), windows)
        for ann in (self.a, self.b, extra):
            self.assertTrue(any(self.generator.calculate_overlap(ann, window) == 1 for window in windows))

    def test_minvis_zero_and_edges(self):
        for minvis in (0, 0.3, 1):
            windows = self.windows([self.a, self.b], minvis)
            self.assertEqual(len(windows), len(set(windows)))
            for ann in (self.a, self.b):
                self.assertTrue(any(self.generator.calculate_overlap(ann, w) >= minvis for w in windows))
        edge = Annotation(0, 'edge', (5, 5, 20, 20))
        self.assertEqual(self.windows([edge, edge]), [(0, 0, 1000, 1000)])
        self.assertEqual(self.windows([]), [])

    def test_voc_and_yolo_files_keep_both_labels(self):
        for fmt in ('voc', 'yolo'):
            with self.subTest(format=fmt), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                images = root / 'images'
                labels = root / 'labels'
                images.mkdir()
                labels.mkdir()
                Image.new('RGB', (3000, 1000)).save(images / 'dense.png')
                if fmt == 'voc':
                    annotation = ET.Element('annotation')
                    ET.SubElement(annotation, 'filename').text = 'dense.png'
                    size = ET.SubElement(annotation, 'size')
                    ET.SubElement(size, 'width').text = '3000'
                    ET.SubElement(size, 'height').text = '1000'
                    ET.SubElement(size, 'depth').text = '3'
                    for ann in (self.a, self.b):
                        obj = ET.SubElement(annotation, 'object')
                        ET.SubElement(obj, 'name').text = ann.class_name
                        bbox = ET.SubElement(obj, 'bndbox')
                        for key, value in zip(('xmin', 'ymin', 'xmax', 'ymax'), ann.bbox):
                            ET.SubElement(bbox, key).text = str(value)
                    ET.ElementTree(annotation).write(labels / 'dense.xml')
                else:
                    (labels / 'classes.txt').write_text('a\nb\n')
                    (labels / 'dense.txt').write_text('0 0.5 0.03 0.006666666667 0.02\n1 0.503333333333 0.07 0.006666666667 0.02\n')
                result = self.generator.generate_dataset({
                    'annotation_format': fmt, 'images_dir': str(images),
                    'annotations_dir': str(labels), 'output_dir': str(root / 'out'),
                    'adaptive_window': True, 'labeled_crop_mode': 'target_center',
                    'overlap_ratio': 0.6, 'minvis': 1,
                    'preserve_annotation_format': True,
                })
                self.assertTrue(result.get('success'), result)
                self.assertEqual(len(list((root / 'out/images').glob('*.png'))), 3)
                suffix = '*.xml' if fmt == 'voc' else '*.txt'
                outputs = list((root / 'out/labels').glob(suffix))
                self.assertEqual(len(outputs), 3)
                for output in outputs:
                    count = len(ET.parse(output).findall('object')) if fmt == 'voc' else len(output.read_text().splitlines())
                    self.assertEqual(count, 2)


if __name__ == '__main__':
    unittest.main()
