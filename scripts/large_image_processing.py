#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超大图处理/滑窗工具模块（A7）

功能：
- 超大长图平滑浏览（DeepZoom）
- 滑窗切割（支持重叠和非重叠）
- 超大图可视化标注 overlay

支持单文件和批量文件夹处理
"""

import os
import sys
import argparse
import json
import logging
import math
import numpy as np
import cv2
from typing import List, Dict, Any, Tuple, Optional, Generator
import xml.etree.ElementTree as ET
from PIL import Image
import tqdm

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
        for root, _, files in os.walk(image_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_extensions:
                    image_paths.append(os.path.join(root, file))
    else:
        for file in os.listdir(image_dir):
            file_path = os.path.join(image_dir, file)
            if os.path.isfile(file_path):
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_extensions:
                    image_paths.append(file_path)
    
    logger.info(f"找到 {len(image_paths)} 个图像文件")
    return image_paths


def read_yolo_label(label_path: str) -> List[Dict[str, Any]]:
    """
    读取YOLO格式标签
    
    Args:
        label_path: 标签文件路径
    
    Returns:
        标注列表 [{'class_id': int, 'bbox': [x_center, y_center, width, height]}, ...]
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
                        annotations.append({
                            'class_id': class_id,
                            'bbox': bbox
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
        标注列表 [{'class_name': str, 'bbox': [xmin, ymin, xmax, ymax]}, ...]
    """
    annotations = []
    if not os.path.exists(label_path):
        return annotations
    
    try:
        tree = ET.parse(label_path)
        root = tree.getroot()
        
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
                
                annotations.append({
                    'class_name': class_name,
                    'bbox': [xmin, ymin, xmax, ymax]
                })
            except ValueError:
                continue
    except Exception as e:
        logger.error(f"读取Pascal VOC标签文件失败 {label_path}: {str(e)}")
    
    return annotations


def sliding_window_generator(
    image_shape: Tuple[int, int, int],
    window_size: Tuple[int, int],
    stride: Tuple[int, int],
    overlap_ratio: Optional[float] = None
) -> Generator[Tuple[int, int, int, int], None, None]:
    """
    生成滑窗坐标
    
    Args:
        image_shape: 图像形状 (height, width, channels)
        window_size: 窗口大小 (height, width)
        stride: 滑动步长 (height, width)
        overlap_ratio: 重叠比例（如果提供则覆盖stride）
    
    Yields:
        (y_start, y_end, x_start, x_end) 窗口坐标
    """
    height, width = image_shape[:2]
    win_h, win_w = window_size
    
    # 如果提供了重叠比例，计算步长
    if overlap_ratio is not None:
        stride = (
            int(win_h * (1 - overlap_ratio)),
            int(win_w * (1 - overlap_ratio))
        )
    
    stride_h, stride_w = stride
    
    # 计算窗口数量
    num_windows_h = math.ceil((height - win_h) / stride_h) + 1
    num_windows_w = math.ceil((width - win_w) / stride_w) + 1
    
    # 生成窗口
    for i in range(num_windows_h):
        for j in range(num_windows_w):
            y_start = i * stride_h
            y_end = min(y_start + win_h, height)
            x_start = j * stride_w
            x_end = min(x_start + win_w, width)
            
            # 如果最后一个窗口不够大，调整起始位置以确保窗口大小
            if y_end - y_start < win_h and i > 0:
                y_start = height - win_h
                y_end = height
            if x_end - x_start < win_w and j > 0:
                x_start = width - win_w
                x_end = width
            
            yield y_start, y_end, x_start, x_end


def slice_image(
    image_path: str,
    output_dir: str,
    window_size: Tuple[int, int],
    stride: Tuple[int, int] = None,
    overlap_ratio: Optional[float] = None,
    min_area_ratio: float = 0.1,
    save_metadata: bool = True
) -> Dict[str, Any]:
    """
    滑窗切割图像
    
    Args:
        image_path: 图像路径
        output_dir: 输出目录
        window_size: 窗口大小 (height, width)
        stride: 滑动步长 (height, width)
        overlap_ratio: 重叠比例（如果提供则覆盖stride）
        min_area_ratio: 最小有效区域比例
        save_metadata: 是否保存元数据
    
    Returns:
        切割结果统计信息
    """
    # 读取图像
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    
    # 获取图像信息
    image_shape = img.shape
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    
    # 确保输出目录存在
    ensure_directory(output_dir)
    
    # 如果没有提供步长，使用窗口大小（无重叠）
    if stride is None and overlap_ratio is None:
        stride = window_size
    
    # 生成滑窗
    windows = list(sliding_window_generator(image_shape, window_size, stride, overlap_ratio))
    
    # 保存切片
    slices_info = []
    for idx, (y_start, y_end, x_start, x_end) in enumerate(tqdm.tqdm(windows, desc="切割图像")):
        # 提取切片
        slice_img = img[y_start:y_end, x_start:x_end]
        
        # 检查切片是否有效（非空）
        if slice_img.size == 0:
            continue
        
        # 计算有效像素比例（非空白区域）
        # 转换为灰度并进行阈值处理
        gray = cv2.cvtColor(slice_img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
        valid_pixels = cv2.countNonZero(thresh)
        total_pixels = slice_img.shape[0] * slice_img.shape[1]
        valid_ratio = valid_pixels / total_pixels if total_pixels > 0 else 0
        
        # 如果有效区域比例过低，跳过
        if valid_ratio < min_area_ratio:
            continue
        
        # 保存切片
        slice_filename = f"{image_name}_slice_{idx}_{y_start}_{x_end}_{window_size[0]}_{window_size[1]}.jpg"
        slice_path = os.path.join(output_dir, slice_filename)
        
        # 使用PIL保存以支持大图像
        try:
            pil_img = Image.fromarray(cv2.cvtColor(slice_img, cv2.COLOR_BGR2RGB))
            pil_img.save(slice_path, quality=95, optimize=True)
            # cv2.imwrite(slice_path, slice_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        except Exception as e:
            logger.error(f"保存切片失败 {slice_path}: {str(e)}")
            continue
        
        # 记录切片信息
        slices_info.append({
            'filename': slice_filename,
            'path': slice_path,
            'coordinates': {
                'y_start': y_start,
                'y_end': y_end,
                'x_start': x_start,
                'x_end': x_end
            },
            'size': {
                'height': slice_img.shape[0],
                'width': slice_img.shape[1]
            },
            'valid_ratio': valid_ratio
        })
    
    # 保存元数据
    if save_metadata:
        metadata = {
            'original_image': {
                'path': image_path,
                'shape': image_shape,
                'name': image_name
            },
            'slice_parameters': {
                'window_size': window_size,
                'stride': stride,
                'overlap_ratio': overlap_ratio,
                'min_area_ratio': min_area_ratio
            },
            'slices': slices_info,
            'total_slices_generated': len(windows),
            'total_slices_saved': len(slices_info)
        }
        
        metadata_path = os.path.join(output_dir, f"{image_name}_slices_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"元数据已保存: {metadata_path}")
    
    return {
        'original_image': image_path,
        'total_slices_generated': len(windows),
        'total_slices_saved': len(slices_info),
        'output_dir': output_dir,
        'metadata_path': metadata_path if save_metadata else None
    }


def create_deepzoom_tiles(
    image_path: str,
    output_dir: str,
    tile_size: int = 254,
    overlap: int = 1,
    limit_bounds: bool = True
) -> Dict[str, Any]:
    """
    创建DeepZoom格式的图像金字塔
    
    Args:
        image_path: 图像路径
        output_dir: 输出目录
        tile_size: 瓦片大小
        overlap: 瓦片重叠像素数
        limit_bounds: 是否限制边界
    
    Returns:
        DeepZoom生成结果信息
    """
    try:
        # 尝试导入DeepZoomGenerator
        from PIL import Image
        try:
            from openslide import open_slide
            from openslide.deepzoom import DeepZoomGenerator
            has_openslide = True
        except ImportError:
            logger.warning("未找到openslide库，将使用PIL实现基础版本")
            has_openslide = False
        
        # 创建输出目录
        dzi_dir = os.path.join(output_dir, 'deepzoom')
        ensure_directory(dzi_dir)
        
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        
        if has_openslide:
            # 使用OpenSlide（支持更多格式和大图像）
            try:
                slide = open_slide(image_path)
                generator = DeepZoomGenerator(
                    slide,
                    tile_size=tile_size,
                    overlap=overlap,
                    limit_bounds=limit_bounds
                )
                
                # 获取金字塔级别
                levels = generator.level_count
                logger.info(f"创建DeepZoom金字塔，共 {levels} 个级别")
                
                # 保存每个级别的瓦片
                for level in tqdm.tqdm(range(levels), desc="生成DeepZoom金字塔"):
                    level_dir = os.path.join(dzi_dir, str(level))
                    ensure_directory(level_dir)
                    
                    # 获取该级别的行列数
                    cols, rows = generator.level_tiles[level]
                    
                    for row in range(rows):
                        for col in range(cols):
                            try:
                                # 获取瓦片
                                tile = generator.get_tile(level, (col, row))
                                # 保存瓦片
                                tile_filename = f"{col}_{row}.jpg"
                                tile_path = os.path.join(level_dir, tile_filename)
                                tile.save(tile_path, quality=90, optimize=True)
                            except Exception as e:
                                logger.error(f"生成瓦片失败 (level={level}, col={col}, row={row}): {str(e)}")
                
                # 创建DZI XML描述文件
                dzi_path = os.path.join(dzi_dir, f"{image_name}.dzi")
                with open(dzi_path, 'w', encoding='utf-8') as f:
                    f.write(f'''\<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" 
       Format="jpg" 
       Overlap="{overlap}" 
       TileSize="{tile_size}" 
       Width="{slide.dimensions[0]}" 
       Height="{slide.dimensions[1]}">
</Image>''')
                
                logger.info(f"DeepZoom DZI文件已创建: {dzi_path}")
                
                return {
                    'original_image': image_path,
                    'dzi_path': dzi_path,
                    'tile_directory': dzi_dir,
                    'levels': levels,
                    'tile_size': tile_size,
                    'overlap': overlap,
                    'image_dimensions': slide.dimensions
                }
                
            except Exception as e:
                logger.error(f"使用OpenSlide处理失败，切换到PIL实现: {str(e)}")
        
        # PIL实现的DeepZoom（基础版本）
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        # 计算金字塔级别
        max_dim = max(img_width, img_height)
        levels = math.floor(math.log2(max_dim / tile_size)) + 2
        if levels < 1:
            levels = 1
        
        logger.info(f"使用PIL实现创建DeepZoom金字塔，共 {levels} 个级别")
        
        # 创建每个级别的图像
        for level in tqdm.tqdm(range(levels), desc="生成DeepZoom金字塔(PIL)"):
            # 计算缩放比例
            scale = 1 / (2 ** (levels - 1 - level))
            level_width = int(img_width * scale)
            level_height = int(img_height * scale)
            
            # 调整图像大小
            resized_img = img.resize((level_width, level_height), Image.Resampling.LANCZOS)
            
            # 计算瓦片数量
            cols = math.ceil(level_width / (tile_size - overlap * 2))
            rows = math.ceil(level_height / (tile_size - overlap * 2))
            
            # 创建级别目录
            level_dir = os.path.join(dzi_dir, str(level))
            ensure_directory(level_dir)
            
            # 生成瓦片
            for row in range(rows):
                for col in range(cols):
                    try:
                        # 计算瓦片坐标
                        x = col * (tile_size - overlap * 2)
                        y = row * (tile_size - overlap * 2)
                        
                        # 创建瓦片大小的图像
                        tile = Image.new('RGB', (tile_size, tile_size), color='white')
                        
                        # 计算源区域
                        src_x = max(0, x - overlap)
                        src_y = max(0, y - overlap)
                        src_w = min(tile_size, level_width - src_x)
                        src_h = min(tile_size, level_height - src_y)
                        
                        # 计算目标区域
                        dst_x = overlap if x > 0 else 0
                        dst_y = overlap if y > 0 else 0
                        
                        # 裁剪并粘贴
                        if src_w > 0 and src_h > 0:
                            src_region = resized_img.crop((src_x, src_y, src_x + src_w, src_y + src_h))
                            tile.paste(src_region, (dst_x, dst_y))
                        
                        # 保存瓦片
                        tile_filename = f"{col}_{row}.jpg"
                        tile_path = os.path.join(level_dir, tile_filename)
                        tile.save(tile_path, quality=90, optimize=True)
                    except Exception as e:
                        logger.error(f"生成瓦片失败 (level={level}, col={col}, row={row}): {str(e)}")
        
        # 创建DZI XML描述文件
        dzi_path = os.path.join(dzi_dir, f"{image_name}.dzi")
        with open(dzi_path, 'w', encoding='utf-8') as f:
            f.write(f'''\<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" 
       Format="jpg" 
       Overlap="{overlap}" 
       TileSize="{tile_size}" 
       Width="{img_width}" 
       Height="{img_height}">
</Image>''')
        
        logger.info(f"DeepZoom DZI文件已创建: {dzi_path}")
        
        return {
            'original_image': image_path,
            'dzi_path': dzi_path,
            'tile_directory': dzi_dir,
            'levels': levels,
            'tile_size': tile_size,
            'overlap': overlap,
            'image_dimensions': (img_width, img_height)
        }
        
    except Exception as e:
        logger.error(f"创建DeepZoom失败: {str(e)}")
        raise


def create_annotation_overlay(
    image_path: str,
    output_path: str,
    annotations: List[Dict[str, Any]],
    class_names: Optional[List[str]] = None,
    colors: Optional[List[Tuple[int, int, int]]] = None,
    line_thickness: int = 2,
    font_scale: float = 0.5,
    opacity: float = 1.0
) -> None:
    """
    创建标注覆盖层
    
    Args:
        image_path: 图像路径
        output_path: 输出路径
        annotations: 标注列表
        class_names: 类别名称列表
        colors: 类别颜色列表
        line_thickness: 线条粗细
        font_scale: 字体大小
        opacity: 透明度
    """
    # 读取图像
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    
    # 创建副本用于绘制
    overlay = img.copy()
    
    # 如果没有提供颜色，生成随机颜色
    if colors is None:
        # 生成一些默认颜色
        colors = [
            (0, 0, 255),    # 红
            (0, 255, 0),    # 绿
            (255, 0, 0),    # 蓝
            (255, 255, 0),  # 黄
            (255, 0, 255),  # 洋红
            (0, 255, 255),  # 青
            (128, 0, 0),    # 深红
            (0, 128, 0),    # 深绿
            (0, 0, 128),    # 深蓝
        ]
    
    # 获取图像尺寸
    height, width = img.shape[:2]
    
    # 绘制每个标注
    for ann in annotations:
        class_id = ann.get('class_id')
        class_name = ann.get('class_name')
        
        # 确定类别名称
        if class_name is None and class_id is not None and class_names:
            class_name = class_names[class_id] if class_id < len(class_names) else f'Class {class_id}'
        elif class_name is None:
            class_name = f'Class {class_id}' if class_id is not None else 'Unknown'
        
        # 确定颜色
        color_idx = class_id % len(colors) if class_id is not None else 0
        color = colors[color_idx]
        
        # 获取bbox
        bbox = ann.get('bbox', [])
        if not bbox:
            continue
        
        # 处理不同格式的bbox
        if len(bbox) == 4:
            if max(bbox) <= 1.0:  # YOLO格式（归一化）
                # YOLO: [x_center, y_center, width, height]
                x_center = int(bbox[0] * width)
                y_center = int(bbox[1] * height)
                bbox_width = int(bbox[2] * width)
                bbox_height = int(bbox[3] * height)
                
                x1 = max(0, int(x_center - bbox_width / 2))
                y1 = max(0, int(y_center - bbox_height / 2))
                x2 = min(width, int(x_center + bbox_width / 2))
                y2 = min(height, int(y_center + bbox_height / 2))
            else:  # VOC格式（像素坐标）
                # VOC: [xmin, ymin, xmax, ymax]
                x1, y1, x2, y2 = map(int, bbox)
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(width, x2)
                y2 = min(height, y2)
            
            # 绘制矩形
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, line_thickness)
            
            # 绘制类别名称
            label_size = cv2.getTextSize(class_name, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
            label_y = y1 - 10 if y1 > 20 else y1 + label_size[1] + 10
            
            # 绘制背景
            cv2.rectangle(
                overlay, 
                (x1, label_y - label_size[1] - 5), 
                (x1 + label_size[0] + 5, label_y + 5), 
                color, 
                -1
            )
            
            # 绘制文字
            cv2.putText(
                overlay, 
                class_name, 
                (x1 + 2, label_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                font_scale, 
                (255, 255, 255), 
                2
            )
    
    # 应用透明度
    result = cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0)
    
    # 保存结果
    cv2.imwrite(output_path, result)
    logger.info(f"标注覆盖图像已保存: {output_path}")


def process_large_image(
    image_path: str,
    output_dir: str,
    operation: str,
    **kwargs
) -> Dict[str, Any]:
    """
    处理大图像的主函数
    
    Args:
        image_path: 图像路径
        output_dir: 输出目录
        operation: 操作类型 ('slice', 'deepzoom', 'annotate')
        **kwargs: 其他参数
    
    Returns:
        处理结果信息
    """
    ensure_directory(output_dir)
    
    if operation == 'slice':
        # 滑窗切割
        window_size = kwargs.get('window_size', (1024, 1024))
        stride = kwargs.get('stride', None)
        overlap_ratio = kwargs.get('overlap_ratio', None)
        min_area_ratio = kwargs.get('min_area_ratio', 0.1)
        save_metadata = kwargs.get('save_metadata', True)
        
        return slice_image(
            image_path,
            output_dir,
            window_size,
            stride,
            overlap_ratio,
            min_area_ratio,
            save_metadata
        )
    
    elif operation == 'deepzoom':
        # 创建DeepZoom
        tile_size = kwargs.get('tile_size', 254)
        overlap = kwargs.get('overlap', 1)
        limit_bounds = kwargs.get('limit_bounds', True)
        
        return create_deepzoom_tiles(
            image_path,
            output_dir,
            tile_size,
            overlap,
            limit_bounds
        )
    
    elif operation == 'annotate':
        # 创建标注覆盖
        label_path = kwargs.get('label_path', None)
        label_format = kwargs.get('label_format', 'yolo')
        class_names = kwargs.get('class_names', None)
        
        # 读取标注
        annotations = []
        if label_path and os.path.exists(label_path):
            if label_format == 'yolo':
                annotations = read_yolo_label(label_path)
            elif label_format == 'voc':
                annotations = read_pascal_voc_label(label_path)
            logger.info(f"读取了 {len(annotations)} 个标注")
        else:
            logger.warning(f"未找到标签文件: {label_path}")
        
        # 保存标注覆盖图像
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = os.path.join(output_dir, f"{image_name}_annotated.jpg")
        
        create_annotation_overlay(
            image_path,
            output_path,
            annotations,
            class_names,
            line_thickness=kwargs.get('line_thickness', 2),
            font_scale=kwargs.get('font_scale', 0.5),
            opacity=kwargs.get('opacity', 1.0)
        )
        
        return {
            'original_image': image_path,
            'annotated_image': output_path,
            'annotation_count': len(annotations),
            'label_format': label_format
        }
    
    else:
        raise ValueError(f"不支持的操作类型: {operation}")


def batch_process(
    image_dir: str,
    output_dir: str,
    operation: str,
    recursive: bool = False,
    label_dir: Optional[str] = None,
    label_format: str = 'yolo',
    class_names_path: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    批量处理图像
    
    Args:
        image_dir: 图像目录
        output_dir: 输出目录
        operation: 操作类型
        recursive: 是否递归处理
        label_dir: 标签目录（用于标注操作）
        label_format: 标签格式
        class_names_path: 类别名称文件路径
        **kwargs: 其他参数
    
    Returns:
        批量处理结果统计
    """
    # 加载类别名称
    class_names = None
    if class_names_path and os.path.exists(class_names_path):
        try:
            with open(class_names_path, 'r', encoding='utf-8') as f:
                class_names = [line.strip() for line in f if line.strip()]
            logger.info(f"加载了 {len(class_names)} 个类别名称")
        except Exception as e:
            logger.error(f"加载类别名称失败: {str(e)}")
    
    # 加载图像路径
    image_paths = load_image_paths(image_dir, recursive=recursive)
    if not image_paths:
        raise ValueError(f"未找到图像文件: {image_dir}")
    
    # 处理每个图像
    results = []
    failed_images = []
    
    for img_path in tqdm.tqdm(image_paths, desc="批量处理图像"):
        try:
            # 为每个图像创建输出子目录
            rel_path = os.path.relpath(img_path, image_dir)
            img_output_dir = os.path.join(output_dir, os.path.dirname(rel_path))
            ensure_directory(img_output_dir)
            
            # 准备参数
            process_kwargs = kwargs.copy()
            
            # 如果是标注操作，查找对应的标签文件
            if operation == 'annotate' and label_dir:
                img_name = os.path.splitext(os.path.basename(img_path))[0]
                label_ext = '.txt' if label_format == 'yolo' else '.xml'
                label_path = os.path.join(label_dir, img_name + label_ext)
                process_kwargs['label_path'] = label_path
                process_kwargs['label_format'] = label_format
                process_kwargs['class_names'] = class_names
            
            # 处理图像
            result = process_large_image(img_path, img_output_dir, operation, **process_kwargs)
            results.append(result)
            
        except Exception as e:
            logger.error(f"处理图像失败 {img_path}: {str(e)}")
            failed_images.append({
                'path': img_path,
                'error': str(e)
            })
    
    # 保存批量处理报告
    report = {
        'total_images': len(image_paths),
        'successful_images': len(results),
        'failed_images': failed_images,
        'operation': operation,
        'parameters': kwargs,
        'results': results
    }
    
    report_path = os.path.join(output_dir, 'batch_process_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"批量处理报告已保存: {report_path}")
    
    return {
        'total_images': len(image_paths),
        'successful_images': len(results),
        'failed_count': len(failed_images),
        'output_dir': output_dir,
        'report_path': report_path
    }


def main():
    parser = argparse.ArgumentParser(description="超大图处理/滑窗工具")
    
    # 基础参数
    parser.add_argument("-i", "--input", required=True, help="输入图像路径或目录")
    parser.add_argument("-o", "--output", required=True, help="输出目录路径")
    parser.add_argument("--operation", required=True, choices=['slice', 'deepzoom', 'annotate'], help="操作类型")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    # 滑窗参数
    parser.add_argument("--window-size", type=int, nargs=2, default=(1024, 1024), help="滑窗大小 (height width)")
    parser.add_argument("--stride", type=int, nargs=2, help="滑动步长 (height width)")
    parser.add_argument("--overlap-ratio", type=float, help="重叠比例 (0.0-1.0)")
    parser.add_argument("--min-area-ratio", type=float, default=0.1, help="最小有效区域比例")
    parser.add_argument("--no-metadata", action="store_true", help="不保存元数据")
    
    # DeepZoom参数
    parser.add_argument("--tile-size", type=int, default=254, help="瓦片大小")
    parser.add_argument("--tile-overlap", type=int, default=1, help="瓦片重叠像素")
    parser.add_argument("--no-limit-bounds", action="store_true", help="不限制边界")
    
    # 标注参数
    parser.add_argument("--label-dir", help="标签目录")
    parser.add_argument("--label-format", choices=['yolo', 'voc'], default='yolo', help="标签格式")
    parser.add_argument("--class-names", help="类别名称文件路径")
    parser.add_argument("--line-thickness", type=int, default=2, help="边框线条粗细")
    parser.add_argument("--font-scale", type=float, default=0.5, help="字体大小")
    parser.add_argument("--opacity", type=float, default=1.0, help="透明度 (0.0-1.0)")
    
    # 日志参数
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    try:
        # 准备参数
        process_kwargs = {}
        
        if args.operation == 'slice':
            process_kwargs['window_size'] = tuple(args.window_size)
            if args.stride:
                process_kwargs['stride'] = tuple(args.stride)
            if args.overlap_ratio is not None:
                process_kwargs['overlap_ratio'] = args.overlap_ratio
            process_kwargs['min_area_ratio'] = args.min_area_ratio
            process_kwargs['save_metadata'] = not args.no_metadata
        
        elif args.operation == 'deepzoom':
            process_kwargs['tile_size'] = args.tile_size
            process_kwargs['overlap'] = args.tile_overlap
            process_kwargs['limit_bounds'] = not args.no_limit_bounds
        
        elif args.operation == 'annotate':
            if not args.label_dir:
                parser.error("标注操作需要指定标签目录 (--label-dir)")
            process_kwargs['line_thickness'] = args.line_thickness
            process_kwargs['font_scale'] = args.font_scale
            process_kwargs['opacity'] = args.opacity
        
        # 执行处理
        if os.path.isfile(args.input):
            # 单文件处理
            logger.info(f"处理单个图像: {args.input}")
            result = process_large_image(args.input, args.output, args.operation, **process_kwargs)
            
            # 打印结果
            print("\n" + "=" * 60)
            print("图像处理完成")
            print("=" * 60)
            for key, value in result.items():
                print(f"{key}: {value}")
        
        else:
            # 批量处理
            logger.info(f"批量处理目录: {args.input}")
            result = batch_process(
                args.input,
                args.output,
                args.operation,
                args.recursive,
                args.label_dir,
                args.label_format,
                args.class_names,
                **process_kwargs
            )
            
            # 打印结果
            print("\n" + "=" * 60)
            print("批量处理完成")
            print("=" * 60)
            print(f"总图像数: {result['total_images']}")
            print(f"成功处理: {result['successful_images']}")
            print(f"处理失败: {result['failed_count']}")
            print(f"输出目录: {result['output_dir']}")
            print(f"处理报告: {result['report_path']}")
    
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()