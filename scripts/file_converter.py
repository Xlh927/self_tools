#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件格式转换工具模块（C2）

功能：
- 图像格式转换（JPG/PNG/BMP/WEBP/TIFF等）
- 标注文件格式转换（YOLO/VOC/COCO等）
- 批量文件转换
- 格式转换参数配置
- 支持转换进度显示
- 转换报告生成
- 支持保留原始文件结构
- 支持递归处理子目录
- 支持文件压缩选项

本模块用于高效地在不同文件格式之间进行转换，特别适用于计算机视觉数据集处理和管理。
"""

import os
import sys
import argparse
import json
import xml.etree.ElementTree as ET
import shutil
import logging
from typing import List, Dict, Any, Tuple, Optional, Union, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import numpy as np
from PIL import Image, UnidentifiedImageError
import cv2
import pandas as pd

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FileConverter:
    """
    文件格式转换工具类
    """
    
    def __init__(self, output_dir=None, overwrite=False, keep_structure=True):
        """
        初始化转换器
        
        Args:
            output_dir: 输出目录
            overwrite: 是否覆盖已存在的文件
            keep_structure: 是否保持原始目录结构
        """
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.keep_structure = keep_structure
        
        # 支持的图像格式
        self.supported_image_formats = {
            'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp', 'gif', 
            'jp2', 'heif', 'avif', 'ppm', 'pgm', 'pbm'
        }
        
        # 支持的标注格式
        self.supported_annotation_formats = {
            'yolo', 'voc', 'coco', 'csv', 'json'
        }
        
        # 支持的视频格式
        self.supported_video_formats = {
            'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'
        }
        
        # 图像格式转换参数映射
        self.image_format_mapping = {
            'jpg': 'JPEG',
            'jpeg': 'JPEG',
            'png': 'PNG',
            'bmp': 'BMP',
            'tiff': 'TIFF',
            'tif': 'TIFF',
            'webp': 'WEBP',
            'gif': 'GIF',
            'jp2': 'JPEG2000',
            'heic': 'HEIF',
            'avif': 'AVIF',
            'ppm': 'PPM',
            'pgm': 'PGM',
            'pbm': 'PBM'
        }
    
    def convert_image_format(self, input_path, output_ext, quality=95, optimize=False, **kwargs):
        """
        转换图像格式
        
        Args:
            input_path: 输入图像路径
            output_ext: 输出格式扩展名（不包含点）
            quality: 图像质量（0-100）
            optimize: 是否优化图像
            **kwargs: 其他转换参数
        
        Returns:
            转换后的文件路径，如果失败则返回None
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"输入文件不存在: {input_path}")
            return None
        
        # 检查输出格式是否支持
        output_ext = output_ext.lower()
        if output_ext not in self.supported_image_formats:
            logger.error(f"不支持的输出格式: {output_ext}")
            return None
        
        # 确定输出文件路径
        output_path = self._get_output_path(input_path, output_ext)
        if not output_path:
            return None
        
        # 如果输出文件已存在且不允许覆盖，则跳过
        if os.path.exists(output_path) and not self.overwrite:
            logger.info(f"文件已存在且不覆盖: {output_path}")
            return output_path
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # 使用PIL打开图像
            with Image.open(input_path) as img:
                # 处理透明度（对于不支持透明度的格式）
                if output_ext.lower() in ['jpg', 'jpeg'] and img.mode == 'RGBA':
                    # 创建白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    # 粘贴图像，使用Alpha通道作为掩码
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode == 'P':
                    # 转换调色板图像为RGB
                    img = img.convert('RGB')
                
                # 准备保存参数
                save_params = {}
                if output_ext.lower() in ['jpg', 'jpeg']:
                    save_params['quality'] = quality
                    save_params['optimize'] = optimize
                    save_params['progressive'] = kwargs.get('progressive', False)
                elif output_ext.lower() == 'png':
                    save_params['quality'] = min(quality, 95)
                    save_params['optimize'] = optimize
                    save_params['compress_level'] = kwargs.get('compress_level', 6)
                elif output_ext.lower() == 'webp':
                    save_params['quality'] = quality
                    save_params['method'] = kwargs.get('method', 4)
                    save_params['lossless'] = kwargs.get('lossless', False)
                
                # 保存图像
                img.save(output_path, self.image_format_mapping[output_ext.lower()], **save_params)
                logger.debug(f"图像转换成功: {input_path} -> {output_path}")
                return output_path
        except UnidentifiedImageError:
            logger.error(f"无法识别的图像文件: {input_path}")
        except Exception as e:
            logger.error(f"图像转换失败 {input_path}: {str(e)}")
        
        return None
    
    def convert_yolo_to_voc(self, input_path, output_path, image_path, class_names):
        """
        将YOLO格式转换为Pascal VOC格式
        
        Args:
            input_path: YOLO标注文件路径
            output_path: VOC标注文件输出路径
            image_path: 对应的图像文件路径
            class_names: 类别名称列表
        
        Returns:
            是否转换成功
        """
        try:
            # 读取图像尺寸
            if not os.path.exists(image_path):
                logger.error(f"图像文件不存在: {image_path}")
                return False
            
            with Image.open(image_path) as img:
                img_width, img_height = img.size
            
            # 创建根元素
            root = ET.Element('annotation')
            
            # 添加文件夹和文件名
            folder = ET.SubElement(root, 'folder')
            folder.text = os.path.basename(os.path.dirname(image_path))
            
            filename = ET.SubElement(root, 'filename')
            filename.text = os.path.basename(image_path)
            
            # 添加路径
            path = ET.SubElement(root, 'path')
            path.text = os.path.abspath(image_path)
            
            # 添加源信息
            source = ET.SubElement(root, 'source')
            database = ET.SubElement(source, 'database')
            database.text = 'Unknown'
            
            # 添加尺寸信息
            size = ET.SubElement(root, 'size')
            width = ET.SubElement(size, 'width')
            width.text = str(img_width)
            height = ET.SubElement(size, 'height')
            height.text = str(img_height)
            depth = ET.SubElement(size, 'depth')
            depth.text = '3'
            
            # 添加分割信息
            segmented = ET.SubElement(root, 'segmented')
            segmented.text = '0'
            
            # 读取YOLO标注
            with open(input_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    
                    class_id = int(float(parts[0]))
                    center_x = float(parts[1])
                    center_y = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    
                    # 转换为VOC格式
                    xmin = int((center_x - width / 2) * img_width)
                    ymin = int((center_y - height / 2) * img_height)
                    xmax = int((center_x + width / 2) * img_width)
                    ymax = int((center_y + height / 2) * img_height)
                    
                    # 确保坐标有效
                    xmin = max(0, xmin)
                    ymin = max(0, ymin)
                    xmax = min(img_width - 1, xmax)
                    ymax = min(img_height - 1, ymax)
                    
                    # 获取类别名称
                    class_name = f'class_{class_id}'
                    if 0 <= class_id < len(class_names):
                        class_name = class_names[class_id]
                    
                    # 添加对象
                    obj = ET.SubElement(root, 'object')
                    name = ET.SubElement(obj, 'name')
                    name.text = class_name
                    pose = ET.SubElement(obj, 'pose')
                    pose.text = 'Unspecified'
                    truncated = ET.SubElement(obj, 'truncated')
                    truncated.text = '0'
                    difficult = ET.SubElement(obj, 'difficult')
                    difficult.text = '0'
                    
                    bndbox = ET.SubElement(obj, 'bndbox')
                    xmin_elem = ET.SubElement(bndbox, 'xmin')
                    xmin_elem.text = str(xmin)
                    ymin_elem = ET.SubElement(bndbox, 'ymin')
                    ymin_elem.text = str(ymin)
                    xmax_elem = ET.SubElement(bndbox, 'xmax')
                    xmax_elem.text = str(xmax)
                    ymax_elem = ET.SubElement(bndbox, 'ymax')
                    ymax_elem.text = str(ymax)
            
            # 写入XML文件
            tree = ET.ElementTree(root)
            # 创建XML声明
            xml_str = ET.tostring(root, encoding='utf-8')
            xml_str = b'<?xml version="1.0" encoding="utf-8"?>\n' + xml_str
            
            with open(output_path, 'wb') as f:
                f.write(xml_str)
            
            logger.debug(f"YOLO到VOC转换成功: {input_path} -> {output_path}")
            return True
        except Exception as e:
            logger.error(f"YOLO到VOC转换失败 {input_path}: {str(e)}")
            return False
    
    def convert_voc_to_yolo(self, input_path, output_path, image_path, class_names):
        """
        将Pascal VOC格式转换为YOLO格式
        
        Args:
            input_path: VOC标注文件路径
            output_path: YOLO标注文件输出路径
            image_path: 对应的图像文件路径
            class_names: 类别名称列表
        
        Returns:
            是否转换成功
        """
        try:
            # 读取图像尺寸
            if not os.path.exists(image_path):
                logger.error(f"图像文件不存在: {image_path}")
                return False
            
            with Image.open(image_path) as img:
                img_width, img_height = img.size
            
            # 解析XML
            tree = ET.parse(input_path)
            root = tree.getroot()
            
            yolo_lines = []
            
            # 查找所有对象
            for obj in root.findall('object'):
                # 获取类别名称
                name_elem = obj.find('name')
                if name_elem is None or not name_elem.text:
                    continue
                
                class_name = name_elem.text.strip()
                
                # 查找类别ID
                if class_name in class_names:
                    class_id = class_names.index(class_name)
                else:
                    logger.warning(f"类别 '{class_name}' 未在类别列表中找到，跳过")
                    continue
                
                # 获取边界框
                bndbox = obj.find('bndbox')
                if bndbox is None:
                    continue
                
                # 读取坐标
                xmin = float(bndbox.find('xmin').text)
                ymin = float(bndbox.find('ymin').text)
                xmax = float(bndbox.find('xmax').text)
                ymax = float(bndbox.find('ymax').text)
                
                # 转换为YOLO格式
                center_x = (xmin + xmax) / 2 / img_width
                center_y = (ymin + ymax) / 2 / img_height
                width = (xmax - xmin) / img_width
                height = (ymax - ymin) / img_height
                
                # 确保坐标在[0, 1]范围内
                center_x = max(0, min(1, center_x))
                center_y = max(0, min(1, center_y))
                width = max(0, min(1, width))
                height = max(0, min(1, height))
                
                # 添加YOLO行
                yolo_line = f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}"
                yolo_lines.append(yolo_line)
            
            # 写入YOLO文件
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(yolo_lines))
            
            logger.debug(f"VOC到YOLO转换成功: {input_path} -> {output_path}")
            return True
        except Exception as e:
            logger.error(f"VOC到YOLO转换失败 {input_path}: {str(e)}")
            return False
    
    def convert_yolo_to_coco(self, yolo_files, image_files, output_path, class_names):
        """
        将YOLO格式转换为COCO格式
        
        Args:
            yolo_files: YOLO标注文件列表
            image_files: 对应的图像文件列表
            output_path: COCO JSON输出路径
            class_names: 类别名称列表
        
        Returns:
            是否转换成功
        """
        try:
            # 创建COCO数据结构
            coco_data = {
                "info": {
                    "description": "Converted from YOLO format",
                    "version": "1.0",
                    "year": 2023,
                    "contributor": "FileConverter",
                    "date_created": pd.Timestamp.now().strftime("%Y-%m-%d")
                },
                "licenses": [
                    {
                        "id": 1,
                        "name": "Unknown License",
                        "url": "http://example.org/licenses/unknown"
                    }
                ],
                "images": [],
                "annotations": [],
                "categories": []
            }
            
            # 添加类别
            for i, class_name in enumerate(class_names):
                coco_data["categories"].append({
                    "id": i,
                    "name": class_name,
                    "supercategory": "object"
                })
            
            # 创建图像ID到文件路径的映射
            image_map = {}
            for img_path in image_files:
                img_name = os.path.splitext(os.path.basename(img_path))[0]
                image_map[img_name] = img_path
            
            annotation_id = 1
            
            # 处理每个YOLO文件
            for yolo_file in yolo_files:
                # 获取对应的图像
                yolo_name = os.path.splitext(os.path.basename(yolo_file))[0]
                if yolo_name not in image_map:
                    logger.warning(f"未找到对应的图像文件: {yolo_name}")
                    continue
                
                img_path = image_map[yolo_name]
                
                # 读取图像尺寸
                try:
                    with Image.open(img_path) as img:
                        img_width, img_height = img.size
                except Exception as e:
                    logger.error(f"读取图像尺寸失败 {img_path}: {str(e)}")
                    continue
                
                # 添加图像信息
                image_id = len(coco_data["images"]) + 1
                coco_data["images"].append({
                    "id": image_id,
                    "file_name": os.path.basename(img_path),
                    "width": img_width,
                    "height": img_height,
                    "date_captured": "",
                    "license": 1,
                    "coco_url": "",
                    "flickr_url": ""
                })
                
                # 读取YOLO标注
                try:
                    with open(yolo_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) < 5:
                                continue
                            
                            class_id = int(float(parts[0]))
                            center_x = float(parts[1])
                            center_y = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                            
                            # 转换为COCO格式
                            xmin = (center_x - width / 2) * img_width
                            ymin = (center_y - height / 2) * img_height
                            box_width = width * img_width
                            box_height = height * img_height
                            
                            # 计算面积
                            area = box_width * box_height
                            
                            # 添加标注
                            coco_data["annotations"].append({
                                "id": annotation_id,
                                "image_id": image_id,
                                "category_id": class_id,
                                "bbox": [xmin, ymin, box_width, box_height],
                                "area": area,
                                "segmentation": [],  # YOLO不包含分割信息
                                "iscrowd": 0,
                                "attributes": {}
                            })
                            
                            annotation_id += 1
                except Exception as e:
                    logger.error(f"读取YOLO文件失败 {yolo_file}: {str(e)}")
            
            # 保存COCO JSON
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(coco_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"YOLO到COCO转换成功: 生成 {output_path}")
            logger.info(f"转换了 {len(coco_data['images'])} 张图像和 {len(coco_data['annotations'])} 个标注")
            return True
        except Exception as e:
            logger.error(f"YOLO到COCO转换失败: {str(e)}")
            return False
    
    def batch_convert_images(self, input_paths, output_ext, quality=95, optimize=False, 
                           max_workers=4, **kwargs):
        """
        批量转换图像格式
        
        Args:
            input_paths: 输入图像路径列表
            output_ext: 输出格式扩展名
            quality: 图像质量
            optimize: 是否优化图像
            max_workers: 最大工作线程数
            **kwargs: 其他转换参数
        
        Returns:
            (成功转换的文件数, 失败的文件数)
        """
        success_count = 0
        fail_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有转换任务
            future_to_path = {}
            for input_path in input_paths:
                future = executor.submit(
                    self.convert_image_format,
                    input_path=input_path,
                    output_ext=output_ext,
                    quality=quality,
                    optimize=optimize,
                    **kwargs
                )
                future_to_path[future] = input_path
            
            # 处理完成的任务
            with tqdm(total=len(input_paths), desc="转换图像") as pbar:
                for future in as_completed(future_to_path):
                    input_path = future_to_path[future]
                    try:
                        result = future.result()
                        if result:
                            success_count += 1
                        else:
                            fail_count += 1
                    except Exception as e:
                        logger.error(f"处理失败 {input_path}: {str(e)}")
                        fail_count += 1
                    finally:
                        pbar.update(1)
        
        logger.info(f"图像批量转换完成: {success_count} 成功, {fail_count} 失败")
        return success_count, fail_count
    
    def batch_convert_annotations(self, input_paths, output_format, image_dir, class_names, 
                                output_dir=None):
        """
        批量转换标注格式
        
        Args:
            input_paths: 输入标注文件路径列表
            output_format: 输出格式 ('yolo', 'voc', 'coco')
            image_dir: 图像目录
            class_names: 类别名称列表
            output_dir: 输出目录
        
        Returns:
            (成功转换的文件数, 失败的文件数)
        """
        success_count = 0
        fail_count = 0
        
        # 对于COCO格式，一次性转换所有文件
        if output_format == 'coco':
            # 收集对应的图像文件
            image_files = []
            for ann_path in input_paths:
                base_name = os.path.splitext(os.path.basename(ann_path))[0]
                # 尝试查找对应的图像文件
                found = False
                for ext in self.supported_image_formats:
                    img_path = os.path.join(image_dir, f"{base_name}.{ext}")
                    if os.path.exists(img_path):
                        image_files.append(img_path)
                        found = True
                        break
                if not found:
                    logger.warning(f"未找到对应的图像文件: {base_name}")
            
            # 执行COCO转换
            output_path = output_dir or self.output_dir
            if not output_path:
                output_path = os.getcwd()
            
            coco_output = os.path.join(output_path, "coco_annotations.json")
            success = self.convert_yolo_to_coco(input_paths, image_files, coco_output, class_names)
            if success:
                success_count = len(input_paths)
            else:
                fail_count = len(input_paths)
        else:
            # 逐个转换文件
            for ann_path in tqdm(input_paths, desc="转换标注"):
                base_name = os.path.splitext(os.path.basename(ann_path))[0]
                
                # 查找对应的图像文件
                image_path = None
                for ext in self.supported_image_formats:
                    img_path = os.path.join(image_dir, f"{base_name}.{ext}")
                    if os.path.exists(img_path):
                        image_path = img_path
                        break
                
                if not image_path:
                    logger.warning(f"未找到对应的图像文件: {base_name}")
                    fail_count += 1
                    continue
                
                # 确定输出路径
                if output_format == 'voc':
                    output_path = self._get_output_path(ann_path, 'xml', output_dir)
                    success = self.convert_yolo_to_voc(ann_path, output_path, image_path, class_names)
                elif output_format == 'yolo':
                    output_path = self._get_output_path(ann_path, 'txt', output_dir)
                    success = self.convert_voc_to_yolo(ann_path, output_path, image_path, class_names)
                else:
                    logger.error(f"不支持的输出格式: {output_format}")
                    fail_count += 1
                    continue
                
                if success:
                    success_count += 1
                else:
                    fail_count += 1
        
        logger.info(f"标注批量转换完成: {success_count} 成功, {fail_count} 失败")
        return success_count, fail_count
    
    def _get_output_path(self, input_path, output_ext, base_output_dir=None):
        """
        获取输出文件路径
        
        Args:
            input_path: 输入文件路径
            output_ext: 输出扩展名（不包含点）
            base_output_dir: 基础输出目录
        
        Returns:
            输出文件路径
        """
        if not base_output_dir:
            base_output_dir = self.output_dir
        
        if not base_output_dir:
            # 如果没有指定输出目录，使用输入目录
            output_dir = os.path.dirname(input_path)
        else:
            if self.keep_structure:
                # 保持目录结构
                relative_path = os.path.basename(os.path.dirname(input_path))
                output_dir = os.path.join(base_output_dir, relative_path)
            else:
                # 不保持目录结构
                output_dir = base_output_dir
        
        # 生成文件名
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.{output_ext}")
        
        return output_path
    
    def find_files_by_extension(self, directory, extensions, recursive=True):
        """
        根据扩展名查找文件
        
        Args:
            directory: 目录路径
            extensions: 扩展名列表（不包含点）
            recursive: 是否递归搜索
        
        Returns:
            文件路径列表
        """
        if not os.path.exists(directory):
            logger.error(f"目录不存在: {directory}")
            return []
        
        files = []
        extensions = set(ext.lower() for ext in extensions)
        
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower().lstrip('.')
                if ext in extensions:
                    files.append(os.path.join(root, filename))
            
            if not recursive:
                break
        
        logger.info(f"在 {directory} 中找到 {len(files)} 个文件")
        return files
    
    def generate_conversion_report(self, stats, output_path=None):
        """
        生成转换报告
        
        Args:
            stats: 转换统计信息
            output_path: 报告输出路径
        
        Returns:
            报告文件路径
        """
        if not output_path:
            output_path = os.path.join(self.output_dir or os.getcwd(), "conversion_report.json")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 添加时间戳
        import datetime
        stats['timestamp'] = datetime.datetime.now().isoformat()
        
        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"转换报告已生成: {output_path}")
        return output_path


def load_class_names(class_names_path):
    """
    加载类别名称文件
    
    Args:
        class_names_path: 类别名称文件路径
    
    Returns:
        类别名称列表
    """
    if not os.path.exists(class_names_path):
        logger.error(f"类别名称文件不存在: {class_names_path}")
        return []
    
    try:
        with open(class_names_path, 'r', encoding='utf-8') as f:
            class_names = [line.strip() for line in f if line.strip()]
        logger.info(f"加载了 {len(class_names)} 个类别")
        return class_names
    except Exception as e:
        logger.error(f"加载类别名称文件失败: {str(e)}")
        return []


def convert_images(
    input_path,
    output_dir,
    output_format,
    quality=95,
    optimize=False,
    progressive=False,
    compress_level=6,
    method=4,
    lossless=False,
    max_workers=4,
    recursive=True,
    overwrite=False,
    keep_structure=True
):
    """
    图像格式转换主函数
    
    Args:
        input_path: 输入路径（文件或目录）
        output_dir: 输出目录
        output_format: 输出格式
        quality: 图像质量
        optimize: 是否优化
        progressive: 是否生成渐进式JPEG
        compress_level: PNG压缩级别
        method: WebP压缩方法
        lossless: WebP是否无损
        max_workers: 最大工作线程数
        recursive: 是否递归处理
        overwrite: 是否覆盖已存在的文件
        keep_structure: 是否保持目录结构
    
    Returns:
        转换统计信息
    """
    # 初始化转换器
    converter = FileConverter(output_dir=output_dir, overwrite=overwrite, keep_structure=keep_structure)
    
    # 收集输入文件
    input_files = []
    if os.path.isfile(input_path):
        input_files.append(input_path)
    elif os.path.isdir(input_path):
        input_files = converter.find_files_by_extension(
            input_path,
            converter.supported_image_formats,
            recursive=recursive
        )
    else:
        raise ValueError(f"输入路径不存在: {input_path}")
    
    if not input_files:
        logger.warning(f"未找到可转换的图像文件: {input_path}")
        return {}
    
    # 准备转换参数
    convert_params = {
        'quality': quality,
        'optimize': optimize,
        'progressive': progressive,
        'compress_level': compress_level,
        'method': method,
        'lossless': lossless
    }
    
    # 执行批量转换
    success_count, fail_count = converter.batch_convert_images(
        input_files,
        output_format,
        max_workers=max_workers,
        **convert_params
    )
    
    # 生成统计信息
    stats = {
        'input_path': input_path,
        'output_dir': output_dir,
        'output_format': output_format,
        'total_files': len(input_files),
        'success_count': success_count,
        'fail_count': fail_count,
        'success_rate': success_count / max(1, len(input_files)),
        'convert_params': convert_params
    }
    
    # 生成报告
    report_path = converter.generate_conversion_report(stats)
    stats['report_path'] = report_path
    
    return stats


def convert_annotations(
    input_path,
    output_dir,
    output_format,
    image_dir,
    class_names_path=None,
    class_names=None,
    recursive=True,
    overwrite=False,
    keep_structure=True
):
    """
    标注格式转换主函数
    
    Args:
        input_path: 输入路径（文件或目录）
        output_dir: 输出目录
        output_format: 输出格式
        image_dir: 图像目录
        class_names_path: 类别名称文件路径
        class_names: 类别名称列表
        recursive: 是否递归处理
        overwrite: 是否覆盖已存在的文件
        keep_structure: 是否保持目录结构
    
    Returns:
        转换统计信息
    """
    # 加载类别名称
    if class_names_path and not class_names:
        class_names = load_class_names(class_names_path)
    
    if not class_names:
        # 使用默认类别名称
        class_names = [f'class_{i}' for i in range(100)]
        logger.warning("未提供类别名称，使用默认类别")
    
    # 初始化转换器
    converter = FileConverter(output_dir=output_dir, overwrite=overwrite, keep_structure=keep_structure)
    
    # 确定输入文件的格式
    input_format = None
    if os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower().lstrip('.')
        if ext == 'txt':
            input_format = 'yolo'
        elif ext == 'xml':
            input_format = 'voc'
        elif ext == 'json':
            # 假设是COCO格式
            input_format = 'coco'
        else:
            raise ValueError(f"不支持的输入标注格式: {ext}")
        input_files = [input_path]
    elif os.path.isdir(input_path):
        # 检查目录中文件的格式
        yolo_count = 0
        voc_count = 0
        
        for ext in ['.txt', '.xml', '.json']:
            pattern = f"**/*{ext}" if recursive else f"*{ext}"
            files = list(converter.find_files_by_extension(input_path, [ext.lstrip('.')], recursive=recursive))
            if ext == '.txt':
                yolo_count = len(files)
            elif ext == '.xml':
                voc_count = len(files)
        
        # 确定主要格式
        if yolo_count > voc_count:
            input_format = 'yolo'
            input_files = converter.find_files_by_extension(input_path, ['txt'], recursive=recursive)
        else:
            input_format = 'voc'
            input_files = converter.find_files_by_extension(input_path, ['xml'], recursive=recursive)
    else:
        raise ValueError(f"输入路径不存在: {input_path}")
    
    if not input_files:
        logger.warning(f"未找到可转换的标注文件: {input_path}")
        return {}
    
    # 验证输出格式
    if output_format not in converter.supported_annotation_formats:
        raise ValueError(f"不支持的输出格式: {output_format}")
    
    # 执行批量转换
    success_count, fail_count = converter.batch_convert_annotations(
        input_files,
        output_format,
        image_dir,
        class_names,
        output_dir
    )
    
    # 生成统计信息
    stats = {
        'input_path': input_path,
        'output_dir': output_dir,
        'input_format': input_format,
        'output_format': output_format,
        'total_files': len(input_files),
        'success_count': success_count,
        'fail_count': fail_count,
        'success_rate': success_count / max(1, len(input_files)),
        'num_classes': len(class_names)
    }
    
    # 生成报告
    report_path = converter.generate_conversion_report(stats)
    stats['report_path'] = report_path
    
    return stats


def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='文件格式转换工具')
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 图像转换命令
    img_parser = subparsers.add_parser('image', help='图像格式转换')
    img_parser.add_argument('-i', '--input', required=True, help='输入文件或目录路径')
    img_parser.add_argument('-o', '--output', required=True, help='输出目录')
    img_parser.add_argument('-f', '--format', required=True, help='输出图像格式 (jpg, png, webp等)')
    img_parser.add_argument('-q', '--quality', type=int, default=95, help='图像质量 (0-100)')
    img_parser.add_argument('--optimize', action='store_true', help='优化图像')
    img_parser.add_argument('--progressive', action='store_true', help='生成渐进式JPEG')
    img_parser.add_argument('--compress-level', type=int, default=6, help='PNG压缩级别 (0-9)')
    img_parser.add_argument('--method', type=int, default=4, help='WebP压缩方法 (0-6)')
    img_parser.add_argument('--lossless', action='store_true', help='WebP无损压缩')
    img_parser.add_argument('-j', '--jobs', type=int, default=4, help='并行工作线程数')
    img_parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    img_parser.add_argument('--overwrite', action='store_true', help='覆盖已存在的文件')
    img_parser.add_argument('--no-structure', action='store_true', help='不保持目录结构')
    
    # 标注转换命令
    ann_parser = subparsers.add_parser('annotation', help='标注格式转换')
    ann_parser.add_argument('-i', '--input', required=True, help='输入标注文件或目录路径')
    ann_parser.add_argument('-o', '--output', required=True, help='输出目录')
    ann_parser.add_argument('-f', '--format', required=True, choices=['yolo', 'voc', 'coco'], 
                          help='输出标注格式')
    ann_parser.add_argument('-iimg', '--image-dir', required=True, help='图像目录路径')
    ann_parser.add_argument('-c', '--class-names', help='类别名称文件路径')
    ann_parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    ann_parser.add_argument('--overwrite', action='store_true', help='覆盖已存在的文件')
    ann_parser.add_argument('--no-structure', action='store_true', help='不保持目录结构')
    
    # 通用参数
    for p in [img_parser, ann_parser]:
        p.add_argument('--log-level', type=str, choices=['debug', 'info', 'warning', 'error'], 
                     default='info', help='日志级别')
    
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
        if args.command == 'image':
            # 执行图像转换
            results = convert_images(
                input_path=args.input,
                output_dir=args.output,
                output_format=args.format,
                quality=args.quality,
                optimize=args.optimize,
                progressive=args.progressive,
                compress_level=args.compress_level,
                method=args.method,
                lossless=args.lossless,
                max_workers=args.jobs,
                recursive=args.recursive,
                overwrite=args.overwrite,
                keep_structure=not args.no_structure
            )
            
            if results:
                print("\n=== 图像格式转换完成 ===")
                print(f"输入路径: {results.get('input_path', 'N/A')}")
                print(f"输出目录: {results.get('output_dir', 'N/A')}")
                print(f"输出格式: {results.get('output_format', 'N/A')}")
                print(f"总文件数: {results.get('total_files', 0)}")
                print(f"成功转换: {results.get('success_count', 0)}")
                print(f"失败转换: {results.get('fail_count', 0)}")
                print(f"成功率: {results.get('success_rate', 0):.2%}")
                print(f"转换报告: {results.get('report_path', 'N/A')}")
                print("==============================")
        
        elif args.command == 'annotation':
            # 执行标注转换
            results = convert_annotations(
                input_path=args.input,
                output_dir=args.output,
                output_format=args.format,
                image_dir=args.image_dir,
                class_names_path=args.class_names,
                recursive=args.recursive,
                overwrite=args.overwrite,
                keep_structure=not args.no_structure
            )
            
            if results:
                print("\n=== 标注格式转换完成 ===")
                print(f"输入路径: {results.get('input_path', 'N/A')}")
                print(f"输出目录: {results.get('output_dir', 'N/A')}")
                print(f"输入格式: {results.get('input_format', 'N/A')}")
                print(f"输出格式: {results.get('output_format', 'N/A')}")
                print(f"总文件数: {results.get('total_files', 0)}")
                print(f"成功转换: {results.get('success_count', 0)}")
                print(f"失败转换: {results.get('fail_count', 0)}")
                print(f"成功率: {results.get('success_rate', 0):.2%}")
                print(f"类别数量: {results.get('num_classes', 0)}")
                print(f"转换报告: {results.get('report_path', 'N/A')}")
                print("==============================")
        
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n用户中断转换")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {str(e)}")
        logger.error(f"运行失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()