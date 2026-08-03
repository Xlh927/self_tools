"""
Dataset Augmentor
数据集增强工具 - 通过图像变换扩充数据集
"""

import os
import cv2
import numpy as np
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, List, Dict, Tuple
from PIL import Image
import random
import concurrent.futures
import shutil

try:
    from parallelism_config import get_executor_plan
except Exception:  # pragma: no cover - import path differs by runtime entrypoint
    from backend.parallelism_config import get_executor_plan

class DataAugmentor:
    """数据集增强器 - 支持多种增强方法和标注格式"""
    
    def __init__(self):
        self.supported_formats = ['voc', 'yolo']
    
    @staticmethod
    def _augment_single_image_task(img_file: Path, config: Dict) -> Dict:
        """Helper task for multiprocessing to augment a single image"""
        try:
            images_dir = config['images_dir']
            annotations_dir = config['annotations_dir']
            output_dir = config['output_dir']
            annotation_format = config.get('annotation_format', 'voc')
            augmentations = config.get('augmentations', [])
            
            # Create sub-output directories (already created by main process but good to be sure if used independently)
            images_output = Path(output_dir) / 'images'
            if annotation_format == 'yolo':
                annotations_output = Path(output_dir) / 'labels'
            else:
                annotations_output = Path(output_dir) / 'xmls'
            
            # Read image
            image = cv2.imread(str(img_file))
            if image is None:
                return {'success': False, 'image': img_file.name, 'error': '无法读取图片'}
            
            # Read annotation
            if annotation_format == 'voc':
                annotation_file = Path(annotations_dir) / f'{img_file.stem}.xml'
            else:
                annotation_file = Path(annotations_dir) / f'{img_file.stem}.txt'
            
            if not annotation_file.exists():
                return {'success': False, 'image': img_file.name, 'error': '未找到对应的标注文件'}
            
            # Create an instance of DataAugmentor for helper methods (non-multiprocessing methods are fine)
            augmentor = DataAugmentor()
            generated_count = 0
            
            # Copy original image and annotation
            cv2.imwrite(str(images_output / img_file.name), image)
            shutil.copy(annotation_file, annotations_output / annotation_file.name)
            
            # Apply augmentations
            for aug_config in augmentations:
                aug_name, _params = augmentor.normalize_augmentation_config(aug_config)
                if not aug_name:
                    continue
                aug_image, aug_annotations = augmentor.apply_augmentation(
                    image, annotation_file, aug_config, annotation_format
                )
                
                if aug_image is not None:
                    aug_filename = f'{img_file.stem}_{aug_name}{img_file.suffix}'
                    cv2.imwrite(str(images_output / aug_filename), aug_image)
                    
                    if annotation_format == 'voc':
                        augmentor.save_voc_annotation(
                            aug_annotations, 
                            annotations_output / f'{img_file.stem}_{aug_name}.xml',
                            aug_filename,
                            aug_image.shape
                        )
                    else:
                        augmentor.save_yolo_annotation(
                            aug_annotations,
                            annotations_output / f'{img_file.stem}_{aug_name}.txt',
                            aug_image.shape
                        )
                    generated_count += 1
            
            return {'success': True, 'image': img_file.name, 'generated': generated_count}
            
        except Exception as e:
            return {'success': False, 'image': img_file.name, 'error': str(e)}

    def augment_dataset(self, config: Dict, progress_callback=None) -> Dict:
        """
        批量增强数据集
        
        Args:
            config: 配置字典，包含：
                - images_dir: 图片目录
                - annotations_dir: 标注目录
                - output_dir: 输出目录
                - annotation_format: 标注格式 ('voc' 或 'yolo')
                - augmentations: 增强方法列表
                - classes_file: YOLO格式的类别文件（可选）
        
        Returns:
            结果字典
        """
        try:
            images_dir = config['images_dir']
            annotations_dir = config['annotations_dir']
            output_dir = config['output_dir']
            annotation_format = config.get('annotation_format', 'voc')
            augmentations = config.get('augmentations', [])
            classes_file = config.get('classes_file')
            
            if annotation_format not in self.supported_formats:
                return {
                    'success': False,
                    'error': f'不支持的标注格式: {annotation_format}'
                }
            
            # 创建输出目录
            images_output = Path(output_dir) / 'images'
            # 根据标注格式使用不同的文件夹名称
            if annotation_format == 'yolo':
                annotations_output = Path(output_dir) / 'labels'
            else:  # voc
                annotations_output = Path(output_dir) / 'xmls'
            images_output.mkdir(parents=True, exist_ok=True)
            annotations_output.mkdir(parents=True, exist_ok=True)
            
            # 获取图片文件列表
            image_files = []
            for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                image_files.extend(Path(images_dir).glob(f'*{ext}'))
                image_files.extend(Path(images_dir).glob(f'*{ext.upper()}'))
            
            if not image_files:
                return {
                    'success': False,
                    'error': f'在 {images_dir} 中未找到图片文件'
                }
            
            processed = 0
            generated = 0
            errors = []
            
            plan = get_executor_plan(len(image_files), workload='cpu', prefer_process=True)
            if plan.kind == 'serial':
                for img_file in image_files:
                    try:
                        result = self._augment_single_image_task(img_file, config)
                        if result['success']:
                            processed += 1
                            generated += result['generated']
                        else:
                            errors.append(f"{result['image']}: {result['error']}")
                    except Exception as e:
                        errors.append(f"{img_file.name}: {str(e)}")

                    if progress_callback:
                        progress_callback(processed, len(image_files), f"Augmenting {img_file.name}")
            else:
                executor_cls = (
                    concurrent.futures.ProcessPoolExecutor
                    if plan.kind == 'process'
                    else concurrent.futures.ThreadPoolExecutor
                )
                with executor_cls(max_workers=plan.workers) as executor:
                    future_to_img = {
                        executor.submit(self._augment_single_image_task, img_file, config): img_file
                        for img_file in image_files
                    }

                    for future in concurrent.futures.as_completed(future_to_img):
                        img_file = future_to_img[future]
                        try:
                            result = future.result()
                            if result['success']:
                                processed += 1
                                generated += result['generated']
                            else:
                                errors.append(f"{result['image']}: {result['error']}")
                        except Exception as e:
                            errors.append(f"{img_file.name}: {str(e)}")

                        if progress_callback:
                            progress_callback(processed, len(image_files), f"Augmenting {img_file.name}")
            
            # If YOLO format, copy classes.txt
            if annotation_format == 'yolo' and classes_file and os.path.exists(classes_file):
                shutil.copy(classes_file, annotations_output / 'classes.txt')
            
            return {
                'success': True,
                'processed': processed,
                'generated': generated,
                'total_images': processed + generated,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def normalize_augmentation_config(self, aug_config: Any) -> Tuple[str, Dict]:
        """兼容旧字符串格式和新的带参数对象格式。"""
        if isinstance(aug_config, str):
            return aug_config, {}
        if isinstance(aug_config, dict):
            name = aug_config.get('name') or aug_config.get('key') or ''
            params = {k: v for k, v in aug_config.items() if k not in ('name', 'key')}
            return name, params
        return '', {}

    def get_float_param(self, params: Dict, name: str, default: float, min_value: float, max_value: float) -> float:
        try:
            value = float(params.get(name, default))
        except (TypeError, ValueError):
            value = default
        return max(min_value, min(max_value, value))

    def get_int_param(self, params: Dict, name: str, default: int, allowed_values=None) -> int:
        try:
            value = int(params.get(name, default))
        except (TypeError, ValueError):
            value = default
        if allowed_values and value not in allowed_values:
            return default
        return value

    def get_range_param(
        self,
        params: Dict,
        min_name: str,
        max_name: str,
        default_min: float,
        default_max: float,
        lower_bound: float,
        upper_bound: float,
    ) -> Tuple[float, float]:
        min_value = self.get_float_param(params, min_name, default_min, lower_bound, upper_bound)
        max_value = self.get_float_param(params, max_name, default_max, lower_bound, upper_bound)
        if min_value > max_value:
            min_value, max_value = max_value, min_value
        return min_value, max_value

    def apply_augmentation(self, image: np.ndarray, annotation_file: Path,
                          aug_config: Any, annotation_format: str) -> Tuple:
        """应用指定的增强方法"""
        aug_name, params = self.normalize_augmentation_config(aug_config)
        
        # 读取标注
        if annotation_format == 'voc':
            annotations = self.read_voc_annotation(annotation_file)
        else:
            annotations = self.read_yolo_annotation(annotation_file, image.shape)
        
        if aug_name == 'hflip':
            return self.horizontal_flip(image, annotations)
        elif aug_name == 'vflip':
            return self.vertical_flip(image, annotations)
        elif aug_name == 'rotate90':
            return self.rotate_90(image, annotations)
        elif aug_name == 'rotate180':
            return self.rotate_180(image, annotations)
        elif aug_name == 'rotate270':
            return self.rotate_270(image, annotations)
        elif aug_name == 'stretch_width':
            min_scale, max_scale = self.get_range_param(params, 'min', 'max', 0.8, 1.2, 0.5, 2.0)
            return self.stretch_width(image, annotations, min_scale, max_scale)
        elif aug_name == 'stretch_height':
            min_scale, max_scale = self.get_range_param(params, 'min', 'max', 0.9, 1.1, 0.5, 2.0)
            return self.stretch_height(image, annotations, min_scale, max_scale)
        elif aug_name == 'brightness':
            factor_min, factor_max = self.get_range_param(params, 'min', 'max', 0.7, 1.3, 0.1, 3.0)
            return self.adjust_brightness_range(image, annotations, factor_min, factor_max)
        elif aug_name == 'contrast':
            factor_min, factor_max = self.get_range_param(params, 'min', 'max', 0.7, 1.3, 0.1, 3.0)
            return self.adjust_contrast_range(image, annotations, factor_min, factor_max)
        elif aug_name == 'brightness_up':
            factor = self.get_float_param(params, 'factor', 1.3, 1.0, 3.0)
            return self.adjust_brightness(image, annotations, factor)
        elif aug_name == 'brightness_down':
            factor = self.get_float_param(params, 'factor', 0.7, 0.1, 1.0)
            return self.adjust_brightness(image, annotations, factor)
        elif aug_name == 'contrast_up':
            factor = self.get_float_param(params, 'factor', 1.3, 1.0, 3.0)
            return self.adjust_contrast(image, annotations, factor)
        elif aug_name == 'contrast_down':
            factor = self.get_float_param(params, 'factor', 0.7, 0.1, 1.0)
            return self.adjust_contrast(image, annotations, factor)
        elif aug_name == 'noise':
            var_min, var_max = self.get_range_param(params, 'var_min', 'var_max', 0.0, 15.0, 0.0, 100.0)
            return self.add_noise(image, annotations, var_min, var_max)
        elif aug_name == 'blur':
            kernel = self.get_int_param(params, 'kernel', 3, allowed_values=(3, 5, 7))
            return self.apply_blur(image, annotations, kernel)
        else:
            return None, None
    
    # ============ 几何变换 ============
    
    def horizontal_flip(self, image: np.ndarray, annotations: List[Dict]) -> Tuple:
        """水平翻转"""
        h, w = image.shape[:2]
        flipped_image = cv2.flip(image, 1)
        flipped_annotations = []
        
        for ann in annotations:
            xmin, ymin, xmax, ymax = ann['bbox']
            new_annotation = ann.copy()
            new_annotation['bbox'] = [w - xmax, ymin, w - xmin, ymax]
            flipped_annotations.append(new_annotation)
        
        return flipped_image, flipped_annotations
    
    def vertical_flip(self, image: np.ndarray, annotations: List[Dict]) -> Tuple:
        """垂直翻转"""
        h, w = image.shape[:2]
        flipped_image = cv2.flip(image, 0)
        flipped_annotations = []
        
        for ann in annotations:
            xmin, ymin, xmax, ymax = ann['bbox']
            new_annotation = ann.copy()
            new_annotation['bbox'] = [xmin, h - ymax, xmax, h - ymin]
            flipped_annotations.append(new_annotation)
        
        return flipped_image, flipped_annotations
    
    def rotate_90(self, image: np.ndarray, annotations: List[Dict]) -> Tuple:
        """顺时针旋转90度"""
        h, w = image.shape[:2]
        rotated_image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        rotated_annotations = []
        
        for ann in annotations:
            xmin, ymin, xmax, ymax = ann['bbox']
            new_annotation = ann.copy()
            # 旋转90度后: (x, y) -> (h - y, x)
            new_annotation['bbox'] = [h - ymax, xmin, h - ymin, xmax]
            rotated_annotations.append(new_annotation)
        
        return rotated_image, rotated_annotations
    
    def rotate_180(self, image: np.ndarray, annotations: List[Dict]) -> Tuple:
        """旋转180度"""
        h, w = image.shape[:2]
        rotated_image = cv2.rotate(image, cv2.ROTATE_180)
        rotated_annotations = []
        
        for ann in annotations:
            xmin, ymin, xmax, ymax = ann['bbox']
            new_annotation = ann.copy()
            new_annotation['bbox'] = [w - xmax, h - ymax, w - xmin, h - ymin]
            rotated_annotations.append(new_annotation)
        
        return rotated_image, rotated_annotations
    
    def rotate_270(self, image: np.ndarray, annotations: List[Dict]) -> Tuple:
        """顺时针旋转270度"""
        h, w = image.shape[:2]
        rotated_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        rotated_annotations = []
        
        for ann in annotations:
            xmin, ymin, xmax, ymax = ann['bbox']
            new_annotation = ann.copy()
            # 旋转270度后: (x, y) -> (y, w - x)
            new_annotation['bbox'] = [ymin, w - xmax, ymax, w - xmin]
            rotated_annotations.append(new_annotation)
        
        return rotated_image, rotated_annotations

    def stretch_width(
        self,
        image: np.ndarray,
        annotations: List[Dict],
        min_scale: float = 0.8,
        max_scale: float = 1.2,
    ) -> Tuple:
        """宽度方向拉伸"""
        return self.scale_axis(image, annotations, x_range=(min_scale, max_scale), y_range=(1.0, 1.0))

    def stretch_height(
        self,
        image: np.ndarray,
        annotations: List[Dict],
        min_scale: float = 0.9,
        max_scale: float = 1.1,
    ) -> Tuple:
        """高度方向拉伸"""
        return self.scale_axis(image, annotations, x_range=(1.0, 1.0), y_range=(min_scale, max_scale))

    def scale_axis(
        self,
        image: np.ndarray,
        annotations: List[Dict],
        x_range: Tuple[float, float],
        y_range: Tuple[float, float],
    ) -> Tuple:
        """按单轴随机缩放图片，并同步缩放标注框坐标。"""
        h, w = image.shape[:2]
        scale_x = random.uniform(*x_range)
        scale_y = random.uniform(*y_range)
        new_w = max(1, int(round(w * scale_x)))
        new_h = max(1, int(round(h * scale_y)))
        actual_scale_x = new_w / w
        actual_scale_y = new_h / h
        scaled_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        scaled_annotations = []
        for ann in annotations:
            xmin, ymin, xmax, ymax = ann['bbox']
            new_annotation = ann.copy()
            new_annotation['bbox'] = [
                xmin * actual_scale_x,
                ymin * actual_scale_y,
                xmax * actual_scale_x,
                ymax * actual_scale_y,
            ]
            scaled_annotations.append(new_annotation)

        return scaled_image, scaled_annotations
    
    # ============ 颜色调整与特效 ============
    
    def adjust_brightness(self, image: np.ndarray, annotations: List[Dict], factor: float) -> Tuple:
        """调整亮度"""
        adjusted = cv2.convertScaleAbs(image, alpha=factor, beta=0)
        return adjusted, annotations

    def adjust_brightness_range(
        self,
        image: np.ndarray,
        annotations: List[Dict],
        factor_min: float = 0.7,
        factor_max: float = 1.3,
    ) -> Tuple:
        """在指定范围内随机调整亮度"""
        return self.adjust_brightness(image, annotations, random.uniform(factor_min, factor_max))
    
    def adjust_contrast(self, image: np.ndarray, annotations: List[Dict], factor: float) -> Tuple:
        """调整对比度"""
        mean = np.mean(image)
        adjusted = cv2.convertScaleAbs(image, alpha=factor, beta=(1 - factor) * mean)
        return adjusted, annotations

    def adjust_contrast_range(
        self,
        image: np.ndarray,
        annotations: List[Dict],
        factor_min: float = 0.7,
        factor_max: float = 1.3,
    ) -> Tuple:
        """在指定范围内随机调整对比度"""
        return self.adjust_contrast(image, annotations, random.uniform(factor_min, factor_max))
        
    def add_noise(
        self,
        image: np.ndarray,
        annotations: List[Dict],
        var_min: float = 0.0,
        var_max: float = 15.0,
    ) -> Tuple:
        """添加高斯噪声"""
        variance = random.uniform(var_min, var_max)
        sigma = variance ** 0.5
        gauss = np.random.normal(0, sigma, image.shape)
        noisy = image.astype(np.float32) + gauss
        noisy = np.clip(noisy, 0, 255).astype(np.uint8)
        return noisy, annotations
        
    def apply_blur(self, image: np.ndarray, annotations: List[Dict], kernel: int = 3) -> Tuple:
        """应用高斯模糊"""
        blurred = cv2.GaussianBlur(image, (kernel, kernel), 0)
        return blurred, annotations
    
    # ============ 标注文件处理 ============
    
    def read_voc_annotation(self, xml_file: Path) -> List[Dict]:
        """读取VOC格式标注"""
        tree = ET.parse(xml_file)
        root = tree.getroot()
        annotations = []
        
        for obj in root.findall('object'):
            name = obj.find('name').text
            bbox = obj.find('bndbox')
            xmin = float(bbox.find('xmin').text)
            ymin = float(bbox.find('ymin').text)
            xmax = float(bbox.find('xmax').text)
            ymax = float(bbox.find('ymax').text)
            
            annotations.append({
                'class_name': name,
                'bbox': [xmin, ymin, xmax, ymax]
            })
        
        return annotations
    
    def read_yolo_annotation(self, txt_file: Path, image_shape: Tuple) -> List[Dict]:
        """读取YOLO格式标注"""
        h, w = image_shape[:2]
        annotations = []
        
        with open(txt_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    x_center = float(parts[1]) * w
                    y_center = float(parts[2]) * h
                    width = float(parts[3]) * w
                    height = float(parts[4]) * h
                    
                    xmin = x_center - width / 2
                    ymin = y_center - height / 2
                    xmax = x_center + width / 2
                    ymax = y_center + height / 2
                    
                    annotations.append({
                        'class_id': class_id,
                        'bbox': [xmin, ymin, xmax, ymax]
                    })
        
        return annotations
    
    def save_voc_annotation(self, annotations: List[Dict], output_file: Path, 
                           image_filename: str, image_shape: Tuple):
        """保存VOC格式标注"""
        h, w = image_shape[:2]
        
        annotation = ET.Element('annotation')
        ET.SubElement(annotation, 'folder').text = 'images'
        ET.SubElement(annotation, 'filename').text = image_filename
        
        size = ET.SubElement(annotation, 'size')
        ET.SubElement(size, 'width').text = str(w)
        ET.SubElement(size, 'height').text = str(h)
        ET.SubElement(size, 'depth').text = '3'
        
        for ann in annotations:
            obj = ET.SubElement(annotation, 'object')
            ET.SubElement(obj, 'name').text = ann['class_name']
            ET.SubElement(obj, 'pose').text = 'Unspecified'
            ET.SubElement(obj, 'truncated').text = '0'
            ET.SubElement(obj, 'difficult').text = '0'
            
            bndbox = ET.SubElement(obj, 'bndbox')
            xmin, ymin, xmax, ymax = ann['bbox']
            ET.SubElement(bndbox, 'xmin').text = str(int(xmin))
            ET.SubElement(bndbox, 'ymin').text = str(int(ymin))
            ET.SubElement(bndbox, 'xmax').text = str(int(xmax))
            ET.SubElement(bndbox, 'ymax').text = str(int(ymax))
        
        tree = ET.ElementTree(annotation)
        ET.indent(tree, space='  ')
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
    
    def save_yolo_annotation(self, annotations: List[Dict], output_file: Path, image_shape: Tuple):
        """保存YOLO格式标注"""
        h, w = image_shape[:2]
        lines = []
        
        for ann in annotations:
            class_id = ann['class_id']
            xmin, ymin, xmax, ymax = ann['bbox']
            
            # 转换为YOLO归一化格式
            x_center = ((xmin + xmax) / 2) / w
            y_center = ((ymin + ymax) / 2) / h
            width = (xmax - xmin) / w
            height = (ymax - ymin) / h
            
            lines.append(f'{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}')
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))
