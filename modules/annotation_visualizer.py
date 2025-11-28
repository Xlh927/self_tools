import os
import cv2
import json
import xml.etree.ElementTree as ET
import numpy as np
from pathlib import Path
import random


class AnnotationVisualizer:
    def __init__(self):
        self.colors = self._generate_colors(100)
    
    def _generate_colors(self, n):
        """Generate n distinct colors for visualization"""
        colors = []
        for i in range(n):
            hue = int(180 * i / n)
            color = cv2.cvtColor(np.uint8([[[hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
            colors.append(tuple(map(int, color)))
        return colors
    
    def detect_format(self, annotations_dir):
        """Auto-detect annotation format"""
        annotations_path = Path(annotations_dir)
        
        if not annotations_path.exists():
            return None
        
        files = list(annotations_path.iterdir())
        
        for f in files:
            if f.suffix.lower() == '.xml':
                return 'voc'
            elif f.suffix.lower() == '.txt':
                return 'yolo'
            elif f.suffix.lower() == '.json':
                return 'json'
        
        return None
    
    def detect_classes(self, annotations_dir, annotation_format=None):
        """Detect available classes from annotations"""
        if annotation_format is None:
            annotation_format = self.detect_format(annotations_dir)
        
        if annotation_format is None:
            return {'success': False, 'error': 'Could not detect annotation format'}
        
        annotations_path = Path(annotations_dir)
        classes = set()
        
        try:
            if annotation_format == 'voc':
                for xml_file in annotations_path.glob('*.xml'):
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    for obj in root.findall('object'):
                        name = obj.find('name').text
                        classes.add(name)
            
            elif annotation_format == 'yolo':
                # Try to find classes.txt
                classes_file = annotations_path.parent / 'classes.txt'
                if not classes_file.exists():
                    classes_file = annotations_path / 'classes.txt'
                
                if classes_file.exists():
                    with open(classes_file, 'r') as f:
                        classes = set(line.strip() for line in f if line.strip())
                else:
                    # Return indices if no classes.txt found
                    max_class_id = -1
                    for txt_file in annotations_path.glob('*.txt'):
                        with open(txt_file, 'r') as f:
                            for line in f:
                                parts = line.strip().split()
                                if parts:
                                    class_id = int(parts[0])
                                    max_class_id = max(max_class_id, class_id)
                    
                    if max_class_id >= 0:
                        classes = set(str(i) for i in range(max_class_id + 1))
            
            elif annotation_format == 'json':
                for json_file in annotations_path.glob('*.json'):
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        if 'shapes' in data:  # LabelMe format
                            for shape in data['shapes']:
                                classes.add(shape['label'])
            
            return {
                'success': True,
                'format': annotation_format,
                'classes': sorted(list(classes))
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def parse_voc_annotation(self, xml_path, image_shape):
        """Parse VOC XML annotation"""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        annotations = []
        for obj in root.findall('object'):
            name = obj.find('name').text
            bndbox = obj.find('bndbox')
            
            xmin = int(float(bndbox.find('xmin').text))
            ymin = int(float(bndbox.find('ymin').text))
            xmax = int(float(bndbox.find('xmax').text))
            ymax = int(float(bndbox.find('ymax').text))
            
            # Check for polygon/segmentation
            polygon = obj.find('polygon')
            if polygon is not None:
                points = []
                for pt in polygon.findall('pt'):
                    x = int(float(pt.find('x').text))
                    y = int(float(pt.find('y').text))
                    points.append([x, y])
                
                annotations.append({
                    'class': name,
                    'type': 'polygon',
                    'bbox': [xmin, ymin, xmax, ymax],
                    'points': points
                })
            else:
                annotations.append({
                    'class': name,
                    'type': 'bbox',
                    'bbox': [xmin, ymin, xmax, ymax]
                })
        
        return annotations
    
    def parse_yolo_annotation(self, txt_path, image_shape, classes_list):
        """Parse YOLO TXT annotation"""
        h, w = image_shape[:2]
        annotations = []
        
        with open(txt_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                
                class_id = int(parts[0])
                class_name = classes_list[class_id] if class_id < len(classes_list) else str(class_id)
                
                if len(parts) == 5:  # bbox format
                    x_center, y_center, width, height = map(float, parts[1:5])
                    
                    x_center *= w
                    y_center *= h
                    width *= w
                    height *= h
                    
                    xmin = int(x_center - width / 2)
                    ymin = int(y_center - height / 2)
                    xmax = int(x_center + width / 2)
                    ymax = int(y_center + height / 2)
                    
                    annotations.append({
                        'class': class_name,
                        'type': 'bbox',
                        'bbox': [xmin, ymin, xmax, ymax]
                    })
                
                elif len(parts) > 5:  # segmentation format
                    points = []
                    for i in range(1, len(parts), 2):
                        x = int(float(parts[i]) * w)
                        y = int(float(parts[i + 1]) * h)
                        points.append([x, y])
                    
                    # Calculate bbox from polygon
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    xmin, xmax = min(xs), max(xs)
                    ymin, ymax = min(ys), max(ys)
                    
                    annotations.append({
                        'class': class_name,
                        'type': 'polygon',
                        'bbox': [xmin, ymin, xmax, ymax],
                        'points': points
                    })
        
        return annotations
    
    def parse_json_annotation(self, json_path, image_shape):
        """Parse JSON annotation (LabelMe format)"""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        annotations = []
        
        if 'shapes' in data:
            for shape in data['shapes']:
                label = shape['label']
                shape_type = shape['shape_type']
                points = shape['points']
                
                if shape_type == 'rectangle':
                    x1, y1 = points[0]
                    x2, y2 = points[1]
                    xmin, xmax = int(min(x1, x2)), int(max(x1, x2))
                    ymin, ymax = int(min(y1, y2)), int(max(y1, y2))
                    
                    annotations.append({
                        'class': label,
                        'type': 'bbox',
                        'bbox': [xmin, ymin, xmax, ymax]
                    })
                
                elif shape_type == 'polygon':
                    points_int = [[int(p[0]), int(p[1])] for p in points]
                    xs = [p[0] for p in points_int]
                    ys = [p[1] for p in points_int]
                    xmin, xmax = min(xs), max(xs)
                    ymin, ymax = min(ys), max(ys)
                    
                    annotations.append({
                        'class': label,
                        'type': 'polygon',
                        'bbox': [xmin, ymin, xmax, ymax],
                        'points': points_int
                    })
        
        return annotations
    
    def visualize(self, config):
        """
        Visualize annotations on images
        
        config = {
            'images_dir': str,
            'annotations_dir': str,
            'output_dir': str,
            'annotation_format': str (optional, auto-detect if not provided),
            'selected_classes': list (optional, all classes if not provided),
            'draw_mode': 'bbox' or 'mask' (default: 'bbox')
        }
        """
        images_dir = Path(config['images_dir'])
        annotations_dir = Path(config['annotations_dir'])
        output_dir = Path(config['output_dir'])
        
        if not images_dir.exists():
            return {'success': False, 'error': f'Images directory not found: {images_dir}'}
        
        if not annotations_dir.exists():
            return {'success': False, 'error': f'Annotations directory not found: {annotations_dir}'}
        
        # Detect format
        annotation_format = config.get('annotation_format')
        if not annotation_format:
            annotation_format = self.detect_format(annotations_dir)
        
        if not annotation_format:
            return {'success': False, 'error': 'Could not detect annotation format'}
        
        # Get classes
        classes_result = self.detect_classes(annotations_dir, annotation_format)
        if not classes_result['success']:
            return classes_result
        
        all_classes = classes_result['classes']
        selected_classes = config.get('selected_classes', all_classes)
        draw_mode = config.get('draw_mode', 'bbox')
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create class-to-color mapping
        class_colors = {cls: self.colors[i % len(self.colors)] for i, cls in enumerate(all_classes)}
        
        processed_count = 0
        errors = []
        
        # Process images
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        for img_file in images_dir.iterdir():
            if img_file.suffix.lower() not in image_extensions:
                continue
            
            # Find corresponding annotation
            ann_file = None
            if annotation_format == 'voc':
                ann_file = annotations_dir / f"{img_file.stem}.xml"
            elif annotation_format == 'yolo':
                ann_file = annotations_dir / f"{img_file.stem}.txt"
            elif annotation_format == 'json':
                ann_file = annotations_dir / f"{img_file.stem}.json"
            
            if not ann_file or not ann_file.exists():
                continue
            
            try:
                # Load image
                image = cv2.imread(str(img_file))
                if image is None:
                    errors.append(f"Failed to load image: {img_file.name}")
                    continue
                
                # Parse annotations
                if annotation_format == 'voc':
                    annotations = self.parse_voc_annotation(ann_file, image.shape)
                elif annotation_format == 'yolo':
                    annotations = self.parse_yolo_annotation(ann_file, image.shape, all_classes)
                elif annotation_format == 'json':
                    annotations = self.parse_json_annotation(ann_file, image.shape)
                
                # Draw annotations
                for ann in annotations:
                    if ann['class'] not in selected_classes:
                        continue
                    
                    color = class_colors[ann['class']]
                    
                    if draw_mode == 'bbox' or ann['type'] == 'bbox':
                        # Draw bounding box
                        xmin, ymin, xmax, ymax = ann['bbox']
                        cv2.rectangle(image, (xmin, ymin), (xmax, ymax), color, 2)
                        
                        # Draw label
                        label = ann['class']
                        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        cv2.rectangle(image, (xmin, ymin - label_h - 4), (xmin + label_w, ymin), color, -1)
                        cv2.putText(image, label, (xmin, ymin - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    elif draw_mode == 'mask' and 'points' in ann:
                        # Draw polygon/mask
                        points = np.array(ann['points'], dtype=np.int32)
                        cv2.polylines(image, [points], True, color, 2)
                        
                        # Draw label at bbox top-left
                        xmin, ymin = ann['bbox'][:2]
                        label = ann['class']
                        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        cv2.rectangle(image, (xmin, ymin - label_h - 4), (xmin + label_w, ymin), color, -1)
                        cv2.putText(image, label, (xmin, ymin - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Save visualized image
                output_path = output_dir / img_file.name
                cv2.imwrite(str(output_path), image)
                processed_count += 1
            
            except Exception as e:
                errors.append(f"Error processing {img_file.name}: {str(e)}")
        
        return {
            'success': True,
            'format': annotation_format,
            'processed_count': processed_count,
            'total_classes': len(all_classes),
            'selected_classes': len(selected_classes),
            'errors': errors
        }
