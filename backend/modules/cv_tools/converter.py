"""
Dataset Format Converter
Supports bidirectional conversion between VOC and YOLO formats
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict
import concurrent.futures
import multiprocessing
from PIL import Image


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
    
    @staticmethod
    def _voc_to_yolo_task(xml_file: Path, output_dir: str, img_width: int, img_height: int, custom_class_mapping: Dict[str, int], classes: List[str]) -> Tuple[bool, str]:
        """Helper task for multiprocessing to convert one VOC file"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            yolo_annotations = []
            
            for obj in root.findall('object'):
                class_name = obj.find('name').text
                if custom_class_mapping:
                    if class_name not in custom_class_mapping:
                        continue
                    class_id = custom_class_mapping[class_name]
                else:
                    if class_name not in classes:
                        # This case is tricky with parallel detection, 
                        # but usually classes are pre-scanned or provided.
                        continue
                    class_id = classes.index(class_name)
                
                bbox = obj.find('bndbox')
                xmin = float(bbox.find('xmin').text)
                ymin = float(bbox.find('ymin').text)
                xmax = float(bbox.find('xmax').text)
                ymax = float(bbox.find('ymax').text)
                
                x_center = ((xmin + xmax) / 2) / img_width
                y_center = ((ymin + ymax) / 2) / img_height
                width = (xmax - xmin) / img_width
                height = (ymax - ymin) / img_height
                
                yolo_annotations.append(f'{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}')
            
            output_file = Path(output_dir) / f'{xml_file.stem}.txt'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(yolo_annotations))
            return True, ""
        except Exception as e:
            return False, f"{xml_file.name}: {str(e)}"

    def voc_to_yolo(self, voc_xml_dir: str, images_dir: str, output_dir: str, 
                    classes_file: str = None, custom_class_mapping: Dict[str, int] = None,
                    progress_callback=None) -> Dict[str, any]:
        """
        Convert VOC format to YOLO format
        
        Args:
            voc_xml_dir: Directory containing VOC XML annotation files
            images_dir: Directory containing images
            output_dir: Output directory for YOLO txt files
            classes_file: Path to classes.txt file (optional)
            custom_class_mapping: Dictionary mapping class_name to class_id (optional)
            progress_callback: Optional function(current, total, message)
            
        Returns:
            Dictionary with conversion results
        """
        try:
            # If custom mapping is provided, use it to set up classes
            if custom_class_mapping:
                # Sort by index to create the classes list
                max_idx = max(custom_class_mapping.values())
                self.classes = [''] * (max_idx + 1)
                for class_name, idx in custom_class_mapping.items():
                    self.classes[idx] = class_name
            # Load classes if provided
            elif classes_file and os.path.exists(classes_file):
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
            
            # Map for dimensions
            xml_data = []
            for xml_file in xml_files:
                try:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    size = root.find('size')
                    if size is None:
                        skipped_count += 1
                        errors.append(f'{xml_file.name}: Missing size element')
                        continue
                    img_width = int(size.find('width').text)
                    img_height = int(size.find('height').text)
                    xml_data.append((xml_file, img_width, img_height))
                except Exception as e:
                    skipped_count += 1
                    errors.append(f'{xml_file.name}: {str(e)}')

            # Run parallel
            num_workers = min(multiprocessing.cpu_count(), len(xml_data))
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = {
                    executor.submit(
                        self._voc_to_yolo_task, 
                        item[0], output_dir, item[1], item[2], 
                        custom_class_mapping, self.classes
                    ): item[0] for item in xml_data
                }
                
                for future in concurrent.futures.as_completed(futures):
                    success, error_msg = future.result()
                    if success:
                        converted_count += 1
                    else:
                        skipped_count += 1
                        errors.append(error_msg)
                    
                    if progress_callback:
                        progress_callback(converted_count + skipped_count, len(xml_files), f"Processed {futures[future].name}")
            
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
    
    def scan_voc_classes(self, voc_xml_dir: str) -> Dict[str, any]:
        """
        扫描VOC格式XML文件,提取所有存在的类别名称及其出现次数
        
        Args:
            voc_xml_dir: Directory containing VOC XML annotation files
            
        Returns:
            Dictionary with 'success', 'classes' (list of {name, count, index}), 'error'
        """
        try:
            class_counts = {}
            xml_files = list(Path(voc_xml_dir).glob('*.xml'))
            
            if not xml_files:
                return {
                    'success': False,
                    'error': f'No XML files found in {voc_xml_dir}'
                }
            
            for xml_file in xml_files:
                try:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    
                    for obj in root.findall('object'):
                        name_elem = obj.find('name')
                        if name_elem is not None and name_elem.text:
                            class_name = name_elem.text.strip()
                            class_counts[class_name] = class_counts.get(class_name, 0) + 1
                except Exception:
                    continue
            
            # Convert to list of dicts with default indices sorted alphabetically
            sorted_classes = sorted(class_counts.keys())
            classes_list = [
                {
                    'name': class_name,
                    'count': class_counts[class_name],
                    'index': idx
                }
                for idx, class_name in enumerate(sorted_classes)
            ]
            
            return {
                'success': True,
                'classes': classes_list,
                'total_files': len(xml_files)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def scan_yolo_classes(self, yolo_txt_dir: str) -> Dict[int, int]:
        """
        扫描YOLO格式文件,提取所有存在的类别ID及其出现次数
        
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
    
    @staticmethod
    def _yolo_to_voc_task(txt_file: Path, images_dir: str, output_dir: str, classes: List[str]) -> Tuple[bool, str]:
        """Helper task for multiprocessing to convert one YOLO file"""
        try:
            image_path = None
            for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                potential_path = Path(images_dir) / f'{txt_file.stem}{ext}'
                if potential_path.exists():
                    image_path = potential_path
                    break
            
            if not image_path:
                return False, f'{txt_file.name}: No corresponding image found'
            
            with Image.open(image_path) as img:
                img_width, img_height = img.size
            
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
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    parts = line.split()
                    if len(parts) != 5: continue
                    
                    class_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    
                    xmin = int((x_center - width / 2) * img_width)
                    ymin = int((y_center - height / 2) * img_height)
                    xmax = int((x_center + width / 2) * img_width)
                    ymax = int((y_center + height / 2) * img_height)
                    
                    xmin = max(0, xmin); ymin = max(0, ymin); xmax = min(img_width, xmax); ymax = min(img_height, ymax)
                    
                    if class_id >= len(classes): continue
                    class_name = classes[class_id]
                    
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
            
            tree = ET.ElementTree(annotation)
            ET.indent(tree, space='  ')
            output_file = Path(output_dir) / f'{txt_file.stem}.xml'
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
            return True, ""
        except Exception as e:
            return False, f"{txt_file.name}: {str(e)}"

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
            
            num_workers = min(multiprocessing.cpu_count(), len(txt_files))
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = {
                    executor.submit(
                        self._yolo_to_voc_task, 
                        txt_file, images_dir, output_dir, self.classes
                    ): txt_file for txt_file in txt_files
                }
                
                for future in concurrent.futures.as_completed(futures):
                    success, error_msg = future.result()
                    if success:
                        converted_count += 1
                    else:
                        skipped_count += 1
                        errors.append(error_msg)
                    
                    if progress_callback:
                        progress_callback(converted_count + skipped_count, len(txt_files), f"Processed {futures[future].name}")
            
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