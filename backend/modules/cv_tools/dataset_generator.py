"""
Annotation-Aware Dataset Generator
Generates small datasets from large annotated images using sliding windows
"""

import os
import json
import concurrent.futures
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from PIL import Image
from dataclasses import dataclass

try:
    from parallelism_config import get_executor_plan
except Exception:  # pragma: no cover - import path differs by runtime entrypoint
    from backend.parallelism_config import get_executor_plan

# Remove PIL image size limit for large images
Image.MAX_IMAGE_PIXELS = None


@dataclass
class Annotation:
    """Represents a single annotation"""
    class_id: int
    class_name: str
    bbox: Tuple[float, float, float, float]  # xmin, ymin, xmax, ymax
    polygon: Optional[List[Tuple[float, float]]] = None
    
    @property
    def area(self) -> float:
        """Calculate annotation area"""
        if self.polygon:
            # Use shoelace formula for polygon area
            return self._polygon_area()
        else:
            # Bounding box area
            return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])
    
    def _polygon_area(self) -> float:
        """Calculate polygon area using shoelace formula"""
        if not self.polygon or len(self.polygon) < 3:
            return 0.0
        
        area = 0.0
        n = len(self.polygon)
        for i in range(n):
            j = (i + 1) % n
            area += self.polygon[i][0] * self.polygon[j][1]
            area -= self.polygon[j][0] * self.polygon[i][1]
        return abs(area) / 2.0


class AnnotationParser:
    """Parse annotations from different formats"""
    
    @staticmethod
    def parse_voc(xml_path: str, class_filter: Optional[List[str]] = None) -> Tuple[List[Annotation], Tuple[int, int]]:
        """
        Parse VOC XML format
        
        Returns:
            (annotations, (img_width, img_height))
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Get image size
        size = root.find('size')
        img_width = int(size.find('width').text)
        img_height = int(size.find('height').text)
        
        annotations = []
        for obj in root.findall('object'):
            class_name = obj.find('name').text
            
            # Filter by class if specified
            if class_filter and class_name not in class_filter:
                continue
            
            # Get bounding box
            bbox_elem = obj.find('bndbox')
            xmin = float(bbox_elem.find('xmin').text)
            ymin = float(bbox_elem.find('ymin').text)
            xmax = float(bbox_elem.find('xmax').text)
            ymax = float(bbox_elem.find('ymax').text)
            
            # Check for polygon (if exists)
            polygon = None
            polygon_elem = obj.find('polygon')
            if polygon_elem is not None:
                polygon = []
                for pt in polygon_elem.findall('pt'):
                    x = float(pt.find('x').text)
                    y = float(pt.find('y').text)
                    polygon.append((x, y))
            
            annotations.append(Annotation(
                class_id=-1,  # Will be assigned later
                class_name=class_name,
                bbox=(xmin, ymin, xmax, ymax),
                polygon=polygon
            ))
        
        return annotations, (img_width, img_height)
    
    @staticmethod
    def parse_yolo(txt_path: str, img_width: int, img_height: int, 
                   classes: List[str], class_filter: Optional[List[int]] = None) -> List[Annotation]:
        """
        Parse YOLO TXT format
        
        Args:
            txt_path: Path to YOLO txt file
            img_width: Image width
            img_height: Image height
            classes: List of class names
            class_filter: List of class indices to keep
        """
        annotations = []
        
        with open(txt_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                
                class_id = int(parts[0])
                
                # Filter by class if specified
                if class_filter and class_id not in class_filter:
                    continue
                
                # Parse YOLO format (normalized center x, y, width, height)
                x_center = float(parts[1]) * img_width
                y_center = float(parts[2]) * img_height
                width = float(parts[3]) * img_width
                height = float(parts[4]) * img_height
                
                # Convert to bbox
                xmin = x_center - width / 2
                ymin = y_center - height / 2
                xmax = x_center + width / 2
                ymax = y_center + height / 2
                
                class_name = classes[class_id] if class_id < len(classes) else f"class_{class_id}"
                
                annotations.append(Annotation(
                    class_id=class_id,
                    class_name=class_name,
                    bbox=(xmin, ymin, xmax, ymax),
                    polygon=None
                ))
        
        return annotations
    
    @staticmethod
    def parse_json(json_path: str, class_filter: Optional[List[str]] = None) -> Tuple[List[Annotation], Tuple[int, int]]:
        """
        Parse JSON format (COCO-like)
        
        Expected format:
        {
            "image": {"width": 1920, "height": 1080},
            "annotations": [
                {
                    "class_name": "person",
                    "bbox": [x, y, w, h],  # or
                    "polygon": [[x1,y1], [x2,y2], ...]
                }
            ]
        }
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        img_width = data.get('image', {}).get('width', 0)
        img_height = data.get('image', {}).get('height', 0)
        
        annotations = []
        for ann in data.get('annotations', []):
            class_name = ann.get('class_name', 'unknown')
            
            # Filter by class if specified
            if class_filter and class_name not in class_filter:
                continue
            
            # Parse bbox or polygon
            bbox = None
            polygon = None
            
            if 'bbox' in ann:
                # COCO format: [x, y, width, height]
                x, y, w, h = ann['bbox']
                bbox = (x, y, x + w, y + h)
            elif 'polygon' in ann:
                polygon = [tuple(pt) for pt in ann['polygon']]
                # Calculate bounding box from polygon
                xs = [pt[0] for pt in polygon]
                ys = [pt[1] for pt in polygon]
                bbox = (min(xs), min(ys), max(xs), max(ys))
            else:
                continue
            
            annotations.append(Annotation(
                class_id=-1,  # Will be assigned later
                class_name=class_name,
                bbox=bbox,
                polygon=polygon
            ))
        
        return annotations, (img_width, img_height)


class DatasetGenerator:
    """Generate dataset from large annotated images using sliding windows"""
    
    def __init__(self):
        self.parser = AnnotationParser()
    
    def calculate_overlap(self, annotation: Annotation, window: Tuple[int, int, int, int]) -> float:
        """
        Calculate overlap ratio between annotation and window
        
        Args:
            annotation: Annotation object
            window: (x, y, x+w, y+h) window coordinates
            
        Returns:
            Overlap ratio (intersection area / original annotation area)
        """
        if annotation.polygon:
            return self._calculate_polygon_overlap(annotation.polygon, window)
        else:
            return self._calculate_bbox_overlap(annotation.bbox, window)
    
    def _calculate_bbox_overlap(self, bbox: Tuple[float, float, float, float], 
                                window: Tuple[int, int, int, int]) -> float:
        """Calculate bounding box overlap"""
        # Calculate intersection
        x1 = max(bbox[0], window[0])
        y1 = max(bbox[1], window[1])
        x2 = min(bbox[2], window[2])
        y2 = min(bbox[3], window[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection_area = (x2 - x1) * (y2 - y1)
        original_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        
        return intersection_area / original_area if original_area > 0 else 0.0
    
    def _calculate_polygon_overlap(self, polygon: List[Tuple[float, float]], 
                                   window: Tuple[int, int, int, int]) -> float:
        """Calculate polygon overlap using shapely"""
        try:
            from shapely.geometry import Polygon as ShapelyPolygon
            
            poly = ShapelyPolygon(polygon)
            window_poly = ShapelyPolygon([
                (window[0], window[1]),
                (window[2], window[1]),
                (window[2], window[3]),
                (window[0], window[3])
            ])
            
            intersection = poly.intersection(window_poly)
            return intersection.area / poly.area if poly.area > 0 else 0.0
        except ImportError:
            # Fallback to bbox if shapely not available
            xs = [pt[0] for pt in polygon]
            ys = [pt[1] for pt in polygon]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            return self._calculate_bbox_overlap(bbox, window)
    
    def transform_annotation_to_window(self, annotation: Annotation, 
                                      window: Tuple[int, int, int, int],
                                      window_size: Tuple[int, int]) -> Optional[Tuple[int, float, float, float, float]]:
        """
        Transform annotation coordinates to window-relative YOLO format
        
        Returns:
            (class_id, x_center, y_center, width, height) in normalized coordinates
            or None if annotation is invalid
        """
        wx, wy, wx2, wy2 = window
        window_w, window_h = window_size
        
        # Get bbox (use polygon bbox if polygon exists)
        if annotation.polygon:
            xs = [pt[0] for pt in annotation.polygon]
            ys = [pt[1] for pt in annotation.polygon]
            bbox = (min(xs), min(ys), max(xs), max(ys))
        else:
            bbox = annotation.bbox
        
        # Transform to window coordinates
        xmin = max(0, bbox[0] - wx)
        ymin = max(0, bbox[1] - wy)
        xmax = min(window_w, bbox[2] - wx)
        ymax = min(window_h, bbox[3] - wy)
        
        # Check if valid
        if xmax <= xmin or ymax <= ymin:
            return None
        
        # Convert to YOLO format (normalized)
        x_center = ((xmin + xmax) / 2) / window_w
        y_center = ((ymin + ymax) / 2) / window_h
        width = (xmax - xmin) / window_w
        height = (ymax - ymin) / window_h
        
        # Clamp to [0, 1]
        x_center = max(0.0, min(1.0, x_center))
        y_center = max(0.0, min(1.0, y_center))
        width = max(0.0, min(1.0, width))
        height = max(0.0, min(1.0, height))
        
        return (annotation.class_id, x_center, y_center, width, height)

    @staticmethod
    def _process_single_image_task(
        img_file: Path,
        annotation_format: str,
        annotations_dir: str,
        classes_filter: List[Union[str, int]],
        class_to_id: Dict[str, int],
        yolo_classes: List[str],
        window_width: int,
        window_height: int,
        stride_x: int,
        stride_y: int,
        overlap_threshold: float,
        output_images_dir: str,
        output_labels_dir: str,
    ) -> Dict:
        try:
            generator = DatasetGenerator()

            ann_file = None
            if annotation_format == 'voc':
                ann_file = Path(annotations_dir) / f'{img_file.stem}.xml'
            elif annotation_format == 'yolo':
                ann_file = Path(annotations_dir) / f'{img_file.stem}.txt'
            elif annotation_format == 'json':
                ann_file = Path(annotations_dir) / f'{img_file.stem}.json'

            if not ann_file or not ann_file.exists():
                return {
                    'success': True,
                    'processed': False,
                    'image_name': img_file.name,
                    'total_crops': 0,
                    'crops_with_annotations': 0,
                    'empty_crops_skipped': 0,
                    'annotations_extracted': 0,
                    'classes_found': [],
                }

            with Image.open(img_file) as img:
                img_width, img_height = img.size

                annotations = []
                if annotation_format == 'voc':
                    class_filter = classes_filter if classes_filter else None
                    annotations, _ = generator.parser.parse_voc(str(ann_file), class_filter)
                elif annotation_format == 'yolo':
                    filter_indices = classes_filter if classes_filter else None
                    annotations = generator.parser.parse_yolo(
                        str(ann_file),
                        img_width,
                        img_height,
                        yolo_classes,
                        filter_indices,
                    )
                elif annotation_format == 'json':
                    class_filter = classes_filter if classes_filter else None
                    annotations, _ = generator.parser.parse_json(str(ann_file), class_filter)

                classes_found = set()
                for ann in annotations:
                    if ann.class_id == -1:
                        ann.class_id = class_to_id.get(ann.class_name, 0)
                    classes_found.add(ann.class_name)

                total_crops = 0
                crops_with_annotations = 0
                empty_crops_skipped = 0
                annotations_extracted = 0
                crop_idx = 0

                for y in range(0, img_height, stride_y):
                    for x in range(0, img_width, stride_x):
                        x2 = min(x + window_width, img_width)
                        y2 = min(y + window_height, img_height)

                        x_start = max(0, x2 - window_width) if x2 == img_width else x
                        y_start = max(0, y2 - window_height) if y2 == img_height else y
                        window = (x_start, y_start, x_start + window_width, y_start + window_height)

                        window_annotations = []
                        for ann in annotations:
                            overlap = generator.calculate_overlap(ann, window)
                            if overlap >= overlap_threshold:
                                yolo_ann = generator.transform_annotation_to_window(
                                    ann,
                                    window,
                                    (window_width, window_height),
                                )
                                if yolo_ann:
                                    window_annotations.append(yolo_ann)
                                    annotations_extracted += 1

                        if not window_annotations:
                            empty_crops_skipped += 1
                            continue

                        crop = img.crop((x_start, y_start, x_start + window_width, y_start + window_height))
                        crop_name = f'{img_file.stem}_crop_{crop_idx}'
                        crop_path = os.path.join(output_images_dir, f'{crop_name}.jpg')
                        crop.save(crop_path, 'JPEG', quality=95)

                        label_path = os.path.join(output_labels_dir, f'{crop_name}.txt')
                        with open(label_path, 'w') as f:
                            for class_id, xc, yc, w, h in window_annotations:
                                f.write(f'{class_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n')

                        total_crops += 1
                        crops_with_annotations += 1
                        crop_idx += 1

            return {
                'success': True,
                'processed': True,
                'image_name': img_file.name,
                'total_crops': total_crops,
                'crops_with_annotations': crops_with_annotations,
                'empty_crops_skipped': empty_crops_skipped,
                'annotations_extracted': annotations_extracted,
                'classes_found': sorted(classes_found),
            }
        except Exception as e:
            return {
                'success': False,
                'processed': False,
                'image_name': img_file.name,
                'error': str(e),
                'total_crops': 0,
                'crops_with_annotations': 0,
                'empty_crops_skipped': 0,
                'annotations_extracted': 0,
                'classes_found': [],
            }
    
    def generate_dataset(self, config: Dict, progress_callback=None) -> Dict:
        """
        Generate dataset from large annotated images
        
        Args:
            config: Configuration dictionary with keys:
                - annotation_format: 'voc', 'yolo', or 'json'
                - images_dir: Path to images
                - annotations_dir: Path to annotations
                - output_dir: Output directory
                - classes: List of class names/indices to keep
                - window_width: Window width
                - window_height: Window height
                - stride_y: Vertical stride
                - overlap_threshold: Minimum overlap percentage (0-100)
            progress_callback: Optional function(current, total, message)
        """
        try:
            annotation_format = config['annotation_format']
            images_dir = config['images_dir']
            annotations_dir = config['annotations_dir']
            output_dir = config['output_dir']
            classes_filter = config.get('classes', [])
            window_width = config.get('window_width', 640)
            window_height = config.get('window_height', 640)
            stride_x = config.get('stride_x', 320)
            stride_y = config.get('stride_y', 320)
            overlap_threshold = config.get('overlap_threshold', 100) / 100.0
            
            # Create output directories
            output_images_dir = os.path.join(output_dir, 'images')
            output_labels_dir = os.path.join(output_dir, 'labels')
            os.makedirs(output_images_dir, exist_ok=True)
            os.makedirs(output_labels_dir, exist_ok=True)
            
            # Get image files
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
            image_files = []
            for ext in image_extensions:
                image_files.extend(Path(images_dir).glob(f'*{ext}'))
                image_files.extend(Path(images_dir).glob(f'*{ext.upper()}'))
            
            if not image_files:
                return {
                    'success': False,
                    'error': f'No images found in {images_dir}'
                }
            
            # Statistics
            total_images = len(image_files)
            total_crops = 0
            crops_with_annotations = 0
            empty_crops_skipped = 0
            annotations_extracted = 0
            
            # Build class mapping
            class_to_id = {}
            if annotation_format == 'yolo':
                # For YOLO, load classes.txt when available.
                classes_file = os.path.join(annotations_dir, 'classes.txt')
                if os.path.exists(classes_file):
                    with open(classes_file, 'r') as f:
                        all_classes = [line.strip() for line in f if line.strip()]
                    if classes_filter:
                        for idx in classes_filter:
                            if idx < len(all_classes):
                                class_to_id[all_classes[idx]] = idx
                    else:
                        for idx, class_name in enumerate(all_classes):
                            class_to_id[class_name] = idx
                else:
                    # Use indices directly
                    for idx in classes_filter:
                        class_to_id[f'class_{idx}'] = idx
            else:
                # For VOC/JSON, classes_filter contains names
                for idx, class_name in enumerate(classes_filter):
                    class_to_id[class_name] = idx
            
            yolo_classes = list(class_to_id.keys())
            classes_found = set()
            errors = []

            plan = get_executor_plan(total_images, workload='cpu', prefer_process=True)
            completed_images = 0
            if plan.kind == 'serial':
                for img_file in image_files:
                    result = self._process_single_image_task(
                        img_file,
                        annotation_format,
                        annotations_dir,
                        classes_filter,
                        class_to_id,
                        yolo_classes,
                        window_width,
                        window_height,
                        stride_x,
                        stride_y,
                        overlap_threshold,
                        output_images_dir,
                        output_labels_dir,
                    )
                    completed_images += 1

                    total_crops += result.get('total_crops', 0)
                    crops_with_annotations += result.get('crops_with_annotations', 0)
                    empty_crops_skipped += result.get('empty_crops_skipped', 0)
                    annotations_extracted += result.get('annotations_extracted', 0)
                    classes_found.update(result.get('classes_found', []))
                    if not result.get('success'):
                        errors.append(f"{img_file.name}: {result.get('error', 'unknown error')}")

                    if progress_callback:
                        progress_callback(completed_images, total_images, f"Processed {img_file.name}")
            else:
                executor_cls = (
                    concurrent.futures.ProcessPoolExecutor
                    if plan.kind == 'process'
                    else concurrent.futures.ThreadPoolExecutor
                )
                with executor_cls(max_workers=plan.workers) as executor:
                    future_to_image = {
                        executor.submit(
                            self._process_single_image_task,
                            img_file,
                            annotation_format,
                            annotations_dir,
                            classes_filter,
                            class_to_id,
                            yolo_classes,
                            window_width,
                            window_height,
                            stride_x,
                            stride_y,
                            overlap_threshold,
                            output_images_dir,
                            output_labels_dir,
                        ): img_file
                        for img_file in image_files
                    }

                    for future in concurrent.futures.as_completed(future_to_image):
                        img_file = future_to_image[future]
                        result = future.result()
                        completed_images += 1

                        total_crops += result.get('total_crops', 0)
                        crops_with_annotations += result.get('crops_with_annotations', 0)
                        empty_crops_skipped += result.get('empty_crops_skipped', 0)
                        annotations_extracted += result.get('annotations_extracted', 0)
                        classes_found.update(result.get('classes_found', []))
                        if not result.get('success'):
                            errors.append(f"{img_file.name}: {result.get('error', 'unknown error')}")

                        if progress_callback:
                            progress_callback(completed_images, total_images, f"Processed {img_file.name}")
            
            # Save classes.txt
            if class_to_id:
                classes_list = sorted(class_to_id.items(), key=lambda x: x[1])
                with open(os.path.join(output_dir, 'classes.txt'), 'w') as f:
                    for class_name, _ in classes_list:
                        f.write(f'{class_name}\n')
            
            return {
                'success': True,
                'total_images': total_images,
                'total_crops': total_crops,
                'crops_with_annotations': crops_with_annotations,
                'empty_crops_skipped': empty_crops_skipped,
                'annotations_extracted': annotations_extracted,
                'classes_found': sorted(list(classes_found)),
                'errors': errors,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
