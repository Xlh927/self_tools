#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集格式转换模块（B1）

功能：
- YOLO ↔ COCO 格式转换
- bbox ↔ polygon mask 转换
- RGB ↔ 单通道 转换

支持单文件和批量文件夹处理
"""

import os
import json
import cv2
import numpy as np
import argparse
from tqdm import tqdm
import re
import xml.etree.ElementTree as ET

def load_image(image_path):
    """加载图像"""
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise Exception(f"无法加载图像: {image_path}")
        return image
    except Exception as e:
        print(f"加载图像错误: {e}")
        return None

def save_image(image, output_path):
    """保存图像"""
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        cv2.imwrite(output_path, image)
        return True
    except Exception as e:
        print(f"保存图像错误: {e}")
        return False

def read_voc_annotation(xml_path):
    """读取VOC XML格式标注"""
    annotations = []
    if not os.path.exists(xml_path):
        return annotations
    
    try:
        # 解析XML文件
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 获取图像尺寸信息
        size_elem = root.find('size')
        width = int(size_elem.find('width').text)
        height = int(size_elem.find('height').text)
        
        # 获取所有object元素
        for obj in root.findall('object'):
            class_name = obj.find('name').text
            
            # 获取边界框坐标
            bndbox = obj.find('bndbox')
            xmin = int(bndbox.find('xmin').text)
            ymin = int(bndbox.find('ymin').text)
            xmax = int(bndbox.find('xmax').text)
            ymax = int(bndbox.find('ymax').text)
            
            # 计算面积
            area = (xmax - xmin) * (ymax - ymin)
            
            annotations.append({
                'class_name': class_name,
                'bbox': [xmin, ymin, xmax, ymax],
                'area': area
            })
        
        return annotations, width, height
    except Exception as e:
        print(f"解析XML文件错误: {e}")
        return [], 0, 0

def write_voc_annotation(annotations, output_path, image_width, image_height, image_file_name, class_names=None):
    """写入VOC XML格式标注"""
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # 创建XML根元素
        root = ET.Element('annotation')
        
        # 添加基本信息
        folder = ET.SubElement(root, 'folder')
        folder.text = os.path.basename(os.path.dirname(image_file_name)) if os.path.dirname(image_file_name) else 'VOC2007'
        
        filename = ET.SubElement(root, 'filename')
        filename.text = os.path.basename(image_file_name)
        
        path = ET.SubElement(root, 'path')
        path.text = image_file_name
        
        source = ET.SubElement(root, 'source')
        database = ET.SubElement(source, 'database')
        database.text = 'Unknown'
        
        # 添加图像尺寸信息
        size = ET.SubElement(root, 'size')
        width_elem = ET.SubElement(size, 'width')
        width_elem.text = str(image_width)
        height_elem = ET.SubElement(size, 'height')
        height_elem.text = str(image_height)
        depth = ET.SubElement(size, 'depth')
        depth.text = '3'  # 假设为RGB图像
        
        segmented = ET.SubElement(root, 'segmented')
        segmented.text = '0'
        
        # 添加每个标注对象
        for ann in annotations:
            obj = ET.SubElement(root, 'object')
            
            name = ET.SubElement(obj, 'name')
            if 'class_name' in ann:
                name.text = ann['class_name']
            elif class_names and 'class_id' in ann and ann['class_id'] < len(class_names):
                name.text = class_names[ann['class_id']]
            else:
                name.text = 'unknown'
            
            pose = ET.SubElement(obj, 'pose')
            pose.text = 'Unspecified'
            
            truncated = ET.SubElement(obj, 'truncated')
            truncated.text = '0'
            
            difficult = ET.SubElement(obj, 'difficult')
            difficult.text = '0'
            
            # 添加边界框信息
            bndbox = ET.SubElement(obj, 'bndbox')
            xmin = ET.SubElement(bndbox, 'xmin')
            xmin.text = str(int(ann['bbox'][0]))
            ymin = ET.SubElement(bndbox, 'ymin')
            ymin.text = str(int(ann['bbox'][1]))
            xmax = ET.SubElement(bndbox, 'xmax')
            xmax.text = str(int(ann['bbox'][2]))
            ymax = ET.SubElement(bndbox, 'ymax')
            ymax.text = str(int(ann['bbox'][3]))
        
        # 创建XML树并写入文件
        tree = ET.ElementTree(root)
        # 添加XML声明
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_declaration + '\n')
            # 美化输出
            tree.write(f, encoding='unicode', xml_declaration=False)
        
        return True
    except Exception as e:
        print(f"写入XML文件错误: {e}")
        return False

def read_yolo_annotation(annotation_path, image_width, image_height):
    """读取YOLO格式标注"""
    annotations = []
    if not os.path.exists(annotation_path):
        return annotations
    
    with open(annotation_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            
            class_id = int(parts[0])
            x_center = float(parts[1]) * image_width
            y_center = float(parts[2]) * image_height
            width = float(parts[3]) * image_width
            height = float(parts[4]) * image_height
            
            # 转换为左上角坐标
            x_min = max(0, x_center - width / 2)
            y_min = max(0, y_center - height / 2)
            x_max = min(image_width, x_center + width / 2)
            y_max = min(image_height, y_center + height / 2)
            
            annotations.append({
                'class_id': class_id,
                'bbox': [x_min, y_min, x_max, y_max],
                'area': width * height
            })
    
    return annotations

def write_yolo_annotation(annotations, output_path, image_width, image_height):
    """写入YOLO格式标注"""
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_path, 'w') as f:
        for ann in annotations:
            class_id = ann['class_id']
            x_min, y_min, x_max, y_max = ann['bbox']
            
            # 转换为YOLO格式（归一化中心坐标和宽高）
            x_center = (x_min + x_max) / 2 / image_width
            y_center = (y_min + y_max) / 2 / image_height
            width = (x_max - x_min) / image_width
            height = (y_max - y_min) / image_height
            
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

def yolo_to_coco(yolo_dir, image_dir, output_json, class_names=None):
    """YOLO格式转换为COCO格式"""
    if class_names is None:
        class_names = []
    
    # COCO数据结构
    coco_data = {
        'images': [],
        'annotations': [],
        'categories': []
    }
    
    # 添加类别信息
    for i, class_name in enumerate(class_names):
        coco_data['categories'].append({
            'id': i,
            'name': class_name,
            'supercategory': 'object'
        })
    
    # 获取所有图像文件
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    image_files = [f for f in os.listdir(image_dir) if any(f.lower().endswith(ext) for ext in image_extensions)]
    
    annotation_id = 1
    
    for img_id, img_file in enumerate(tqdm(image_files, desc="转换YOLO到COCO")):
        img_path = os.path.join(image_dir, img_file)
        image = load_image(img_path)
        if image is None:
            continue
        
        height, width = image.shape[:2]
        
        # 添加图像信息
        coco_data['images'].append({
            'id': img_id + 1,
            'file_name': img_file,
            'height': height,
            'width': width
        })
        
        # 对应的YOLO标注文件
        txt_file = os.path.splitext(img_file)[0] + '.txt'
        txt_path = os.path.join(yolo_dir, txt_file)
        
        if not os.path.exists(txt_path):
            continue
        
        # 读取YOLO标注
        yolo_annotations = read_yolo_annotation(txt_path, width, height)
        
        # 转换为COCO标注
        for ann in yolo_annotations:
            x_min, y_min, x_max, y_max = ann['bbox']
            class_id = ann['class_id']
            
            # 确保类别ID有效
            if class_id >= len(class_names) and class_names:
                continue
            
            coco_data['annotations'].append({
                'id': annotation_id,
                'image_id': img_id + 1,
                'category_id': class_id,
                'bbox': [x_min, y_min, x_max - x_min, y_max - y_min],
                'area': ann['area'],
                'segmentation': [],  # YOLO不包含分割信息
                'iscrowd': 0
            })
            annotation_id += 1
    
    # 保存COCO JSON
    output_dir = os.path.dirname(output_json)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_json, 'w') as f:
        json.dump(coco_data, f, indent=2)
    
    print(f"COCO格式文件已保存到: {output_json}")
    print(f"转换了 {len(coco_data['images'])} 张图像，{len(coco_data['annotations'])} 个标注")

def coco_to_yolo(coco_json, output_dir, image_dir=None):
    """COCO格式转换为YOLO格式"""
    # 读取COCO JSON
    with open(coco_json, 'r') as f:
        coco_data = json.load(f)
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 构建图像ID到图像信息的映射
    image_map = {img['id']: img for img in coco_data['images']}
    
    # 处理每个标注
    annotations_by_image = {}
    for ann in coco_data['annotations']:
        img_id = ann['image_id']
        if img_id not in annotations_by_image:
            annotations_by_image[img_id] = []
        
        # 转换COCO bbox到[min_x, min_y, max_x, max_y]
        x, y, w, h = ann['bbox']
        annotations_by_image[img_id].append({
            'class_id': ann['category_id'],
            'bbox': [x, y, x + w, y + h]
        })
    
    # 写入YOLO格式标注文件
    for img_id, annotations in tqdm(annotations_by_image.items(), desc="转换COCO到YOLO"):
        if img_id not in image_map:
            continue
        
        img_info = image_map[img_id]
        img_file = img_info['file_name']
        img_width = img_info['width']
        img_height = img_info['height']
        
        # 如果提供了图像目录，验证图像是否存在
        if image_dir:
            img_path = os.path.join(image_dir, img_file)
            if not os.path.exists(img_path):
                print(f"警告: 找不到图像文件 {img_path}")
                continue
        
        # 生成YOLO标注文件
        txt_file = os.path.splitext(img_file)[0] + '.txt'
        txt_path = os.path.join(output_dir, txt_file)
        
        write_yolo_annotation(annotations, txt_path, img_width, img_height)
    
    print(f"YOLO格式标注已保存到目录: {output_dir}")
    print(f"转换了 {len(annotations_by_image)} 个图像的标注")

def voc_to_yolo(voc_dir, output_dir, class_names=None, image_dir=None):
    """VOC格式转换为YOLO格式"""
    if class_names is None:
        class_names = []
    
    # 创建类别名称到ID的映射
    class_map = {name: idx for idx, name in enumerate(class_names)}
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 获取所有XML文件
    xml_files = [f for f in os.listdir(voc_dir) if f.lower().endswith('.xml')]
    
    processed_count = 0
    skipped_count = 0
    
    for xml_file in tqdm(xml_files, desc="转换VOC到YOLO"):
        xml_path = os.path.join(voc_dir, xml_file)
        
        # 读取VOC标注
        voc_annotations, width, height = read_voc_annotation(xml_path)
        
        if not voc_annotations or width <= 0 or height <= 0:
            skipped_count += 1
            continue
        
        # 转换为YOLO格式的标注
        yolo_annotations = []
        for ann in voc_annotations:
            class_name = ann['class_name']
            # 如果提供了类别名称列表，检查类别是否在列表中
            if class_names and class_name not in class_map:
                continue
            
            # 获取类别ID
            class_id = class_map.get(class_name, 0) if class_names else 0
            
            x_min, y_min, x_max, y_max = ann['bbox']
            
            yolo_annotations.append({
                'class_id': class_id,
                'bbox': [x_min, y_min, x_max, y_max]
            })
        
        # 生成YOLO标注文件
        base_name = os.path.splitext(xml_file)[0]
        txt_file = base_name + '.txt'
        txt_path = os.path.join(output_dir, txt_file)
        
        # 写入YOLO标注
        write_yolo_annotation(yolo_annotations, txt_path, width, height)
        
        processed_count += 1
    
    print(f"YOLO格式标注已保存到目录: {output_dir}")
    print(f"成功转换: {processed_count} 个文件")
    if skipped_count > 0:
        print(f"跳过: {skipped_count} 个文件 (无效标注或无匹配类别)")
    
    # 如果没有提供类别列表，提示用户
    if not class_names and processed_count > 0:
        print("警告: 未提供类别名称列表，所有标注默认使用类别ID 0")
        print("建议创建类别列表文件以正确映射类别名称到ID")

def read_yolo_annotation(txt_path, img_width, img_height):
    """读取YOLO格式标注文件"""
    annotations = []
    
    if not os.path.exists(txt_path):
        return annotations
    
    try:
        with open(txt_path, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # YOLO格式: class_id center_x center_y width height (归一化值)
            parts = line.split()
            if len(parts) >= 5:
                class_id = int(parts[0])
                
                # 读取归一化的坐标
                center_x = float(parts[1])
                center_y = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                
                # 转换为绝对坐标 [x_min, y_min, x_max, y_max]
                x_min = (center_x - width / 2) * img_width
                y_min = (center_y - height / 2) * img_height
                x_max = (center_x + width / 2) * img_width
                y_max = (center_y + height / 2) * img_height
                
                # 确保坐标在有效范围内
                x_min = max(0, x_min)
                y_min = max(0, y_min)
                x_max = min(img_width, x_max)
                y_max = min(img_height, y_max)
                
                annotations.append({
                    'class_id': class_id,
                    'bbox': [x_min, y_min, x_max, y_max]
                })
    except Exception as e:
        print(f"读取YOLO标注文件时出错 {txt_path}: {e}")
    
    return annotations

def yolo_to_voc(yolo_dir, output_dir, class_names=None, image_dir=None):
    """YOLO格式转换为VOC格式"""
    if class_names is None:
        class_names = []
    
    # 创建ID到类别名称的映射
    id_to_class = {idx: name for idx, name in enumerate(class_names)}
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 获取所有YOLO标注文件
    yolo_files = [f for f in os.listdir(yolo_dir) if f.lower().endswith('.txt')]
    
    processed_count = 0
    skipped_count = 0
    
    for yolo_file in tqdm(yolo_files, desc="转换YOLO到VOC"):
        yolo_path = os.path.join(yolo_dir, yolo_file)
        base_name = os.path.splitext(yolo_file)[0]
        
        # 如果提供了图像目录，尝试获取图像尺寸
        img_width, img_height = 0, 0
        if image_dir:
            # 尝试不同的图像扩展名
            for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                img_path = os.path.join(image_dir, base_name + ext)
                if os.path.exists(img_path):
                    try:
                        # 使用PIL获取图像尺寸
                        from PIL import Image
                        with Image.open(img_path) as img:
                            img_width, img_height = img.size
                        break
                    except Exception as e:
                        print(f"读取图像尺寸时出错 {img_path}: {e}")
        
        # 如果无法获取图像尺寸，使用默认值（可能导致坐标计算不准确）
        if img_width <= 0 or img_height <= 0:
            print(f"警告: 无法获取图像尺寸，使用默认值 (1024x768)")
            img_width, img_height = 1024, 768
        
        # 读取YOLO标注
        yolo_annotations = read_yolo_annotation(yolo_path, img_width, img_height)
        
        if not yolo_annotations:
            skipped_count += 1
            continue
        
        # 转换为VOC格式的标注
        voc_annotations = []
        for ann in yolo_annotations:
            class_id = ann['class_id']
            
            # 获取类别名称
            if class_id < len(id_to_class):
                class_name = id_to_class[class_id]
            else:
                class_name = f'class_{class_id}'
            
            x_min, y_min, x_max, y_max = ann['bbox']
            
            voc_annotations.append({
                'class_name': class_name,
                'bbox': [x_min, y_min, x_max, y_max],
                'pose': 'Unspecified',
                'truncated': 0,
                'difficult': 0
            })
        
        # 生成VOC XML文件
        xml_file = base_name + '.xml'
        xml_path = os.path.join(output_dir, xml_file)
        
        # 写入VOC XML标注
        write_voc_annotation(voc_annotations, xml_path, base_name + '.jpg', 
                           img_width, img_height)
        
        processed_count += 1
    
    print(f"VOC格式标注已保存到目录: {output_dir}")
    print(f"成功转换: {processed_count} 个文件")
    if skipped_count > 0:
        print(f"跳过: {skipped_count} 个文件 (无效标注)")
    
    # 如果没有提供类别列表，提示用户
    if not class_names and processed_count > 0:
        print("警告: 未提供类别名称列表，类别名称使用默认格式 'class_<id>'")
        print("建议创建类别列表文件以正确映射类别ID到名称")

def bbox_to_polygon(bbox):
    """将边界框转换为多边形"""
    x_min, y_min, x_max, y_max = bbox
    return [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]]

def polygon_to_bbox(polygon):
    """将多边形转换为边界框"""
    polygon = np.array(polygon)
    x_min = np.min(polygon[:, 0])
    y_min = np.min(polygon[:, 1])
    x_max = np.max(polygon[:, 0])
    y_max = np.max(polygon[:, 1])
    return [x_min, y_min, x_max, y_max]

def create_polygon_mask(image_shape, polygons):
    """根据多边形创建掩码"""
    mask = np.zeros(image_shape[:2], dtype=np.uint8)
    for polygon in polygons:
        pts = np.array(polygon, dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)
    return mask

def rgb_to_single_channel(image, channel='gray'):
    """将RGB图像转换为单通道图像"""
    if channel == 'gray':
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif channel == 'red':
        return image[:, :, 2]  # OpenCV使用BGR顺序
    elif channel == 'green':
        return image[:, :, 1]
    elif channel == 'blue':
        return image[:, :, 0]
    elif channel == 'hue':
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        return hsv[:, :, 0]
    elif channel == 'saturation':
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        return hsv[:, :, 1]
    elif channel == 'value':
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        return hsv[:, :, 2]
    else:
        print(f"未知的通道类型: {channel}")
        return image[:, :, 0]  # 默认返回蓝色通道

def single_channel_to_rgb(image, channel='gray'):
    """将单通道图像转换为RGB图像"""
    if len(image.shape) == 3:
        return image
    
    if channel == 'gray':
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif channel == 'red':
        return cv2.merge([np.zeros_like(image), np.zeros_like(image), image])
    elif channel == 'green':
        return cv2.merge([np.zeros_like(image), image, np.zeros_like(image)])
    elif channel == 'blue':
        return cv2.merge([image, np.zeros_like(image), np.zeros_like(image)])
    else:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)  # 默认转换为灰度RGB

def process_single_image_format(input_path, output_path, conversion_type, params=None):
    """处理单个图像格式转换"""
    if params is None:
        params = {}
    
    image = load_image(input_path)
    if image is None:
        return False
    
    if conversion_type == 'rgb_to_single':
        channel = params.get('channel', 'gray')
        result = rgb_to_single_channel(image, channel)
    elif conversion_type == 'single_to_rgb':
        channel = params.get('channel', 'gray')
        result = single_channel_to_rgb(image, channel)
    else:
        print(f"未知的转换类型: {conversion_type}")
        return False
    
    return save_image(result, output_path)

def process_directory_format(input_dir, output_dir, conversion_type, params=None, recursive=False, image_extensions=None):
    """批量处理目录中的图像格式转换"""
    if params is None:
        params = {}
    if image_extensions is None:
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    
    processed_count = 0
    failed_count = 0
    
    if recursive:
        walk_func = os.walk
    else:
        def walk_func(path):
            yield (path, [], [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
    
    for root, _, files in tqdm(walk_func(input_dir), desc="处理进度"):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                input_path = os.path.join(root, file)
                
                # 保持目录结构
                relative_path = os.path.relpath(root, input_dir)
                if relative_path == '.':
                    relative_path = ''
                
                output_path = os.path.join(output_dir, relative_path, file)
                
                if process_single_image_format(input_path, output_path, conversion_type, params):
                    processed_count += 1
                else:
                    failed_count += 1
    
    print(f"处理完成! 成功: {processed_count}, 失败: {failed_count}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='数据集格式转换工具')
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='选择转换命令')
    
    # YOLO转COCO
    yolo2coco = subparsers.add_parser('yolo2coco', help='YOLO格式转换为COCO格式')
    yolo2coco.add_argument('--yolo-dir', '-y', required=True, help='YOLO标注文件目录')
    yolo2coco.add_argument('--image-dir', '-i', required=True, help='图像文件目录')
    yolo2coco.add_argument('--output-json', '-o', required=True, help='输出COCO JSON文件路径')
    yolo2coco.add_argument('--class-file', '-c', help='类别名称文件路径')
    
    # COCO转YOLO
    coco2yolo = subparsers.add_parser('coco2yolo', help='COCO格式转换为YOLO格式')
    coco2yolo.add_argument('--coco-json', '-c', required=True, help='COCO JSON文件路径')
    coco2yolo.add_argument('--output-dir', '-o', required=True, help='输出YOLO标注目录')
    coco2yolo.add_argument('--image-dir', '-i', help='图像文件目录（用于验证）')
    
    # RGB转单通道
    rgb2single = subparsers.add_parser('rgb2single', help='RGB图像转换为单通道')
    rgb2single.add_argument('--input', '-i', required=True, help='输入图像或目录路径')
    rgb2single.add_argument('--output', '-o', required=True, help='输出图像或目录路径')
    rgb2single.add_argument('--channel', '-c', default='gray', 
                          choices=['gray', 'red', 'green', 'blue', 'hue', 'saturation', 'value'],
                          help='目标通道类型')
    rgb2single.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    # 单通道转RGB
    single2rgb = subparsers.add_parser('single2rgb', help='单通道图像转换为RGB')
    single2rgb.add_argument('--input', '-i', required=True, help='输入图像或目录路径')
    single2rgb.add_argument('--output', '-o', required=True, help='输出图像或目录路径')
    single2rgb.add_argument('--channel', '-c', default='gray', 
                          choices=['gray', 'red', 'green', 'blue'],
                          help='源通道类型')
    single2rgb.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    # VOC转YOLO
    voc2yolo = subparsers.add_parser('voc2yolo', help='VOC格式转换为YOLO格式')
    voc2yolo.add_argument('--voc-dir', '-v', required=True, help='VOC标注文件目录（包含XML文件）')
    voc2yolo.add_argument('--output-dir', '-o', required=True, help='输出YOLO标注目录')
    voc2yolo.add_argument('--class-file', '-c', help='类别名称文件路径')
    voc2yolo.add_argument('--image-dir', '-i', help='图像文件目录（用于验证）')
    
    # YOLO转VOC
    yolo2voc = subparsers.add_parser('yolo2voc', help='YOLO格式转换为VOC格式')
    yolo2voc.add_argument('--yolo-dir', '-y', required=True, help='YOLO标注文件目录')
    yolo2voc.add_argument('--output-dir', '-o', required=True, help='输出VOC标注目录')
    yolo2voc.add_argument('--class-file', '-c', help='类别名称文件路径')
    yolo2voc.add_argument('--image-dir', '-i', help='图像文件目录（用于获取图像尺寸）')
    
    return parser.parse_args()

def read_class_names(class_file):
    """从文件中读取类别名称"""
    class_names = []
    if os.path.exists(class_file):
        with open(class_file, 'r') as f:
            for line in f:
                class_name = line.strip()
                if class_name:
                    class_names.append(class_name)
    return class_names

def main():
    """主函数"""
    args = parse_arguments()
    
    if args.command == 'yolo2coco':
        # 读取类别名称
        class_names = []
        if args.class_file:
            class_names = read_class_names(args.class_file)
        
        # 执行YOLO到COCO转换
        yolo_to_coco(args.yolo_dir, args.image_dir, args.output_json, class_names)
    
    elif args.command == 'coco2yolo':
        # 执行COCO到YOLO转换
        coco_to_yolo(args.coco_json, args.output_dir, args.image_dir)
    
    elif args.command == 'voc2yolo':
        # 读取类别名称
        class_names = []
        if args.class_file:
            class_names = read_class_names(args.class_file)
        
        # 执行VOC到YOLO转换
        voc_to_yolo(args.voc_dir, args.output_dir, class_names, args.image_dir)
    
    elif args.command == 'yolo2voc':
        # 读取类别名称
        class_names = []
        if args.class_file:
            class_names = read_class_names(args.class_file)
        
        # 执行YOLO到VOC转换
        yolo_to_voc(args.yolo_dir, args.output_dir, class_names, args.image_dir)
    
    elif args.command == 'rgb2single':
        params = {'channel': args.channel}
        
        if os.path.isfile(args.input):
            # 处理单个文件
            if process_single_image_format(args.input, args.output, 'rgb_to_single', params):
                print(f"图像已成功转换并保存到: {args.output}")
            else:
                print("图像转换失败")
        elif os.path.isdir(args.input):
            # 处理目录
            process_directory_format(args.input, args.output, 'rgb_to_single', params, args.recursive)
        else:
            print(f"输入路径不存在: {args.input}")
    
    elif args.command == 'single2rgb':
        params = {'channel': args.channel}
        
        if os.path.isfile(args.input):
            # 处理单个文件
            if process_single_image_format(args.input, args.output, 'single_to_rgb', params):
                print(f"图像已成功转换并保存到: {args.output}")
            else:
                print("图像转换失败")
        elif os.path.isdir(args.input):
            # 处理目录
            process_directory_format(args.input, args.output, 'single_to_rgb', params, args.recursive)
        else:
            print(f"输入路径不存在: {args.input}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()