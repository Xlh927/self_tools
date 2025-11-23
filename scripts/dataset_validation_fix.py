#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集校验 & 自动修复模块（B2）

功能：
- 缺失标签文件检测
- BBox 越界检测
- Mask 破损检测
- 标签与图片不一致自动修复

支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
import glob
import json
import shutil
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
import re


def load_image(image_path: str) -> Optional[np.ndarray]:
    """
    加载图像
    
    Args:
        image_path: 图像路径
    
    Returns:
        图像数组或None
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"错误: 无法读取图像 {image_path}")
        return None
    return image

def detect_missing_labels(
    image_dir: str,
    label_dir: str,
    image_extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.bmp'),
    label_extensions: Tuple[str, ...] = ('.txt', '.json', '.xml')
) -> List[Dict[str, Any]]:
    """
    检测缺失的标签文件
    
    Args:
        image_dir: 图像目录
        label_dir: 标签目录
        image_extensions: 图像扩展名
        label_extensions: 标签扩展名
    
    Returns:
        缺失标签信息列表
    """
    # 获取所有图像文件
    image_files = {}
    for ext in image_extensions:
        for img_path in glob.glob(os.path.join(image_dir, f"*{ext}")):
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            image_files[base_name] = img_path
    
    # 获取所有标签文件
    label_files = {}
    for ext in label_extensions:
        for label_path in glob.glob(os.path.join(label_dir, f"*{ext}")):
            base_name = os.path.splitext(os.path.basename(label_path))[0]
            label_files[base_name] = label_path
    
    # 检测缺失标签
    missing_labels = []
    for base_name, img_path in image_files.items():
        if base_name not in label_files:
            missing_labels.append({
                "image_path": img_path,
                "base_name": base_name,
                "error_type": "missing_label"
            })
    
    # 检测多余标签
    extra_labels = []
    for base_name, label_path in label_files.items():
        if base_name not in image_files:
            extra_labels.append({
                "label_path": label_path,
                "base_name": base_name,
                "error_type": "extra_label"
            })
    
    return missing_labels + extra_labels

def validate_yolo_bbox(bbox: List[float], img_width: int, img_height: int) -> Dict[str, Any]:
    """
    验证YOLO格式的边界框
    
    Args:
        bbox: YOLO格式边界框 [x_center, y_center, width, height]（归一化）
        img_width: 图像宽度
        img_height: 图像高度
    
    Returns:
        验证结果
    """
    x_center, y_center, width, height = bbox
    issues = []
    fixed = False
    
    # 检查值范围
    for i, (val, name) in enumerate(zip(bbox, ["x_center", "y_center", "width", "height"])):
        if val < 0:
            issues.append(f"{name} < 0: {val}")
            bbox[i] = 0
            fixed = True
        elif val > 1:
            issues.append(f"{name} > 1: {val}")
            bbox[i] = 1
            fixed = True
    
    # 检查零宽高
    if width <= 0:
        issues.append(f"width <= 0: {width}")
        width = 0.01
        bbox[2] = width
        fixed = True
    if height <= 0:
        issues.append(f"height <= 0: {height}")
        height = 0.01
        bbox[3] = height
        fixed = True
    
    # 转换为像素坐标检查
    x_min_pixel = (x_center - width / 2) * img_width
    y_min_pixel = (y_center - height / 2) * img_height
    x_max_pixel = (x_center + width / 2) * img_width
    y_max_pixel = (y_center + height / 2) * img_height
    
    # 检查是否完全越界
    if x_max_pixel <= 0 or x_min_pixel >= img_width or y_max_pixel <= 0 or y_min_pixel >= img_height:
        issues.append("BBox completely out of image bounds")
        # 修正到图像中心一个小区域
        bbox[0] = 0.5
        bbox[1] = 0.5
        fixed = True
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "fixed": fixed,
        "fixed_bbox": bbox if fixed else None
    }

def validate_coco_bbox(bbox: List[float], img_width: int, img_height: int) -> Dict[str, Any]:
    """
    验证COCO格式的边界框
    
    Args:
        bbox: COCO格式边界框 [x, y, width, height]（像素坐标）
        img_width: 图像宽度
        img_height: 图像高度
    
    Returns:
        验证结果
    """
    x, y, width, height = bbox
    issues = []
    fixed = False
    
    # 检查负值
    if x < 0:
        issues.append(f"x < 0: {x}")
        x = 0
        fixed = True
    if y < 0:
        issues.append(f"y < 0: {y}")
        y = 0
        fixed = True
    if width <= 0:
        issues.append(f"width <= 0: {width}")
        width = 1
        fixed = True
    if height <= 0:
        issues.append(f"height <= 0: {height}")
        height = 1
        fixed = True
    
    # 检查越界
    x_min = x
    y_min = y
    x_max = x + width
    y_max = y + height
    
    if x_max > img_width:
        issues.append(f"x_max > img_width: {x_max} > {img_width}")
        width = img_width - x
        fixed = True
    if y_max > img_height:
        issues.append(f"y_max > img_height: {y_max} > {img_height}")
        height = img_height - y
        fixed = True
    
    # 检查是否完全越界
    if x_max <= 0 or x_min >= img_width or y_max <= 0 or y_min >= img_height:
        issues.append("BBox completely out of image bounds")
        # 修正到图像中心一个小区域
        x = max(0, img_width // 2 - 5)
        y = max(0, img_height // 2 - 5)
        width = 10
        height = 10
        fixed = True
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "fixed": fixed,
        "fixed_bbox": [x, y, width, height] if fixed else None
    }

def validate_pascal_voc_bbox(bbox: List[float], img_width: int, img_height: int) -> Dict[str, Any]:
    """
    验证Pascal VOC格式的边界框
    
    Args:
        bbox: Pascal VOC格式边界框 [xmin, ymin, xmax, ymax]（像素坐标）
        img_width: 图像宽度
        img_height: 图像高度
    
    Returns:
        验证结果
    """
    xmin, ymin, xmax, ymax = bbox
    issues = []
    fixed = False
    
    # 检查负值
    if xmin < 0:
        issues.append(f"xmin < 0: {xmin}")
        xmin = 0
        fixed = True
    if ymin < 0:
        issues.append(f"ymin < 0: {ymin}")
        ymin = 0
        fixed = True
    if xmax < 0:
        issues.append(f"xmax < 0: {xmax}")
        xmax = 1
        fixed = True
    if ymax < 0:
        issues.append(f"ymax < 0: {ymax}")
        ymax = 1
        fixed = True
    
    # 检查越界
    if xmax > img_width:
        issues.append(f"xmax > img_width: {xmax} > {img_width}")
        xmax = img_width
        fixed = True
    if ymax > img_height:
        issues.append(f"ymax > img_height: {ymax} > {img_height}")
        ymax = img_height
        fixed = True
    
    # 检查xmax > xmin和ymax > ymin
    if xmax <= xmin:
        issues.append(f"xmax <= xmin: {xmax} <= {xmin}")
        xmax = xmin + 1
        fixed = True
    if ymax <= ymin:
        issues.append(f"ymax <= ymin: {ymax} <= {ymin}")
        ymax = ymin + 1
        fixed = True
    
    # 检查是否完全越界
    if xmax <= 0 or xmin >= img_width or ymax <= 0 or ymin >= img_height:
        issues.append("BBox completely out of image bounds")
        # 修正到图像中心一个小区域
        xmin = max(0, img_width // 2 - 5)
        ymin = max(0, img_height // 2 - 5)
        xmax = xmin + 10
        ymax = ymin + 10
        fixed = True
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "fixed": fixed,
        "fixed_bbox": [xmin, ymin, xmax, ymax] if fixed else None
    }

def validate_mask(mask: np.ndarray) -> Dict[str, Any]:
    """
    验证分割掩码
    
    Args:
        mask: 分割掩码
    
    Returns:
        验证结果
    """
    issues = []
    fixed = False
    
    # 检查掩码是否为空
    if np.sum(mask) == 0:
        issues.append("Empty mask")
        fixed = False  # 空掩码无法自动修复
    
    # 检查掩码连通性
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) > 10:  # 如果轮廓太多，可能是掩码破损
        issues.append(f"Mask has too many contours: {len(contours)}")
        fixed = False  # 复杂掩码需要人工修复
    
    # 检查掩码面积
    mask_area = np.sum(mask)
    total_area = mask.shape[0] * mask.shape[1]
    
    if mask_area < 10:  # 面积太小
        issues.append(f"Mask area too small: {mask_area} pixels")
        fixed = False
    elif mask_area > total_area * 0.95:  # 面积太大
        issues.append(f"Mask area too large: {mask_area / total_area:.2%} of image")
        # 可以尝试收缩边界
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.erode(mask.astype(np.uint8), kernel, iterations=1)
        fixed = True
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "fixed": fixed,
        "fixed_mask": mask if fixed else None,
        "contour_count": len(contours),
        "mask_area": mask_area,
        "mask_percentage": mask_area / total_area if total_area > 0 else 0
    }

def read_yolo_label(label_path: str) -> List[List[float]]:
    """
    读取YOLO格式标签
    
    Args:
        label_path: 标签文件路径
    
    Returns:
        标签列表 [[class_id, x_center, y_center, width, height], ...]
    """
    labels = []
    try:
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = float(parts[0])
                    bbox = list(map(float, parts[1:5]))
                    labels.append([class_id] + bbox)
    except Exception as e:
        print(f"读取YOLO标签文件失败 {label_path}: {str(e)}")
    return labels

def write_yolo_label(label_path: str, labels: List[List[float]]) -> bool:
    """
    写入YOLO格式标签
    
    Args:
        label_path: 标签文件路径
        labels: 标签列表
    
    Returns:
        是否成功
    """
    try:
        with open(label_path, 'w') as f:
            for label in labels:
                f.write(' '.join(map(str, label)) + '\n')
        return True
    except Exception as e:
        print(f"写入YOLO标签文件失败 {label_path}: {str(e)}")
        return False

def read_pascal_voc_label(label_path: str) -> List[Dict[str, Any]]:
    """
    读取Pascal VOC格式标签
    
    Args:
        label_path: 标签文件路径
    
    Returns:
        标签列表 [{'name': class_name, 'bbox': [xmin, ymin, xmax, ymax]}, ...]
    """
    labels = []
    try:
        tree = ET.parse(label_path)
        root = tree.getroot()
        
        for obj in root.findall('object'):
            name = obj.find('name').text
            bndbox = obj.find('bndbox')
            xmin = float(bndbox.find('xmin').text)
            ymin = float(bndbox.find('ymin').text)
            xmax = float(bndbox.find('xmax').text)
            ymax = float(bndbox.find('ymax').text)
            
            labels.append({
                'name': name,
                'bbox': [xmin, ymin, xmax, ymax]
            })
    except Exception as e:
        print(f"读取Pascal VOC标签文件失败 {label_path}: {str(e)}")
    return labels

def write_pascal_voc_label(label_path: str, labels: List[Dict[str, Any]], img_width: int, img_height: int, img_depth: int = 3, filename: str = None) -> bool:
    """
    写入Pascal VOC格式标签
    
    Args:
        label_path: 标签文件路径
        labels: 标签列表
        img_width: 图像宽度
        img_height: 图像高度
        img_depth: 图像深度
        filename: 文件名
    
    Returns:
        是否成功
    """
    try:
        if not filename:
            filename = os.path.basename(label_path).replace('.xml', '.jpg')
        
        root = ET.Element('annotation')
        ET.SubElement(root, 'filename').text = filename
        
        size = ET.SubElement(root, 'size')
        ET.SubElement(size, 'width').text = str(img_width)
        ET.SubElement(size, 'height').text = str(img_height)
        ET.SubElement(size, 'depth').text = str(img_depth)
        
        for i, label in enumerate(labels):
            obj = ET.SubElement(root, 'object')
            ET.SubElement(obj, 'name').text = label['name']
            ET.SubElement(obj, 'pose').text = 'Unspecified'
            ET.SubElement(obj, 'truncated').text = '0'
            ET.SubElement(obj, 'difficult').text = '0'
            
            bndbox = ET.SubElement(obj, 'bndbox')
            xmin, ymin, xmax, ymax = label['bbox']
            ET.SubElement(bndbox, 'xmin').text = str(xmin)
            ET.SubElement(bndbox, 'ymin').text = str(ymin)
            ET.SubElement(bndbox, 'xmax').text = str(xmax)
            ET.SubElement(bndbox, 'ymax').text = str(ymax)
        
        tree = ET.ElementTree(root)
        tree.write(label_path)
        return True
    except Exception as e:
        print(f"写入Pascal VOC标签文件失败 {label_path}: {str(e)}")
        return False

def validate_yolo_file(label_path: str, image_path: str) -> Dict[str, Any]:
    """
    验证YOLO格式标签文件
    
    Args:
        label_path: 标签文件路径
        image_path: 对应图像路径
    
    Returns:
        验证结果
    """
    # 检查文件是否存在
    if not os.path.exists(label_path):
        return {
            "is_valid": False,
            "issues": ["Label file does not exist"],
            "fixed": False
        }
    
    # 读取图像
    image = load_image(image_path)
    if image is None:
        return {
            "is_valid": False,
            "issues": ["Image file does not exist or cannot be read"],
            "fixed": False
        }
    
    img_height, img_width = image.shape[:2]
    
    # 读取标签
    labels = read_yolo_label(label_path)
    
    issues = []
    fixed = False
    fixed_labels = []
    
    for i, label in enumerate(labels):
        if len(label) < 5:
            issues.append(f"Label {i} has insufficient data")
            continue
        
        class_id = label[0]
        bbox = label[1:5]
        
        # 验证边界框
        result = validate_yolo_bbox(bbox, img_width, img_height)
        
        if not result["is_valid"]:
            for issue in result["issues"]:
                issues.append(f"Label {i} (class {class_id}): {issue}")
        
        if result["fixed"]:
            fixed = True
            fixed_labels.append([class_id] + result["fixed_bbox"] + label[5:])  # 保留其他信息
        else:
            fixed_labels.append(label)
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "fixed": fixed,
        "fixed_labels": fixed_labels if fixed else None,
        "total_labels": len(labels),
        "label_path": label_path,
        "image_path": image_path
    }

def validate_voc_file(label_path: str, image_path: str) -> Dict[str, Any]:
    """
    验证Pascal VOC格式标签文件
    
    Args:
        label_path: 标签文件路径
        image_path: 对应图像路径
    
    Returns:
        验证结果
    """
    # 检查文件是否存在
    if not os.path.exists(label_path):
        return {
            "is_valid": False,
            "issues": ["Label file does not exist"],
            "fixed": False
        }
    
    # 读取图像
    image = load_image(image_path)
    if image is None:
        return {
            "is_valid": False,
            "issues": ["Image file does not exist or cannot be read"],
            "fixed": False
        }
    
    img_height, img_width = image.shape[:2]
    
    # 读取标签
    labels = read_pascal_voc_label(label_path)
    
    issues = []
    fixed = False
    fixed_labels = []
    
    for i, label in enumerate(labels):
        class_name = label['name']
        bbox = label['bbox']
        
        # 验证边界框
        result = validate_pascal_voc_bbox(bbox, img_width, img_height)
        
        if not result["is_valid"]:
            for issue in result["issues"]:
                issues.append(f"Object {i} ({class_name}): {issue}")
        
        if result["fixed"]:
            fixed = True
            fixed_labels.append({
                'name': class_name,
                'bbox': result["fixed_bbox"]
            })
        else:
            fixed_labels.append(label)
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "fixed": fixed,
        "fixed_labels": fixed_labels if fixed else None,
        "total_labels": len(labels),
        "label_path": label_path,
        "image_path": image_path
    }

def fix_label_file(result: Dict[str, Any], output_path: str = None) -> bool:
    """
    修复标签文件
    
    Args:
        result: 验证结果
        output_path: 输出路径，如果为None则覆盖原文件
    
    Returns:
        是否修复成功
    """
    if not result["fixed"]:
        return False
    
    label_path = result["label_path"]
    if output_path is None:
        output_path = label_path
    
    # 根据文件扩展名判断格式
    if label_path.endswith('.txt'):
        # YOLO格式
        return write_yolo_label(output_path, result["fixed_labels"])
    elif label_path.endswith('.xml'):
        # Pascal VOC格式
        # 读取图像信息
        image = load_image(result["image_path"])
        if image is None:
            return False
        img_height, img_width = image.shape[:2]
        img_depth = image.shape[2] if len(image.shape) > 2 else 1
        filename = os.path.basename(result["image_path"])
        return write_pascal_voc_label(output_path, result["fixed_labels"], img_width, img_height, img_depth, filename)
    
    return False

def batch_validate_and_fix(
    image_dir: str,
    label_dir: str,
    output_dir: str = None,
    fix: bool = False,
    recursive: bool = False
) -> Dict[str, Any]:
    """
    批量验证并修复标签文件
    
    Args:
        image_dir: 图像目录
        label_dir: 标签目录
        output_dir: 输出目录
        fix: 是否修复问题
        recursive: 是否递归处理
    
    Returns:
        验证统计信息
    """
    # 统计信息
    stats = {
        "total_images": 0,
        "missing_labels": 0,
        "extra_labels": 0,
        "valid_labels": 0,
        "invalid_labels": 0,
        "fixed_labels": 0,
        "bbox_issues": 0,
        "errors": []
    }
    
    # 获取所有图像文件
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    if recursive:
        glob_pattern = os.path.join(image_dir, "**", "*.???")
    else:
        glob_pattern = os.path.join(image_dir, "*.???")
    
    image_files = [
        f for f in glob.glob(glob_pattern, recursive=recursive)
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in image_extensions
    ]
    
    stats["total_images"] = len(image_files)
    
    # 获取所有标签文件
    label_extensions = {'.txt', '.xml', '.json'}
    if recursive:
        label_glob_pattern = os.path.join(label_dir, "**", "*.???")
    else:
        label_glob_pattern = os.path.join(label_dir, "*.???")
    
    label_files = {
        os.path.splitext(os.path.basename(f))[0]: f
        for f in glob.glob(label_glob_pattern, recursive=recursive)
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in label_extensions
    }
    
    # 验证每个图像的标签
    for img_path in image_files:
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        
        if base_name not in label_files:
            stats["missing_labels"] += 1
            stats["errors"].append({
                "type": "missing_label",
                "image_path": img_path,
                "message": f"Missing label file for {img_path}"
            })
            continue
        
        label_path = label_files[base_name]
        
        # 根据扩展名选择验证函数
        if label_path.endswith('.txt'):
            result = validate_yolo_file(label_path, img_path)
        elif label_path.endswith('.xml'):
            result = validate_voc_file(label_path, img_path)
        else:
            stats["errors"].append({
                "type": "unsupported_format",
                "label_path": label_path,
                "message": f"Unsupported label format for {label_path}"
            })
            continue
        
        # 处理验证结果
        if result["is_valid"]:
            stats["valid_labels"] += 1
        else:
            stats["invalid_labels"] += 1
            stats["bbox_issues"] += len(result["issues"])
            
            for issue in result["issues"]:
                stats["errors"].append({
                    "type": "bbox_issue",
                    "image_path": img_path,
                    "label_path": label_path,
                    "message": issue
                })
            
            # 如果需要修复
            if fix and result["fixed"]:
                if output_dir:
                    # 确保输出目录结构与输入一致
                    rel_path = os.path.relpath(os.path.dirname(label_path), label_dir)
                    output_label_dir = os.path.join(output_dir, rel_path)
                    os.makedirs(output_label_dir, exist_ok=True)
                    output_label_path = os.path.join(output_label_dir, os.path.basename(label_path))
                else:
                    output_label_path = label_path
                
                if fix_label_file(result, output_label_path):
                    stats["fixed_labels"] += 1
    
    # 检测多余标签
    image_basenames = {os.path.splitext(os.path.basename(f))[0] for f in image_files}
    for base_name, label_path in label_files.items():
        if base_name not in image_basenames:
            stats["extra_labels"] += 1
            stats["errors"].append({
                "type": "extra_label",
                "label_path": label_path,
                "message": f"Extra label file without corresponding image: {label_path}"
            })
    
    return stats

def generate_validation_report(stats: Dict[str, Any], output_path: str) -> bool:
    """
    生成验证报告
    
    Args:
        stats: 验证统计信息
        output_path: 输出路径
    
    Returns:
        是否生成成功
    """
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 生成报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("数据集验证报告\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"总图像数: {stats['total_images']}\n")
            f.write(f"有效标签数: {stats['valid_labels']}\n")
            f.write(f"无效标签数: {stats['invalid_labels']}\n")
            f.write(f"缺失标签数: {stats['missing_labels']}\n")
            f.write(f"多余标签数: {stats['extra_labels']}\n")
            f.write(f"修复的标签数: {stats['fixed_labels']}\n")
            f.write(f"边界框问题总数: {stats['bbox_issues']}\n\n")
            
            if stats['errors']:
                f.write("错误详情:\n")
                f.write("-" * 60 + "\n")
                
                for i, error in enumerate(stats['errors'], 1):
                    f.write(f"错误 {i}:\n")
                    f.write(f"  类型: {error['type']}\n")
                    if 'image_path' in error:
                        f.write(f"  图像路径: {error['image_path']}\n")
                    if 'label_path' in error:
                        f.write(f"  标签路径: {error['label_path']}\n")
                    f.write(f"  消息: {error['message']}\n")
                    f.write("-" * 60 + "\n")
            else:
                f.write("没有发现错误！数据集验证通过。\n")
        
        print(f"验证报告已生成: {output_path}")
        return True
    except Exception as e:
        print(f"生成验证报告失败: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="数据集校验 & 自动修复工具")
    
    # 基本参数
    parser.add_argument("-i", "--image-dir", required=True, help="图像目录路径")
    parser.add_argument("-l", "--label-dir", required=True, help="标签目录路径")
    parser.add_argument("-o", "--output-dir", help="修复后的标签输出目录")
    parser.add_argument("--report", help="验证报告输出路径")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    # 操作选项
    parser.add_argument("--fix", action="store_true", help="自动修复发现的问题")
    parser.add_argument("--check-missing", action="store_true", help="只检查缺失标签")
    
    args = parser.parse_args()
    
    # 执行批量验证和修复
    stats = batch_validate_and_fix(
        args.image_dir,
        args.label_dir,
        args.output_dir,
        args.fix,
        args.recursive
    )
    
    # 打印统计信息
    print("\n" + "=" * 60)
    print("数据集验证结果")
    print("=" * 60)
    print(f"总图像数: {stats['total_images']}")
    print(f"有效标签数: {stats['valid_labels']}")
    print(f"无效标签数: {stats['invalid_labels']}")
    print(f"缺失标签数: {stats['missing_labels']}")
    print(f"多余标签数: {stats['extra_labels']}")
    print(f"修复的标签数: {stats['fixed_labels']}")
    print(f"边界框问题总数: {stats['bbox_issues']}")
    
    # 生成报告
    if args.report:
        generate_validation_report(stats, args.report)
    
    # 如果有错误，打印一些示例
    if stats['errors'][:5]:  # 只显示前5个错误
        print("\n示例错误:")
        for error in stats['errors'][:5]:
            print(f"- {error['message']}")
        if len(stats['errors']) > 5:
            print(f"... 还有 {len(stats['errors']) - 5} 个错误未显示")


if __name__ == "__main__":
    main()