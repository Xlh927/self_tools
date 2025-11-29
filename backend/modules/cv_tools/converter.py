"""
Dataset Format Converter
Supports bidirectional conversion between VOC and YOLO formats
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict


class DatasetConverter:
    """Handles conversion between VOC and YOLO dataset formats"""
    
    def __init__(self, classes_file: str = None):
        """
        Initialize converter
        
        Args:
            classes_file: Path to classes.txt file (one class per line)
        """
        self.classes = []
        if classes_file and os.path.exists(classes_file):
            with open(classes_file, 'r', encoding='utf-8') as f:
                self.classes = [line.strip() for line in f if line.strip()]
    
    def set_classes(self, classes: List[str]):
        """Set class names manually"""
        self.classes = classes
    
    def voc_to_yolo(self, voc_xml_dir: str, images_dir: str, output_dir: str, 
                    classes_file: str = None, progress_callback=None) -> Dict[str, any]:
        """
        Convert VOC format to YOLO format
        
        Args:
            voc_xml_dir: Directory containing VOC XML annotation files
            images_dir: Directory containing images
            output_dir: Output directory for YOLO txt files
            classes_file: Path to classes.txt file (optional)
            progress_callback: Optional function(current, total, message)
            
        Returns:
            Dictionary with conversion results
        """
        try:
            # Load classes if provided
            if classes_file and os.path.exists(classes_file):
                with open(classes_file, 'r', encoding='utf-8') as f:
                    self.classes = [line.strip() for line in f if line.strip()]
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Get all XML files
            xml_files = list(Path(voc_xml_dir).glob('*.xml'))
            
            if not xml_files:
                return {
                    'success': False,
                    'error': f'No XML files found in {voc_xml_dir}'
                }
            
            converted_count = 0
            skipped_count = 0
            errors = []
            
            for i, xml_file in enumerate(xml_files):
                if progress_callback:
                    progress_callback(i, len(xml_files), f"Processing {xml_file.name}")

                try:
                    # Parse XML
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    
                    # Get image dimensions
                    size = root.find('size')
                    if size is None:
                        skipped_count += 1
                        errors.append(f'{xml_file.name}: Missing size element')
                        continue
                    
                    img_width = int(size.find('width').text)
                    img_height = int(size.find('height').text)
                    
                    # Process objects
                    yolo_annotations = []
                    
                    for obj in root.findall('object'):
                        class_name = obj.find('name').text
                        
                        # Auto-add class if not in list
                        if class_name not in self.classes:
                            self.classes.append(class_name)
                        
                        class_id = self.classes.index(class_name)
                        
                        # Get bounding box
                        bbox = obj.find('bndbox')
                        xmin = float(bbox.find('xmin').text)
                        ymin = float(bbox.find('ymin').text)
                        xmax = float(bbox.find('xmax').text)
                        ymax = float(bbox.find('ymax').text)
                        
                        # Convert to YOLO format (normalized center x, y, width, height)
                        x_center = ((xmin + xmax) / 2) / img_width
                        y_center = ((ymin + ymax) / 2) / img_height
                        width = (xmax - xmin) / img_width
                        height = (ymax - ymin) / img_height
                        
                        yolo_annotations.append(
                            f'{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}'
                        )
                    
                    # Write YOLO annotation file
                    output_file = Path(output_dir) / f'{xml_file.stem}.txt'
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(yolo_annotations))
                    
                    converted_count += 1
                    
                except Exception as e:
                    skipped_count += 1
                    errors.append(f'{xml_file.name}: {str(e)}')
            
            # Save classes file
            classes_output = Path(output_dir) / 'classes.txt'
            with open(classes_output, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.classes))
            
            return {
                'success': True,
                'converted': converted_count,
                'skipped': skipped_count,
                'total': len(xml_files),
                'classes': self.classes,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def scan_yolo_classes(self, yolo_txt_dir: str) -> Dict[int, int]:
        """
        扫描YOLO格式文件，提取所有存在的类别ID及其出现次数
        
        Args:
            yolo_txt_dir: Directory containing YOLO txt annotation files
            
        Returns:
            Dictionary of {class_id: count}
        """
        class_counts = {}
        txt_files = list(Path(yolo_txt_dir).glob('*.txt'))
        txt_files = [f for f in txt_files if f.name != 'classes.txt']
        
        for txt_file in txt_files:
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split()
                        if parts:
                            class_id = int(parts[0])
                            class_counts[class_id] = class_counts.get(class_id, 0) + 1
            except Exception:
                continue
        
        return class_counts
    
    def yolo_to_voc(self, yolo_txt_dir: str, images_dir: str, output_dir: str,
                    classes_file: str = None, custom_classes: List[str] = None,
                    progress_callback=None) -> Dict[str, any]:
        """
        Convert YOLO format to VOC format
        
        Args:
            yolo_txt_dir: Directory containing YOLO txt annotation files
            images_dir: Directory containing images
            output_dir: Output directory for VOC XML files
            classes_file: Path to classes.txt file (optional)
            custom_classes: List of custom class names indexed by ID (optional)
            progress_callback: Optional function(current, total, message)
            
        Returns:
            Dictionary with conversion results
        """
        try:
            # Load classes
            if custom_classes:
                # 使用自定义类别列表
                self.classes = custom_classes
            elif classes_file and os.path.exists(classes_file):
                with open(classes_file, 'r', encoding='utf-8') as f:
                    self.classes = [line.strip() for line in f if line.strip()]
            elif not self.classes:
                # 如果没有提供类别信息，使用默认命名
                class_counts = self.scan_yolo_classes(yolo_txt_dir)
                if class_counts:
                    self.classes = [f'class_{i}' for i in range(max(class_counts.keys()) + 1)]
                else:
                    return {
                        'success': False,
                        'error': 'No annotations found in YOLO files'
                    }
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Get all txt files
            txt_files = list(Path(yolo_txt_dir).glob('*.txt'))
            txt_files = [f for f in txt_files if f.name != 'classes.txt']
            
            if not txt_files:
                return {
                    'success': False,
                    'error': f'No txt files found in {yolo_txt_dir}'
                }
            
            converted_count = 0
            skipped_count = 0
            errors = []
            
            for i, txt_file in enumerate(txt_files):
                if progress_callback:
                    progress_callback(i, len(txt_files), f"Processing {txt_file.name}")
                try:
                    # Find corresponding image
                    image_path = None
                    for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                        potential_path = Path(images_dir) / f'{txt_file.stem}{ext}'
                        if potential_path.exists():
                            image_path = potential_path
                            break
                    
                    if not image_path:
                        skipped_count += 1
                        errors.append(f'{txt_file.name}: No corresponding image found')
                        continue
                    
                    # Get image dimensions
                    from PIL import Image
                    with Image.open(image_path) as img:
                        img_width, img_height = img.size
                    
                    # Create XML structure
                    annotation = ET.Element('annotation')
                    
                    ET.SubElement(annotation, 'folder').text = 'images'
                    ET.SubElement(annotation, 'filename').text = image_path.name
                    ET.SubElement(annotation, 'path').text = str(image_path)
                    
                    source = ET.SubElement(annotation, 'source')
                    ET.SubElement(source, 'database').text = 'Unknown'
                    
                    size = ET.SubElement(annotation, 'size')
                    ET.SubElement(size, 'width').text = str(img_width)
                    ET.SubElement(size, 'height').text = str(img_height)
                    ET.SubElement(size, 'depth').text = '3'
                    
                    ET.SubElement(annotation, 'segmented').text = '0'
                    
                    # Read YOLO annotations
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        parts = line.split()
                        if len(parts) != 5:
                            continue
                        
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        
                        # Convert from YOLO to VOC format
                        xmin = int((x_center - width / 2) * img_width)
                        ymin = int((y_center - height / 2) * img_height)
                        xmax = int((x_center + width / 2) * img_width)
                        ymax = int((y_center + height / 2) * img_height)
                        
                        # Ensure bounds
                        xmin = max(0, xmin)
                        ymin = max(0, ymin)
                        xmax = min(img_width, xmax)
                        ymax = min(img_height, ymax)
                        
                        # Get class name
                        if class_id >= len(self.classes):
                            errors.append(f'{txt_file.name}: Invalid class ID {class_id}')
                            continue
                        
                        class_name = self.classes[class_id]
                        
                        # Create object element
                        obj = ET.SubElement(annotation, 'object')
                        ET.SubElement(obj, 'name').text = class_name
                        ET.SubElement(obj, 'pose').text = 'Unspecified'
                        ET.SubElement(obj, 'truncated').text = '0'
                        ET.SubElement(obj, 'difficult').text = '0'
                        
                        bndbox = ET.SubElement(obj, 'bndbox')
                        ET.SubElement(bndbox, 'xmin').text = str(xmin)
                        ET.SubElement(bndbox, 'ymin').text = str(ymin)
                        ET.SubElement(bndbox, 'xmax').text = str(xmax)
                        ET.SubElement(bndbox, 'ymax').text = str(ymax)
                    
                    # Write XML file
                    tree = ET.ElementTree(annotation)
                    ET.indent(tree, space='  ')
                    output_file = Path(output_dir) / f'{txt_file.stem}.xml'
                    tree.write(output_file, encoding='utf-8', xml_declaration=True)
                    
                    converted_count += 1
                    
                except Exception as e:
                    skipped_count += 1
                    errors.append(f'{txt_file.name}: {str(e)}')
            
            return {
                'success': True,
                'converted': converted_count,
                'skipped': skipped_count,
                'total': len(txt_files),
                'classes': self.classes,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }