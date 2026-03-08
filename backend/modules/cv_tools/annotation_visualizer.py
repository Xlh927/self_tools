import os
import cv2
import json
import xml.etree.ElementTree as ET
import numpy as np
from pathlib import Path
import random
import concurrent.futures
from PIL import Image

try:
    from parallelism_config import get_executor_plan
except Exception:  # pragma: no cover - import path differs by runtime entrypoint
    from backend.parallelism_config import get_executor_plan


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
        
        # Check first few files
        count = 0
        for f in annotations_path.iterdir():
            if count > 100: break # optimize
            if f.suffix.lower() == '.xml':
                return 'voc'
            elif f.suffix.lower() == '.txt' and f.name != 'classes.txt':
                return 'yolo'
            elif f.suffix.lower() == '.json':
                return 'json'
            count += 1
        
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
                    try:
                        tree = ET.parse(xml_file)
                        root = tree.getroot()
                        for obj in root.findall('object'):
                            name_elem = obj.find('name')
                            if name_elem is not None and name_elem.text:
                                classes.add(name_elem.text)
                    except:
                        continue
            
            elif annotation_format == 'yolo':
                # Try to find classes.txt
                classes_file = annotations_path.parent / 'classes.txt'
                if not classes_file.exists():
                    classes_file = annotations_path / 'classes.txt'
                
                if classes_file.exists():
                    with open(classes_file, 'r', encoding='utf-8') as f:
                        classes = set(line.strip() for line in f if line.strip())
                else:
                    # Return indices if no classes.txt found
                    max_class_id = -1
                    files = list(annotations_path.glob('*.txt'))
                    # Sample some files if too many
                    if len(files) > 1000:
                        files = files[:1000]
                        
                    for txt_file in files:
                        try:
                            with open(txt_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    parts = line.strip().split()
                                    if parts:
                                        class_id = int(parts[0])
                                        max_class_id = max(max_class_id, class_id)
                        except:
                            continue
                    
                    if max_class_id >= 0:
                        classes = set(str(i) for i in range(max_class_id + 1))
            
            elif annotation_format == 'json':
                files = list(annotations_path.glob('*.json'))
                if len(files) > 1000: files = files[:1000]
                
                for json_file in files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'shapes' in data:  # LabelMe format
                                for shape in data['shapes']:
                                    classes.add(shape['label'])
                    except:
                        continue
            
            # Sort naturally
            sorted_classes = sorted(list(classes))
            
            # Re-sort if they are all integers
            try:
                if all(c.isdigit() for c in sorted_classes):
                    sorted_classes = sorted(sorted_classes, key=int)
            except:
                pass
                
            return {
                'success': True,
                'format': annotation_format,
                'classes': sorted_classes
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
            
            if bndbox is not None:
                xmin = float(bndbox.find('xmin').text)
                ymin = float(bndbox.find('ymin').text)
                xmax = float(bndbox.find('xmax').text)
                ymax = float(bndbox.find('ymax').text)
                
                annotations.append({
                    'class': name,
                    'type': 'bbox',
                    'bbox': [xmin, ymin, xmax, ymax]
                })
            
            # Check for polygon/segmentation (uncommon in standard VOC but possible)
            polygon = obj.find('polygon')
            if polygon is not None:
                points = []
                for pt in polygon.findall('pt'):
                    x = float(pt.find('x').text)
                    y = float(pt.find('y').text)
                    points.append([x, y])
                
                # If we have points, update the entry to include them
                # Note: bndbox might not exist for some polygon formats, handle accordingly
                # For now assume mixed
                if len(annotations) > 0 and annotations[-1]['class'] == name:
                    annotations[-1]['type'] = 'polygon'
                    annotations[-1]['points'] = points
                else:
                    # Calculate bbox from points if missing
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    annotations.append({
                        'class': name,
                        'type': 'polygon',
                        'bbox': [min(xs), min(ys), max(xs), max(ys)],
                        'points': points
                    })
        
        return annotations
    
    def parse_yolo_annotation(self, txt_path, image_shape, classes_list):
        """Parse YOLO TXT annotation"""
        h, w = image_shape[:2]
        annotations = []
        
        if not classes_list:
            # Fallback to string indices if no classes provided
            classes_list = [str(i) for i in range(1000)]
            
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                
                try:
                    class_id = int(parts[0])
                    class_name = classes_list[class_id] if class_id < len(classes_list) else str(class_id)
                    
                    if len(parts) == 5:  # bbox format
                        x_center, y_center, width, height = map(float, parts[1:5])
                        
                        x_center *= w
                        y_center *= h
                        width *= w
                        height *= h
                        
                        xmin = x_center - width / 2
                        ymin = y_center - height / 2
                        xmax = x_center + width / 2
                        ymax = y_center + height / 2
                        
                        annotations.append({
                            'class': class_name,
                            'type': 'bbox',
                            'bbox': [xmin, ymin, xmax, ymax]
                        })
                    
                    elif len(parts) > 5:  # segmentation format
                        points = []
                        for i in range(1, len(parts), 2):
                            x = float(parts[i]) * w
                            y = float(parts[i + 1]) * h
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
                except Exception as e:
                    # Skip malformed lines
                    continue
        
        return annotations
    
    def parse_json_annotation(self, json_path, image_shape):
        """Parse JSON annotation (LabelMe format)"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        annotations = []
        
        if 'shapes' in data:
            for shape in data['shapes']:
                label = shape['label']
                shape_type = shape.get('shape_type', 'points') # default
                points = shape['points']
                
                if not points: continue
                
                if shape_type == 'rectangle':
                    x1, y1 = points[0]
                    x2, y2 = points[1]
                    xmin, xmax = min(x1, x2), max(x1, x2)
                    ymin, ymax = min(y1, y2), max(y1, y2)
                    
                    annotations.append({
                        'class': label,
                        'type': 'bbox',
                        'bbox': [xmin, ymin, xmax, ymax]
                    })
                
                elif shape_type in ['polygon', 'points']:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    xmin, xmax = min(xs), max(xs)
                    ymin, ymax = min(ys), max(ys)
                    
                    annotations.append({
                        'class': label,
                        'type': 'polygon',
                        'bbox': [xmin, ymin, xmax, ymax],
                        'points': points
                    })
        
        return annotations
    
    def _process_single_image(self, img_file, annotations_dir, output_dir, annotation_format, 
                               all_classes, selected_classes, draw_mode, class_colors, box_thickness, text_size,
                               rename_mode='none', rename_content='name'):
        """Process a single image for visualization"""
        try:
            # Robust image loading with PIL fallback when cv2 decoding fails.
            try:
                # First try cv2
                image = cv2.imread(str(img_file))
                if image is None:
                    pil_img = Image.open(img_file)
                    image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception:
                pil_img = Image.open(img_file)
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')
                image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            if image is None:
               return False, f"Failed to load image: {img_file.name}"
            
            h, w = image.shape[:2]
            
            # Find corresponding annotation
            ann_file = None
            if annotation_format == 'voc':
                ann_file = annotations_dir / f"{img_file.stem}.xml"
            elif annotation_format == 'yolo':
                ann_file = annotations_dir / f"{img_file.stem}.txt"
            elif annotation_format == 'json':
                ann_file = annotations_dir / f"{img_file.stem}.json"
            
            # Determine initial output filename (default same as input)
            output_filename = img_file.name
            
            if not ann_file or not ann_file.exists():
                output_path = output_dir / output_filename
                cv2.imwrite(str(output_path), image)
                return True, None
            
            # Parse annotations
            annotations = []
            if annotation_format == 'voc':
                annotations = self.parse_voc_annotation(ann_file, image.shape)
            elif annotation_format == 'yolo':
                annotations = self.parse_yolo_annotation(ann_file, image.shape, all_classes)
            elif annotation_format == 'json':
                annotations = self.parse_json_annotation(ann_file, image.shape)
            
            # Determine visualization parameters
            # If valid box_thickness provided (>=1), use it. Else use dynamic.
            if box_thickness and box_thickness > 0:
                thickness = int(box_thickness)
            else:
                scale_factor = max(w, h) / 1000.0
                thickness = max(1, int(scale_factor))
            
            # If valid text_size provided (>=1), use it as level (size/10). Else use dynamic.
            if text_size and text_size > 0:
                font_scale = text_size / 10.0
            else:
                scale_factor = max(w, h) / 1000.0
                font_scale = max(0.3, 0.3 * scale_factor)
            
            # Draw annotations and collect present classes
            present_classes = set()
            for ann in annotations:
                if ann['class'] not in selected_classes:
                    continue
                
                present_classes.add(ann['class'])
                
                color = class_colors.get(ann['class'], (0, 255, 0))
                
                # Clip bbox to image boundaries
                bbox = ann['bbox']
                xmin = max(0, min(w - 1, int(bbox[0])))
                ymin = max(0, min(h - 1, int(bbox[1])))
                xmax = max(0, min(w - 1, int(bbox[2])))
                ymax = max(0, min(h - 1, int(bbox[3])))
                
                if xmin >= xmax or ymin >= ymax:
                    continue
                
                if draw_mode == 'bbox' or ann['type'] == 'bbox':
                    # Draw bounding box
                    cv2.rectangle(image, (xmin, ymin), (xmax, ymax), color, thickness)
                    
                    # Draw label
                    label = ann['class']
                    (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                    
                    # Ensure label is within image
                    # Default: top-left of bbox. If it goes above image, put it inside bbox.
                    label_y_bott = ymin - 4
                    if label_y_bott - label_h < 0:
                        label_y_bott = ymin + label_h + 4
                    
                    # Also check right boundary
                    label_x_left = xmin
                    if label_x_left + label_w > w:
                        label_x_left = w - label_w
                    
                    # Draw label background
                    cv2.rectangle(image, (label_x_left, label_y_bott - label_h - baseline), (label_x_left + label_w, label_y_bott + baseline), color, -1)
                    cv2.putText(image, label, (label_x_left, label_y_bott), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), max(1, thickness//2))
                
                elif draw_mode == 'mask' and 'points' in ann:
                    # Draw polygon/mask
                    points = np.array(ann['points'], dtype=np.int32)
                    cv2.polylines(image, [points], True, color, thickness)
                    
                    # Draw label at bbox top-left (same logic as above)
                    label = ann['class']
                    (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                    
                    label_y_bott = ymin - 4
                    if label_y_bott - label_h < 0:
                        label_y_bott = ymin + label_h + 4
                    
                    label_x_left = xmin
                    if label_x_left + label_w > w:
                        label_x_left = w - label_w

                    cv2.rectangle(image, (label_x_left, label_y_bott - label_h - baseline), (label_x_left + label_w, label_y_bott + baseline), color, -1)
                    cv2.putText(image, label, (label_x_left, label_y_bott), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), max(1, thickness//2))

            # Handle Renaming Logic
            if rename_mode in ['prefix', 'suffix'] and present_classes:
                tags = []
                # Sort for determinism
                sorted_classes = sorted(list(present_classes))
                
                if rename_content == 'id':
                    # Convert names to IDs
                    for cls_name in sorted_classes:
                        try:
                            idx = all_classes.index(cls_name)
                            tags.append(str(idx))
                        except ValueError:
                            tags.append(cls_name) # Fallback
                else:
                    tags = sorted_classes
                
                tag_str = '_'.join(tags)
                
                if rename_mode == 'prefix':
                    output_filename = f"{tag_str}_{img_file.name}"
                elif rename_mode == 'suffix':
                    output_filename = f"{img_file.stem}_{tag_str}{img_file.suffix}"
            
            # Save visualized image
            output_path = output_dir / output_filename
            cv2.imwrite(str(output_path), image)
            return True, None
            
        except Exception as e:
            return False, f"Error processing {img_file.name}: {str(e)}"

    def visualize(self, config, progress_callback=None, cancel_event=None):
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
        selected_classes = set(config.get('selected_classes', all_classes))
        draw_mode = config.get('draw_mode', 'bbox')
        box_thickness = config.get('box_thickness')
        text_size = config.get('text_size')
        rename_mode = config.get('rename_mode', 'none')
        rename_content = config.get('rename_content', 'name')
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create class-to-color mapping
        class_colors = {cls: self.colors[i % len(self.colors)] for i, cls in enumerate(all_classes)}
        
        processed_count = 0
        errors = []
        
        # Collect image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
        image_files = [f for f in images_dir.iterdir() if f.suffix.lower() in image_extensions]
        total_files = len(image_files)
        
        completed_files = 0
        plan = get_executor_plan(total_files, workload='io', prefer_process=False)
        if plan.kind == 'serial':
            for img_file in image_files:
                if cancel_event and cancel_event.is_set():
                    return {
                        'success': False,
                        'error': 'Operation cancelled by user',
                        'processed_count': processed_count,
                        'total_classes': len(all_classes),
                        'selected_classes': len(selected_classes),
                        'errors': errors
                    }

                success, error_msg = self._process_single_image(
                    img_file, annotations_dir, output_dir, annotation_format,
                    all_classes, selected_classes, draw_mode, class_colors,
                    box_thickness, text_size, rename_mode, rename_content
                )
                completed_files += 1

                if success:
                    processed_count += 1
                elif error_msg:
                    errors.append(error_msg)

                if progress_callback:
                    progress_callback(completed_files, total_files, f"Processed {img_file.name}")
        else:
            executor_cls = (
                concurrent.futures.ProcessPoolExecutor
                if plan.kind == 'process'
                else concurrent.futures.ThreadPoolExecutor
            )
            with executor_cls(max_workers=plan.workers) as executor:
                futures = {
                    executor.submit(
                        self._process_single_image,
                        img_file, annotations_dir, output_dir, annotation_format,
                        all_classes, selected_classes, draw_mode, class_colors,
                        box_thickness, text_size, rename_mode, rename_content
                    ): img_file for img_file in image_files
                }

                for future in concurrent.futures.as_completed(futures):
                    # Check for cancellation
                    if cancel_event and cancel_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        return {
                            'success': False,
                            'error': 'Operation cancelled by user',
                            'processed_count': processed_count,
                            'total_classes': len(all_classes),
                            'selected_classes': len(selected_classes),
                            'errors': errors
                        }

                    success, error_msg = future.result()
                    completed_files += 1

                    if success:
                        processed_count += 1
                    elif error_msg:
                        errors.append(error_msg)

                    if progress_callback:
                        progress_callback(completed_files, total_files, f"Processed {futures[future].name}")
        
        return {
            'success': True,
            'format': annotation_format,
            'processed_count': processed_count,
            'total_classes': len(all_classes),
            'selected_classes': len(selected_classes),
            'errors': errors
        }
