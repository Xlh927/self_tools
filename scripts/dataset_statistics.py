#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集统计与可视化模块（B4）

功能：
- 类别分布统计与可视化
- 图片宽高分布统计与可视化
- 标注数量统计（按图/按类）
- 异常图（极端尺寸等）检测
- 图像格式与大小分析
- 边界框统计（面积分布、宽高比等）
- 支持单文件和批量文件夹处理
- 支持YOLO、Pascal VOC、COCO等多种标注格式

本模块提供全面的数据集分析功能，帮助用户快速了解数据集特征，发现潜在问题。
"""

import os
import sys
import argparse
import json
import xml.etree.ElementTree as ET
import glob
import logging
from typing import List, Dict, Any, Tuple, Set, Optional, Union
from collections import defaultdict, Counter
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import cv2
from PIL import Image
import pandas as pd
from tqdm import tqdm


class DatasetStatisticsAnalyzer:
    """
    数据集统计分析器类
    """
    
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or "stats_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 统计结果存储
        self.stats = {
            "dataset_info": {
                "name": None,
                "path": None,
                "total_files": 0,
                "total_size_bytes": 0,
                "file_formats": {},
                "directory_count": 0
            },
            "image_stats": {
                "total_images": 0,
                "formats": {},
                "resolutions": [],
                "widths": [],
                "heights": [],
                "aspect_ratios": [],
                "sizes_bytes": [],
                "channels": {},
                "color_distributions": {}
            },
            "annotation_stats": {
                "total_annotations": 0,
                "annotation_types": {},
                "class_distribution": {},
                "bbox_statistics": {},
                "annotations_per_file": []
            }
        }
        
        # 支持的图像格式
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'}
        # 支持的标注格式
        self.annotation_extensions = {'.txt', '.xml', '.json', '.csv', '.yaml', '.yml'}
    
    def collect_files(self, input_path, recursive=False):
        """
        收集文件列表
        """
        files = []
        directory_count = 0
        
        if os.path.isfile(input_path):
            files.append(input_path)
        elif os.path.isdir(input_path):
            for root, dirs, filenames in os.walk(input_path):
                directory_count += len(dirs)
                for filename in filenames:
                    files.append(os.path.join(root, filename))
                if not recursive:
                    break
        
        self.stats["dataset_info"]["total_files"] = len(files)
        self.stats["dataset_info"]["path"] = input_path
        self.stats["dataset_info"]["directory_count"] = directory_count
        
        return files
    
    def analyze_basic_stats(self, file_list):
        """
        分析基本统计信息
        """
        total_size = 0
        formats = Counter()
        
        for file_path in file_list:
            try:
                # 获取文件大小
                file_size = os.path.getsize(file_path)
                total_size += file_size
                
                # 获取文件扩展名
                ext = os.path.splitext(file_path)[1].lower()
                formats[ext] += 1
            except Exception as e:
                logger.error(f"分析文件失败 {file_path}: {str(e)}")
        
        # 更新统计信息
        self.stats["dataset_info"]["total_size_bytes"] = total_size
        self.stats["dataset_info"]["file_formats"] = dict(formats)
        
        # 计算平均文件大小
        if len(file_list) > 0:
            avg_size = total_size / len(file_list)
            self.stats["dataset_info"]["average_file_size_bytes"] = avg_size

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def ensure_directory(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"创建目录: {directory}")


def load_image_paths(image_dir: str, recursive: bool = False) -> List[str]:
    """
    加载图像文件路径
    
    Args:
        image_dir: 图像目录
        recursive: 是否递归搜索子目录
    
    Returns:
        图像文件路径列表
    """
    supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_paths = []
    
    if recursive:
        pattern = os.path.join(image_dir, '**', '*')
    else:
        pattern = os.path.join(image_dir, '*')
    
    for file_path in glob.glob(pattern, recursive=recursive):
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext in supported_extensions:
                image_paths.append(file_path)
    
    logger.info(f"找到 {len(image_paths)} 个图像文件")
    return image_paths


def get_label_path(image_path: str, label_dir: str, label_extension: str = '.txt') -> str:
    """
    根据图像路径获取对应的标签路径
    
    Args:
        image_path: 图像路径
        label_dir: 标签目录
        label_extension: 标签文件扩展名
    
    Returns:
        标签文件路径
    """
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    return os.path.join(label_dir, image_name + label_extension)


def read_yolo_label(label_path: str) -> List[Dict[str, Any]]:
    """
    读取YOLO格式标签
    
    Args:
        label_path: 标签文件路径
    
    Returns:
        标注列表 [{'class_id': int, 'bbox': [x_center, y_center, width, height], 'area': float}, ...]
    """
    annotations = []
    if not os.path.exists(label_path):
        return annotations
    
    try:
        with open(label_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    try:
                        class_id = int(float(parts[0]))
                        bbox = list(map(float, parts[1:5]))
                        # 计算归一化面积
                        area = bbox[2] * bbox[3]
                        annotations.append({
                            'class_id': class_id,
                            'bbox': bbox,
                            'area': area
                        })
                    except ValueError:
                        continue
    except Exception as e:
        logger.error(f"读取YOLO标签文件失败 {label_path}: {str(e)}")
    
    return annotations


def read_pascal_voc_label(label_path: str) -> List[Dict[str, Any]]:
    """
    读取Pascal VOC格式标签
    
    Args:
        label_path: 标签文件路径
    
    Returns:
        标注列表 [{'class_name': str, 'bbox': [xmin, ymin, xmax, ymax], 'area': float}, ...]
    """
    annotations = []
    if not os.path.exists(label_path):
        return annotations
    
    try:
        tree = ET.parse(label_path)
        root = tree.getroot()
        
        # 获取图像尺寸
        width = height = 1  # 默认值
        size_elem = root.find('size')
        if size_elem is not None:
            width_elem = size_elem.find('width')
            height_elem = size_elem.find('height')
            if width_elem is not None and width_elem.text:
                width = float(width_elem.text)
            if height_elem is not None and height_elem.text:
                height = float(height_elem.text)
        
        for obj in root.findall('object'):
            name_elem = obj.find('name')
            if name_elem is None or not name_elem.text:
                continue
            
            class_name = name_elem.text.strip()
            
            bndbox = obj.find('bndbox')
            if bndbox is None:
                continue
            
            xmin_elem = bndbox.find('xmin')
            ymin_elem = bndbox.find('ymin')
            xmax_elem = bndbox.find('xmax')
            ymax_elem = bndbox.find('ymax')
            
            if not all([xmin_elem, ymin_elem, xmax_elem, ymax_elem]):
                continue
            
            try:
                xmin = float(xmin_elem.text)
                ymin = float(ymin_elem.text)
                xmax = float(xmax_elem.text)
                ymax = float(ymax_elem.text)
                
                # 计算面积
                width_pixel = xmax - xmin
                height_pixel = ymax - ymin
                area = width_pixel * height_pixel
                
                annotations.append({
                    'class_name': class_name,
                    'bbox': [xmin, ymin, xmax, ymax],
                    'area': area,
                    'area_normalized': area / (width * height) if width * height > 0 else 0
                })
            except ValueError:
                continue
    except Exception as e:
        logger.error(f"读取Pascal VOC标签文件失败 {label_path}: {str(e)}")
    
    return annotations


def read_coco_annotation(coco_json_path: str) -> Tuple[Dict[str, Any], Dict[str, List[Dict[str, Any]]]]:
    """
    读取COCO格式的标注文件
    
    Args:
        coco_json_path: COCO格式的JSON文件路径
    
    Returns:
        (数据集元数据, 图像ID到标注列表的映射)
    """
    if not os.path.exists(coco_json_path):
        logger.error(f"COCO JSON文件不存在: {coco_json_path}")
        return {}, defaultdict(list)
    
    try:
        with open(coco_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 构建类别ID到名称的映射
        categories = {cat['id']: cat['name'] for cat in data.get('categories', [])}
        
        # 构建图像ID到图像信息的映射
        images = {img['id']: img for img in data.get('images', [])}
        
        # 构建图像ID到标注列表的映射
        image_to_annotations = defaultdict(list)
        for annotation in data.get('annotations', []):
            image_id = annotation.get('image_id')
            category_id = annotation.get('category_id')
            
            if image_id in images and category_id in categories:
                # 计算归一化面积
                img_width = images[image_id].get('width', 1)
                img_height = images[image_id].get('height', 1)
                area = annotation.get('area', 0)
                area_normalized = area / (img_width * img_height) if img_width * img_height > 0 else 0
                
                image_to_annotations[image_id].append({
                    'class_id': category_id,
                    'class_name': categories[category_id],
                    'bbox': annotation.get('bbox', []),
                    'area': area,
                    'area_normalized': area_normalized,
                    'segmentation': annotation.get('segmentation', None),
                    'iscrowd': annotation.get('iscrowd', 0)
                })
        
        metadata = {
            'categories': categories,
            'images': images,
            'image_count': len(images),
            'annotation_count': len(data.get('annotations', [])),
            'category_count': len(categories)
        }
        
        return metadata, image_to_annotations
    
    except Exception as e:
        logger.error(f"读取COCO标注文件失败 {coco_json_path}: {str(e)}")
        return {}, defaultdict(list)


def analyze_image_dimensions(image_paths: List[str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    分析图像尺寸分布
    
    Args:
        image_paths: 图像路径列表
    
    Returns:
        (尺寸统计信息, 异常图像列表)
    """
    widths = []
    heights = []
    aspect_ratios = []
    areas = []
    abnormal_images = []
    
    for img_path in image_paths:
        try:
            # 使用cv2读取图像尺寸
            img = cv2.imread(img_path)
            if img is None:
                logger.warning(f"无法读取图像: {img_path}")
                abnormal_images.append({
                    'path': img_path,
                    'type': 'corrupted',
                    'reason': '无法读取图像'
                })
                continue
            
            height, width = img.shape[:2]
            aspect_ratio = width / height if height > 0 else 0
            area = width * height
            
            widths.append(width)
            heights.append(height)
            aspect_ratios.append(aspect_ratio)
            areas.append(area)
        except Exception as e:
            logger.error(f"分析图像尺寸失败 {img_path}: {str(e)}")
            abnormal_images.append({
                'path': img_path,
                'type': 'error',
                'reason': str(e)
            })
    
    # 计算统计信息
    stats = {
        'total_images': len(widths),
        'min_width': min(widths) if widths else 0,
        'max_width': max(widths) if widths else 0,
        'avg_width': np.mean(widths) if widths else 0,
        'median_width': np.median(widths) if widths else 0,
        'min_height': min(heights) if heights else 0,
        'max_height': max(heights) if heights else 0,
        'avg_height': np.mean(heights) if heights else 0,
        'median_height': np.median(heights) if heights else 0,
        'min_aspect_ratio': min(aspect_ratios) if aspect_ratios else 0,
        'max_aspect_ratio': max(aspect_ratios) if aspect_ratios else 0,
        'avg_aspect_ratio': np.mean(aspect_ratios) if aspect_ratios else 0,
        'min_area': min(areas) if areas else 0,
        'max_area': max(areas) if areas else 0,
        'avg_area': np.mean(areas) if areas else 0,
        'widths': widths,
        'heights': heights,
        'aspect_ratios': aspect_ratios,
        'areas': areas
    }
    
    # 检测异常图像（极端尺寸）
    if widths and heights:
        width_q1 = np.percentile(widths, 25)
        width_q3 = np.percentile(widths, 75)
        height_q1 = np.percentile(heights, 25)
        height_q3 = np.percentile(heights, 75)
        area_q1 = np.percentile(areas, 25)
        area_q3 = np.percentile(areas, 75)
        
        width_iqr = width_q3 - width_q1
        height_iqr = height_q3 - height_q1
        area_iqr = area_q3 - area_q1
        
        # 定义异常阈值
        width_lower = width_q1 - 3 * width_iqr
        width_upper = width_q3 + 3 * width_iqr
        height_lower = height_q1 - 3 * height_iqr
        height_upper = height_q3 + 3 * height_iqr
        area_lower = area_q1 - 3 * area_iqr
        area_upper = area_q3 + 3 * area_iqr
        
        # 重新遍历检查异常
        for i, img_path in enumerate(image_paths):
            if i >= len(widths):  # 跳过无法读取的图像
                continue
            
            width = widths[i]
            height = heights[i]
            area = areas[i]
            
            # 检查过小尺寸
            if width < 10 or height < 10:
                abnormal_images.append({
                    'path': img_path,
                    'type': 'small_size',
                    'reason': f'图像尺寸过小: {width}x{height}',
                    'width': width,
                    'height': height
                })
            # 检查过大尺寸
            elif width > 10000 or height > 10000:
                abnormal_images.append({
                    'path': img_path,
                    'type': 'large_size',
                    'reason': f'图像尺寸过大: {width}x{height}',
                    'width': width,
                    'height': height
                })
            # 检查异常比例
            elif width / max(height, 1) > 10 or height / max(width, 1) > 10:
                abnormal_images.append({
                    'path': img_path,
                    'type': 'extreme_ratio',
                    'reason': f'图像长宽比例极端: {width}x{height}, 比例={width/max(height, 1):.2f}',
                    'width': width,
                    'height': height
                })
            # 使用IQR方法检测异常
            elif (width < width_lower or width > width_upper or 
                  height < height_lower or height > height_upper or 
                  area < area_lower or area > area_upper):
                abnormal_images.append({
                    'path': img_path,
                    'type': 'outlier',
                    'reason': f'图像尺寸为离群值: {width}x{height}, 面积={area}',
                    'width': width,
                    'height': height,
                    'area': area
                })
    
    return stats, abnormal_images
def analyze_class_distribution(
    image_paths: List[str],
    label_dir: str,
    label_format: str = 'yolo',
    coco_json_path: Optional[str] = None,
    class_names: Optional[List[str]] = None
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    分析类别分布
    
    Args:
        image_paths: 图像路径列表
        label_dir: 标签目录
        label_format: 标签格式 ('yolo', 'voc', 'coco')
        coco_json_path: COCO格式的JSON文件路径
        class_names: 类别名称列表
    
    Returns:
        (类别统计信息, 类别ID到名称的映射)
    """
    class_counter = Counter()
    image_class_counter = Counter()  # 统计每个类出现在多少张图像中
    annotations_per_image = []  # 统计每张图像的标注数量
    images_without_annotations = []  # 无标注图像列表
    
    # 类别ID到名称的映射
    class_id_to_name = {}
    if class_names:
        for i, name in enumerate(class_names):
            class_id_to_name[i] = name
    
    if label_format == 'coco' and coco_json_path:
        # 处理COCO格式
        metadata, image_to_annotations = read_coco_annotation(coco_json_path)
        
        # 更新类别映射
        if 'categories' in metadata:
            class_id_to_name.update(metadata['categories'])
        
        # 创建图像文件名到ID的映射
        filename_to_id = {}
        for img_id, img_info in metadata.get('images', {}).items():
            filename = os.path.basename(img_info.get('file_name', ''))
            filename_to_id[filename] = img_id
        
        # 统计每个图像的标注
        for img_path in image_paths:
            img_filename = os.path.basename(img_path)
            img_id = filename_to_id.get(img_filename)
            
            if img_id and img_id in image_to_annotations:
                annotations = image_to_annotations[img_id]
                annotations_per_image.append(len(annotations))
                
                # 更新类别计数
                img_classes = set()
                for ann in annotations:
                    class_id = ann['class_id']
                    class_counter[class_id] += 1
                    img_classes.add(class_id)
                
                # 更新图像计数
                for class_id in img_classes:
                    image_class_counter[class_id] += 1
            else:
                annotations_per_image.append(0)
                images_without_annotations.append(img_path)
    else:
        # 处理YOLO或VOC格式
        label_ext = '.txt' if label_format == 'yolo' else '.xml'
        
        for img_path in image_paths:
            label_path = get_label_path(img_path, label_dir, label_ext)
            
            if label_format == 'yolo':
                annotations = read_yolo_label(label_path)
                img_classes = set(ann['class_id'] for ann in annotations)
            else:  # voc
                annotations = read_pascal_voc_label(label_path)
                # 对于VOC格式，我们需要创建临时类别ID
                img_classes = set()
                for ann in annotations:
                    class_name = ann['class_name']
                    # 如果没有提供类别名称映射，使用哈希值作为临时ID
                    if class_name not in class_id_to_name.values():
                        temp_id = len(class_id_to_name)
                        class_id_to_name[temp_id] = class_name
                    # 查找对应的ID
                    class_id = next((k for k, v in class_id_to_name.items() if v == class_name), len(class_id_to_name))
                    img_classes.add(class_id)
                    ann['class_id'] = class_id
            
            annotations_per_image.append(len(annotations))
            
            # 更新类别计数
            for ann in annotations:
                class_id = ann['class_id']
                class_counter[class_id] += 1
            
            # 更新图像计数
            for class_id in img_classes:
                image_class_counter[class_id] += 1
            
            if not annotations:
                images_without_annotations.append(img_path)
    
    # 计算统计信息
    total_annotations = sum(class_counter.values())
    total_images_with_annotations = len(image_paths) - len(images_without_annotations)
    
    stats = {
        'total_images': len(image_paths),
        'total_annotations': total_annotations,
        'total_categories': len(class_counter),
        'images_without_annotations': len(images_without_annotations),
        'images_with_annotations': total_images_with_annotations,
        'avg_annotations_per_image': np.mean(annotations_per_image) if annotations_per_image else 0,
        'median_annotations_per_image': np.median(annotations_per_image) if annotations_per_image else 0,
        'class_distribution': dict(class_counter),
        'images_per_class': dict(image_class_counter),
        'annotations_per_image': annotations_per_image,
        'images_without_annotations': images_without_annotations
    }
    
    return stats, class_id_to_name


def plot_class_distribution(
    class_distribution: Dict[int, int],
    class_id_to_name: Dict[int, str],
    output_path: str,
    top_n: int = 20
) -> None:
    """
    绘制类别分布图
    
    Args:
        class_distribution: 类别分布
        class_id_to_name: 类别ID到名称的映射
        output_path: 输出路径
        top_n: 只显示前N个类别
    """
    # 按数量排序
    sorted_classes = sorted(class_distribution.items(), key=lambda x: x[1], reverse=True)
    
    # 只取前N个
    if len(sorted_classes) > top_n:
        sorted_classes = sorted_classes[:top_n]
        logger.warning(f"只显示前 {top_n} 个类别")
    
    # 准备数据
    class_ids, counts = zip(*sorted_classes)
    class_labels = [class_id_to_name.get(cid, f'Class {cid}') for cid in class_ids]
    
    # 创建图表
    plt.figure(figsize=(12, max(6, len(class_labels) * 0.3)))
    
    # 绘制水平条形图
    bars = plt.barh(class_labels, counts)
    
    # 添加数值标签
    for bar in bars:
        width = bar.get_width()
        plt.text(width + max(counts) * 0.01, bar.get_y() + bar.get_height()/2, 
                 f'{int(width)}', va='center', fontweight='bold')
    
    # 设置图表
    plt.xlabel('标注数量', fontsize=12)
    plt.ylabel('类别', fontsize=12)
    plt.title('类别分布', fontsize=16)
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"类别分布图已保存: {output_path}")


def plot_image_dimensions(
    widths: List[int],
    heights: List[int],
    output_path: str,
    bins: int = 50
) -> None:
    """
    绘制图像尺寸分布图
    
    Args:
        widths: 宽度列表
        heights: 高度列表
        output_path: 输出路径
        bins: 直方图的bins数量
    """
    plt.figure(figsize=(15, 5))
    
    # 宽度分布
    plt.subplot(1, 3, 1)
    plt.hist(widths, bins=bins, alpha=0.7, color='blue', edgecolor='black')
    plt.xlabel('宽度 (像素)')
    plt.ylabel('频率')
    plt.title('图像宽度分布')
    plt.grid(axis='y', alpha=0.3)
    
    # 高度分布
    plt.subplot(1, 3, 2)
    plt.hist(heights, bins=bins, alpha=0.7, color='green', edgecolor='black')
    plt.xlabel('高度 (像素)')
    plt.ylabel('频率')
    plt.title('图像高度分布')
    plt.grid(axis='y', alpha=0.3)
    
    # 宽高散点图
    plt.subplot(1, 3, 3)
    plt.scatter(widths, heights, alpha=0.5, s=10)
    plt.xlabel('宽度 (像素)')
    plt.ylabel('高度 (像素)')
    plt.title('图像尺寸分布')
    plt.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"图像尺寸分布图已保存: {output_path}")


def plot_annotations_per_image(
    annotations_per_image: List[int],
    output_path: str,
    bins: int = 50
) -> None:
    """
    绘制每张图像的标注数量分布
    
    Args:
        annotations_per_image: 每张图像的标注数量列表
        output_path: 输出路径
        bins: 直方图的bins数量
    """
    plt.figure(figsize=(10, 6))
    
    # 绘制直方图
    plt.hist(annotations_per_image, bins=min(bins, max(annotations_per_image) + 1), 
             alpha=0.7, color='orange', edgecolor='black')
    
    # 添加统计信息
    avg_anns = np.mean(annotations_per_image)
    median_anns = np.median(annotations_per_image)
    
    plt.axvline(avg_anns, color='red', linestyle='dashed', linewidth=2, 
                label=f'平均值: {avg_anns:.2f}')
    plt.axvline(median_anns, color='green', linestyle='dashed', linewidth=2, 
                label=f'中位数: {median_anns}')
    
    plt.xlabel('标注数量')
    plt.ylabel('图像数量')
    plt.title('每张图像的标注数量分布')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"标注数量分布图已保存: {output_path}")


def generate_report(
    image_stats: Dict[str, Any],
    class_stats: Dict[str, Any],
    class_id_to_name: Dict[int, str],
    abnormal_images: List[Dict[str, Any]],
    output_path: str
) -> None:
    """
    生成统计报告
    
    Args:
        image_stats: 图像统计信息
        class_stats: 类别统计信息
        class_id_to_name: 类别ID到名称的映射
        异常图像: 异常图像列表
        output_path: 输出路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("数据集统计报告\n")
        f.write("=" * 80 + "\n\n")
        
        # 图像统计
        f.write("1. 图像统计\n")
        f.write("-" * 40 + "\n")
        f.write(f"总图像数: {image_stats['total_images']}\n")
        f.write(f"图像宽度: 最小={image_stats['min_width']}, 最大={image_stats['max_width']}, "
                f"平均={image_stats['avg_width']:.1f}, 中位数={image_stats['median_width']}\n")
        f.write(f"图像高度: 最小={image_stats['min_height']}, 最大={image_stats['max_height']}, "
                f"平均={image_stats['avg_height']:.1f}, 中位数={image_stats['median_height']}\n")
        f.write(f"图像面积: 最小={image_stats['min_area']}, 最大={image_stats['max_area']}, "
                f"平均={image_stats['avg_area']:.1f}\n")
        f.write(f"长宽比例: 最小={image_stats['min_aspect_ratio']:.2f}, 最大={image_stats['max_aspect_ratio']:.2f}, "
                f"平均={image_stats['avg_aspect_ratio']:.2f}\n\n")
        
        # 标注统计
        f.write("2. 标注统计\n")
        f.write("-" * 40 + "\n")
        f.write(f"总标注数: {class_stats['total_annotations']}\n")
        f.write(f"类别数量: {class_stats['total_categories']}\n")
        f.write(f"无标注图像数: {class_stats['images_without_annotations']}\n")
        f.write(f"有标注图像数: {class_stats['images_with_annotations']}\n")
        f.write(f"每张图像平均标注数: {class_stats['avg_annotations_per_image']:.2f}\n")
        f.write(f"每张图像中位数标注数: {class_stats['median_annotations_per_image']}\n\n")
        
        # 类别分布
        f.write("3. 类别分布\n")
        f.write("-" * 40 + "\n")
        
        # 按数量排序
        sorted_classes = sorted(class_stats['class_distribution'].items(), key=lambda x: x[1], reverse=True)
        
        for class_id, count in sorted_classes[:50]:  # 只显示前50个类别
            class_name = class_id_to_name.get(class_id, f'Class {class_id}')
            image_count = class_stats['images_per_class'].get(class_id, 0)
            percentage = (count / class_stats['total_annotations'] * 100) if class_stats['total_annotations'] > 0 else 0
            f.write(f"{class_name} (ID: {class_id}): {count} 个标注, "
                    f"出现在 {image_count} 张图像中 ({percentage:.2f}%)\n")
        
        if len(sorted_classes) > 50:
            f.write(f"... 还有 {len(sorted_classes) - 50} 个类别未显示\n")
        f.write("\n")
        
        # 异常图像
        f.write("4. 异常图像检测\n")
        f.write("-" * 40 + "\n")
        
        if abnormal_images:
            f.write(f"发现 {len(abnormal_images)} 个异常图像:\n\n")
            
            # 按类型分组
            abnormal_by_type = defaultdict(list)
            for img in abnormal_images:
                abnormal_by_type[img['type']].append(img)
            
            for type_name, img_list in abnormal_by_type.items():
                f.write(f"类型 '{type_name}': {len(img_list)} 个图像\n")
                for img in img_list[:20]:  # 每个类型只显示前20个
                    f.write(f"  - {img['path']}: {img['reason']}\n")
                if len(img_list) > 20:
                    f.write(f"  ... 还有 {len(img_list) - 20} 个图像\n")
                f.write("\n")
        else:
            f.write("未发现异常图像\n")
    
    logger.info(f"统计报告已生成: {output_path}")


def analyze_dataset(
    image_dir: str,
    label_dir: str,
    output_dir: str,
    label_format: str = 'yolo',
    coco_json_path: Optional[str] = None,
    class_names_path: Optional[str] = None,
    recursive: bool = False,
    generate_plots: bool = True,
    generate_report_flag: bool = True
) -> Dict[str, Any]:
    """
    分析数据集的主函数
    
    Args:
        image_dir: 图像目录
        label_dir: 标签目录
        output_dir: 输出目录
        label_format: 标签格式 ('yolo', 'voc', 'coco')
        coco_json_path: COCO格式的JSON文件路径
        class_names_path: 类别名称文件路径
        recursive: 是否递归处理子目录
        generate_plots: 是否生成图表
        generate_report_flag: 是否生成报告
    
    Returns:
        分析结果统计信息
    """
    # 确保输入目录存在
    if not os.path.exists(image_dir):
        raise ValueError(f"图像目录不存在: {image_dir}")
    if not os.path.exists(label_dir) and label_format != 'coco':
        raise ValueError(f"标签目录不存在: {label_dir}")
    
    # 初始化分析器
    analyzer = DatasetStatisticsAnalyzer(output_dir)
    
    # 使用分析器收集文件并进行基本统计
    image_files = analyzer.collect_files(image_dir, recursive=recursive)
    analyzer.analyze_basic_stats(image_files)
    
    # 确保输出目录存在
    ensure_directory(output_dir)
    
    # 加载类别名称
    class_names = None
    if class_names_path and os.path.exists(class_names_path):
        try:
            with open(class_names_path, 'r', encoding='utf-8') as f:
                class_names = [line.strip() for line in f if line.strip()]
            logger.info(f"加载类别名称: {class_names_path}, 共 {len(class_names)} 个类别")
        except Exception as e:
            logger.error(f"加载类别名称文件失败: {str(e)}")
    
    # 加载图像路径
    image_paths = load_image_paths(image_dir, recursive=recursive)
    if not image_paths:
        logger.error(f"未找到图像文件: {image_dir}")
        return {}
    
    # 分析图像尺寸
    logger.info("开始分析图像尺寸...")
    image_stats, abnormal_images = analyze_image_dimensions(image_paths)
    
    # 分析类别分布
    logger.info("开始分析类别分布...")
    class_stats, class_id_to_name = analyze_class_distribution(
        image_paths, label_dir, label_format, coco_json_path, class_names
    )
    
    # 生成图表
    if generate_plots:
        # 类别分布图
        class_dist_path = os.path.join(output_dir, 'class_distribution.png')
        plot_class_distribution(class_stats['class_distribution'], class_id_to_name, class_dist_path)
        
        # 图像尺寸分布图
        dimensions_path = os.path.join(output_dir, 'image_dimensions.png')
        plot_image_dimensions(image_stats['widths'], image_stats['heights'], dimensions_path)
        
        # 标注数量分布图
        annotations_path = os.path.join(output_dir, 'annotations_per_image.png')
        plot_annotations_per_image(class_stats['annotations_per_image'], annotations_path)
    
    # 生成报告
    if generate_report_flag:
        report_path = os.path.join(output_dir, 'dataset_statistics_report.txt')
        generate_report(image_stats, class_stats, class_id_to_name, abnormal_images, report_path)
    
    # 保存统计数据为JSON
    stats_json = {
        'image_statistics': image_stats,
        'class_statistics': class_stats,
        'class_id_to_name': class_id_to_name,
        'anomalies': abnormal_images,
        'analysis_time': str(os.path.getmtime(__file__))
    }
    
    json_path = os.path.join(output_dir, 'dataset_statistics.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(stats_json, f, ensure_ascii=False, indent=2)
    
    logger.info(f"统计数据已保存: {json_path}")
    
    return {
        'image_dir': image_dir,
        'label_dir': label_dir,
        'output_dir': output_dir,
        'total_images': image_stats['total_images'],
        'total_categories': class_stats['total_categories'],
        'total_annotations': class_stats['total_annotations'],
        'anomalies_found': len(abnormal_images),
        'report_path': report_path if generate_report_flag else None,
        'json_stats_path': json_path
    }


def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='数据集统计分析工具')
    
    parser.add_argument('-i', '--image-dir', required=True, help='输入文件或目录路径')
    parser.add_argument('-l', '--label-dir', required=True, help='标签目录路径')
    parser.add_argument('-o', '--output-dir', required=True, help='输出目录')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归分析子目录')
    parser.add_argument('--no-plots', action='store_true', help='跳过图像分析')
    parser.add_argument('--no-report', action='store_true', help='跳过文本分析')
    parser.add_argument('--sample-ratio', type=float, default=1.0, help='采样比例，用于大数据集')
    parser.add_argument('--label-format', type=str, choices=['yolo', 'voc', 'coco'], default='yolo', help='标签格式')
    parser.add_argument('--coco-json', help='COCO格式的JSON标注文件路径')
    parser.add_argument('--class-names', help='类别名称文件路径 (每行一个类别)')
    parser.add_argument('--log-level', type=str, choices=['debug', 'info', 'warning', 'error'], default='info', help='日志级别')
    
    return parser.parse_args()

def main():
    """
    主函数
    """
    args = parse_arguments()
    
    # 设置日志级别
    level = getattr(logging, args.log_level.upper())
    logger.setLevel(level)
    
    try:
        # 执行分析
        results = analyze_dataset(
            args.image_dir,
            args.label_dir,
            args.output_dir,
            args.label_format,
            args.coco_json,
            args.class_names,
            args.recursive,
            not args.no_plots,
            not args.no_report
        )
        
        if results:
            # 输出简短统计信息
            print("\n=== 数据集统计分析完成 ===")
            print(f"总图像数: {results.get('total_images', 0)}")
            print(f"类别数量: {results.get('total_categories', 0)}")
            print(f"标注总数: {results.get('total_annotations', 0)}")
            print(f"发现异常图像: {results.get('anomalies_found', 0)}")
            print(f"输出目录: {results.get('output_dir', 'N/A')}")
            if results.get('report_path'):
                print(f"统计报告: {results['report_path']}")
            print(f"JSON统计数据: {results['json_stats_path']}")
            print("=======================")
            
    except KeyboardInterrupt:
        print("\n用户中断分析")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {str(e)}")
        logger.error(f"运行失败: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()