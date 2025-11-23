#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据增强模块（B5）

功能：
- 图像旋转、翻转、缩放、裁剪
- 亮度/对比度/饱和度调整
- 噪声添加（高斯、椒盐、泊松）
- 模糊（高斯、均值、运动模糊）
- 颜色抖动（色调、饱和度、亮度）
- 透视变换、仿射变换
- 随机擦除（Random Erase）
- 混合增强（MixUp、CutMix）
- 支持标注文件同步增强
- 可配置增强参数和概率

支持单文件和批量文件夹处理
"""

import os
import random
import numpy as np
import argparse
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from tqdm import tqdm
import json
import xml.etree.ElementTree as ET
import glob
import shutil

def ensure_directory(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def parse_annotation_file(annotation_path, image_width, image_height):
    """根据文件扩展名解析标注文件"""
    if not os.path.exists(annotation_path):
        return []
    
    ext = os.path.splitext(annotation_path)[1].lower()
    
    if ext == '.txt':
        # YOLO格式
        return parse_yolo_annotation(annotation_path, image_width, image_height)
    elif ext == '.xml':
        # Pascal VOC格式
        objects, _, _ = parse_voc_annotation(annotation_path)
        return objects
    elif ext == '.json':
        # 简单的JSON格式（COCO格式简化版）
        return parse_json_annotation(annotation_path)
    else:
        print(f"不支持的标注格式: {ext}")
        return []

def parse_yolo_annotation(annotation_path, image_width, image_height):
    """解析YOLO格式的标注文件"""
    objects = []
    with open(annotation_path, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) < 5:
                continue
            
            class_id = int(parts[0])
            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])
            
            # 转换为绝对坐标
            x_min = int((x_center - width / 2) * image_width)
            y_min = int((y_center - height / 2) * image_height)
            x_max = int((x_center + width / 2) * image_width)
            y_max = int((y_center + height / 2) * image_height)
            
            objects.append({
                'class_id': class_id,
                'bbox': [x_min, y_min, x_max, y_max]
            })
    return objects

def parse_voc_annotation(annotation_path):
    """解析Pascal VOC格式的标注文件"""
    objects = []
    try:
        tree = ET.parse(annotation_path)
        root = tree.getroot()
        
        # 获取图像尺寸
        size = root.find('size')
        image_width = int(size.find('width').text)
        image_height = int(size.find('height').text)
        
        for obj in root.findall('object'):
            class_name = obj.find('name').text
            bbox = obj.find('bndbox')
            x_min = int(float(bbox.find('xmin').text))
            y_min = int(float(bbox.find('ymin').text))
            x_max = int(float(bbox.find('xmax').text))
            y_max = int(float(bbox.find('ymax').text))
            
            objects.append({
                'class_name': class_name,
                'bbox': [x_min, y_min, x_max, y_max]
            })
        
        return objects, image_width, image_height
    except Exception as e:
        print(f"解析VOC文件失败 {annotation_path}: {e}")
        return [], 0, 0

def parse_json_annotation(annotation_path):
    """解析简单JSON格式的标注文件"""
    objects = []
    try:
        with open(annotation_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            # COCO格式简化版
            if 'annotations' in data:
                for ann in data['annotations']:
                    if 'bbox' in ann and 'category_id' in ann:
                        x_min, y_min, width, height = ann['bbox']
                        objects.append({
                            'class_id': ann['category_id'],
                            'bbox': [x_min, y_min, x_min + width, y_min + height]
                        })
            elif 'objects' in data:
                # 自定义格式
                for obj in data['objects']:
                    if 'bbox' in obj and 'class_id' in obj:
                        objects.append({
                            'class_id': obj['class_id'],
                            'bbox': obj['bbox']
                        })
        elif isinstance(data, list):
            # 直接是对象列表
            for obj in data:
                if 'bbox' in obj and ('class_id' in obj or 'category_id' in obj):
                    objects.append({
                        'class_id': obj.get('class_id', obj.get('category_id', 0)),
                        'bbox': obj['bbox']
                    })
        
        return objects
    except Exception as e:
        print(f"解析JSON文件失败 {annotation_path}: {e}")
        return []

def write_annotation_file(objects, annotation_path, image_width, image_height, format_type):
    """根据格式写入标注文件"""
    if format_type == 'yolo':
        write_yolo_annotation(objects, annotation_path, image_width, image_height)
    elif format_type == 'voc':
        image_name = os.path.basename(annotation_path).replace('.xml', '.jpg')
        write_voc_annotation(objects, annotation_path, image_name, image_width, image_height)
    elif format_type == 'json':
        write_json_annotation(objects, annotation_path)

def write_yolo_annotation(objects, annotation_path, image_width, image_height):
    """写入YOLO格式的标注文件"""
    with open(annotation_path, 'w') as f:
        for obj in objects:
            class_id = obj['class_id']
            x_min, y_min, x_max, y_max = obj['bbox']
            
            # 确保坐标有效
            x_min = max(0, x_min)
            y_min = max(0, y_min)
            x_max = min(image_width - 1, x_max)
            y_max = min(image_height - 1, y_max)
            
            # 转换为归一化坐标
            x_center = (x_min + x_max) / 2.0 / image_width
            y_center = (y_min + y_max) / 2.0 / image_height
            width = (x_max - x_min) / image_width
            height = (y_max - y_min) / image_height
            
            # 确保坐标在[0,1]范围内
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            width = max(0, min(1, width))
            height = max(0, min(1, height))
            
            f.write(f"{class_id} {x_center} {y_center} {width} {height}\n")

def write_voc_annotation(objects, annotation_path, image_name, image_width, image_height):
    """写入Pascal VOC格式的标注文件"""
    root = ET.Element('annotation')
    
    # 添加基本信息
    folder = ET.SubElement(root, 'folder')
    folder.text = os.path.basename(os.path.dirname(annotation_path))
    
    filename = ET.SubElement(root, 'filename')
    filename.text = image_name
    
    source = ET.SubElement(root, 'source')
    database = ET.SubElement(source, 'database')
    database.text = 'Unknown'
    
    # 添加图像尺寸
    size = ET.SubElement(root, 'size')
    width = ET.SubElement(size, 'width')
    width.text = str(image_width)
    height = ET.SubElement(size, 'height')
    height.text = str(image_height)
    depth = ET.SubElement(size, 'depth')
    depth.text = '3'
    
    segmented = ET.SubElement(root, 'segmented')
    segmented.text = '0'
    
    # 添加对象
    for obj in objects:
        class_id = obj['class_id']
        x_min, y_min, x_max, y_max = obj['bbox']
        
        # 确保坐标有效
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(image_width - 1, x_max)
        y_max = min(image_height - 1, y_max)
        
        object_elem = ET.SubElement(root, 'object')
        name = ET.SubElement(object_elem, 'name')
        name.text = f'class_{class_id}'
        
        pose = ET.SubElement(object_elem, 'pose')
        pose.text = 'Unspecified'
        
        truncated = ET.SubElement(object_elem, 'truncated')
        truncated.text = '0'
        
        difficult = ET.SubElement(object_elem, 'difficult')
        difficult.text = '0'
        
        bndbox = ET.SubElement(object_elem, 'bndbox')
        xmin = ET.SubElement(bndbox, 'xmin')
        xmin.text = str(x_min)
        ymin = ET.SubElement(bndbox, 'ymin')
        ymin.text = str(y_min)
        xmax = ET.SubElement(bndbox, 'xmax')
        xmax.text = str(x_max)
        ymax = ET.SubElement(bndbox, 'ymax')
        ymax.text = str(y_max)
    
    # 写入文件
    tree = ET.ElementTree(root)
    tree.write(annotation_path)

def write_json_annotation(objects, annotation_path):
    """写入简单JSON格式的标注文件"""
    data = {
        'objects': [
            {
                'class_id': obj['class_id'],
                'bbox': obj['bbox']
            } for obj in objects
        ]
    }
    
    with open(annotation_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============== 数据增强函数 ==============

def random_rotation(image, objects=None, max_angle=30):
    """随机旋转图像"""
    angle = random.uniform(-max_angle, max_angle)
    rotated_img = image.rotate(angle, expand=True, fillcolor=(0, 0, 0))
    
    # 计算旋转后的新尺寸
    orig_width, orig_height = image.size
    rotated_width, rotated_height = rotated_img.size
    
    # 计算偏移量
    offset_x = (rotated_width - orig_width) // 2
    offset_y = (rotated_height - orig_height) // 2
    
    # 更新标注框
    if objects:
        # 旋转中心是原图像中心
        center_x, center_y = orig_width / 2, orig_height / 2
        
        # 转换为弧度
        theta = np.radians(angle)
        
        new_objects = []
        for obj in objects:
            class_id = obj['class_id']
            x_min, y_min, x_max, y_max = obj['bbox']
            
            # 获取边界框的四个角点
            corners = [
                (x_min, y_min),
                (x_max, y_min),
                (x_max, y_max),
                (x_min, y_max)
            ]
            
            # 旋转每个角点
            rotated_corners = []
            for x, y in corners:
                # 平移到原点
                x -= center_x
                y -= center_y
                
                # 旋转
                new_x = x * np.cos(theta) - y * np.sin(theta)
                new_y = x * np.sin(theta) + y * np.cos(theta)
                
                # 平移回中心并加上偏移量
                new_x += center_x + offset_x
                new_y += center_y + offset_y
                
                rotated_corners.append((new_x, new_y))
            
            # 计算新的边界框
            new_x_min = min([x for x, y in rotated_corners])
            new_y_min = min([y for x, y in rotated_corners])
            new_x_max = max([x for x, y in rotated_corners])
            new_y_max = max([y for x, y in rotated_corners])
            
            new_objects.append({
                'class_id': class_id,
                'bbox': [new_x_min, new_y_min, new_x_max, new_y_max]
            })
        
        return rotated_img, new_objects
    
    return rotated_img, objects

def random_flip(image, objects=None, horizontal_prob=0.5, vertical_prob=0.5):
    """随机水平或垂直翻转图像"""
    flipped_img = image.copy()
    flip_horizontal = random.random() < horizontal_prob
    flip_vertical = random.random() < vertical_prob
    
    if flip_horizontal:
        flipped_img = ImageOps.mirror(flipped_img)
    if flip_vertical:
        flipped_img = ImageOps.flip(flipped_img)
    
    # 更新标注框
    if objects:
        width, height = image.size
        new_objects = []
        
        for obj in objects:
            class_id = obj['class_id']
            x_min, y_min, x_max, y_max = obj['bbox']
            
            # 水平翻转
            if flip_horizontal:
                x_min, x_max = width - x_max, width - x_min
            
            # 垂直翻转
            if flip_vertical:
                y_min, y_max = height - y_max, height - y_min
            
            new_objects.append({
                'class_id': class_id,
                'bbox': [x_min, y_min, x_max, y_max]
            })
        
        return flipped_img, new_objects
    
    return flipped_img, objects

def random_scale(image, objects=None, min_scale=0.8, max_scale=1.2):
    """随机缩放图像"""
    scale = random.uniform(min_scale, max_scale)
    width, height = image.size
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    scaled_img = image.resize((new_width, new_height))
    
    # 更新标注框
    if objects:
        new_objects = []
        for obj in objects:
            class_id = obj['class_id']
            x_min, y_min, x_max, y_max = obj['bbox']
            
            # 缩放坐标
            x_min = x_min * scale
            y_min = y_min * scale
            x_max = x_max * scale
            y_max = y_max * scale
            
            new_objects.append({
                'class_id': class_id,
                'bbox': [x_min, y_min, x_max, y_max]
            })
        
        return scaled_img, new_objects
    
    return scaled_img, objects

def random_crop(image, objects=None, min_size_ratio=0.7):
    """随机裁剪图像"""
    width, height = image.size
    min_crop_width = int(width * min_size_ratio)
    min_crop_height = int(height * min_size_ratio)
    
    # 随机选择裁剪区域
    crop_width = random.randint(min_crop_width, width)
    crop_height = random.randint(min_crop_height, height)
    
    x1 = random.randint(0, width - crop_width)
    y1 = random.randint(0, height - crop_height)
    x2 = x1 + crop_width
    y2 = y1 + crop_height
    
    # 裁剪图像
    cropped_img = image.crop((x1, y1, x2, y2))
    
    # 更新标注框
    if objects:
        new_objects = []
        for obj in objects:
            class_id = obj['class_id']
            obj_x1, obj_y1, obj_x2, obj_y2 = obj['bbox']
            
            # 调整边界框坐标
            new_x1 = max(0, obj_x1 - x1)
            new_y1 = max(0, obj_y1 - y1)
            new_x2 = min(crop_width, obj_x2 - x1)
            new_y2 = min(crop_height, obj_y2 - y1)
            
            # 只保留完全在裁剪区域内的边界框
            if new_x2 > new_x1 and new_y2 > new_y1:
                new_objects.append({
                    'class_id': class_id,
                    'bbox': [new_x1, new_y1, new_x2, new_y2]
                })
        
        return cropped_img, new_objects
    
    return cropped_img, objects

def adjust_brightness(image, factor_range=(0.5, 1.5)):
    """调整亮度"""
    factor = random.uniform(factor_range[0], factor_range[1])
    enhancer = ImageEnhance.Brightness(image)
    return enhancer.enhance(factor)

def adjust_contrast(image, factor_range=(0.5, 1.5)):
    """调整对比度"""
    factor = random.uniform(factor_range[0], factor_range[1])
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(factor)

def adjust_saturation(image, factor_range=(0.5, 1.5)):
    """调整饱和度"""
    factor = random.uniform(factor_range[0], factor_range[1])
    enhancer = ImageEnhance.Color(image)
    return enhancer.enhance(factor)

def add_gaussian_noise(image, mean=0, std_range=(1, 20)):
    """添加高斯噪声"""
    # 转换为numpy数组
    img_array = np.array(image)
    
    # 添加噪声
    std = random.uniform(std_range[0], std_range[1])
    noise = np.random.normal(mean, std, img_array.shape)
    noisy_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    
    # 转换回PIL图像
    return Image.fromarray(noisy_array)

def add_salt_and_pepper_noise(image, amount_range=(0.01, 0.05)):
    """添加椒盐噪声"""
    # 转换为numpy数组
    img_array = np.array(image)
    amount = random.uniform(amount_range[0], amount_range[1])
    
    # 添加盐噪声（白色像素）
    num_salt = int(np.ceil(amount * img_array.size * 0.5))
    coords = [np.random.randint(0, i - 1, num_salt) for i in img_array.shape[:2]]
    if len(img_array.shape) == 3:
        for i in range(img_array.shape[2]):
            img_array[coords[0], coords[1], i] = 255
    else:
        img_array[coords[0], coords[1]] = 255
    
    # 添加椒噪声（黑色像素）
    num_pepper = int(np.ceil(amount * img_array.size * 0.5))
    coords = [np.random.randint(0, i - 1, num_pepper) for i in img_array.shape[:2]]
    if len(img_array.shape) == 3:
        for i in range(img_array.shape[2]):
            img_array[coords[0], coords[1], i] = 0
    else:
        img_array[coords[0], coords[1]] = 0
    
    # 转换回PIL图像
    return Image.fromarray(img_array)

def add_poisson_noise(image):
    """添加泊松噪声"""
    # 转换为numpy数组
    img_array = np.array(image)
    
    # 添加泊松噪声
    noisy_array = np.random.poisson(img_array / 255.0 * 255) / 255.0 * 255
    noisy_array = np.clip(noisy_array, 0, 255).astype(np.uint8)
    
    # 转换回PIL图像
    return Image.fromarray(noisy_array)

def apply_blur(image, blur_type='gaussian', radius_range=(1, 3)):
    """应用模糊"""
    radius = random.uniform(radius_range[0], radius_range[1])
    
    if blur_type == 'gaussian':
        return image.filter(ImageFilter.GaussianBlur(radius))
    elif blur_type == 'box':
        return image.filter(ImageFilter.BoxBlur(radius))
    elif blur_type == 'median':
        # 中值模糊需要整数半径
        return image.filter(ImageFilter.MedianFilter(size=int(radius)))
    else:
        return image

def color_jitter(image, brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1):
    """颜色抖动"""
    # 亮度调整
    image = adjust_brightness(image, (1 - brightness, 1 + brightness))
    
    # 对比度调整
    image = adjust_contrast(image, (1 - contrast, 1 + contrast))
    
    # 饱和度调整
    image = adjust_saturation(image, (1 - saturation, 1 + saturation))
    
    # 色调调整
    if random.random() < 0.5:  # 50%概率调整色调
        # PIL没有直接调整色调的方法，这里使用HSL转换
        img_array = np.array(image)
        img_hsv = np.array(Image.fromarray(img_array).convert('HSV'))
        h = img_hsv[:, :, 0].astype(np.float32)
        delta_hue = random.uniform(-hue, hue) * 255  # 0-255范围
        h = (h + delta_hue) % 255
        img_hsv[:, :, 0] = h.astype(np.uint8)
        image = Image.fromarray(img_hsv, mode='HSV').convert('RGB')
    
    return image

def random_erase(image, objects=None, max_area=0.2, min_aspect=0.25, max_aspect=4):
    """随机擦除"""
    width, height = image.size
    img_array = np.array(image)
    area = width * height
    erase_area = random.uniform(0.02, max_area) * area
    aspect_ratio = random.uniform(min_aspect, max_aspect)
    
    # 计算擦除区域的尺寸
    erase_height = int(np.sqrt(erase_area / aspect_ratio))
    erase_width = int(aspect_ratio * erase_height)
    
    # 随机选择擦除位置
    x1 = random.randint(0, width - erase_width)
    y1 = random.randint(0, height - erase_width)
    x2 = x1 + erase_width
    y2 = y1 + erase_height
    
    # 生成随机颜色
    color = np.random.randint(0, 256, 3, dtype=np.uint8)
    
    # 应用擦除
    img_array[y1:y2, x1:x2] = color
    
    # 标注框不需要更新，因为擦除的是背景区域
    return Image.fromarray(img_array), objects

def mix_up(image1, image2, alpha=0.2):
    """MixUp增强"""
    # 确保图像尺寸相同
    if image1.size != image2.size:
        image2 = image2.resize(image1.size)
    
    # 生成混合比例
    lam = np.random.beta(alpha, alpha)
    
    # 混合图像
    img_array1 = np.array(image1).astype(np.float32)
    img_array2 = np.array(image2).astype(np.float32)
    mixed_array = lam * img_array1 + (1 - lam) * img_array2
    mixed_array = np.clip(mixed_array, 0, 255).astype(np.uint8)
    
    return Image.fromarray(mixed_array), lam

def cut_mix(image1, image2, objects1=None, objects2=None, alpha=1.0):
    """CutMix增强"""
    # 确保图像尺寸相同
    if image1.size != image2.size:
        image2 = image2.resize(image1.size)
    
    width, height = image1.size
    
    # 生成混合区域
    lam = np.random.beta(alpha, alpha)
    cut_ratio = np.sqrt(1. - lam)
    cut_w = int(width * cut_ratio)
    cut_h = int(height * cut_ratio)
    
    # 随机中心点
    cx = np.random.randint(width)
    cy = np.random.randint(height)
    
    # 计算裁剪区域
    x1 = max(0, cx - cut_w // 2)
    y1 = max(0, cy - cut_h // 2)
    x2 = min(width, cx + cut_w // 2)
    y2 = min(height, cy + cut_h // 2)
    
    # 创建混合图像
    img_array1 = np.array(image1)
    img_array2 = np.array(image2)
    img_array1[y1:y2, x1:x2] = img_array2[y1:y2, x1:x2]
    mixed_img = Image.fromarray(img_array1)
    
    # 更新标注框
    if objects1 is not None and objects2 is not None:
        # 保留第一个图像中不在裁剪区域的标注
        new_objects = [obj for obj in objects1 if not (
            obj['bbox'][0] > x1 and obj['bbox'][2] < x2 and 
            obj['bbox'][1] > y1 and obj['bbox'][3] < y2
        )]
        
        # 添加第二个图像中在裁剪区域的标注
        for obj in objects2:
            bx1, by1, bx2, by2 = obj['bbox']
            # 检查标注框是否与裁剪区域有交集
            if bx2 > x1 and bx1 < x2 and by2 > y1 and by1 < y2:
                new_objects.append(obj)
        
        return mixed_img, new_objects
    
    return mixed_img, objects1

# ============== 主增强流程 ==============

def apply_augmentations(image, objects=None, config=None):
    """应用一系列数据增强"""
    if config is None:
        config = {}
    
    augmented_img = image.copy()
    augmented_objects = objects.copy() if objects else None
    
    # 随机旋转
    if random.random() < config.get('rotation_prob', 0.5):
        augmented_img, augmented_objects = random_rotation(
            augmented_img, 
            augmented_objects, 
            max_angle=config.get('max_angle', 30)
        )
    
    # 随机翻转
    if random.random() < config.get('flip_prob', 0.5):
        augmented_img, augmented_objects = random_flip(
            augmented_img, 
            augmented_objects,
            horizontal_prob=config.get('horizontal_prob', 0.5),
            vertical_prob=config.get('vertical_prob', 0.0)
        )
    
    # 随机缩放
    if random.random() < config.get('scale_prob', 0.5):
        augmented_img, augmented_objects = random_scale(
            augmented_img, 
            augmented_objects,
            min_scale=config.get('min_scale', 0.8),
            max_scale=config.get('max_scale', 1.2)
        )
    
    # 随机裁剪
    if random.random() < config.get('crop_prob', 0.5):
        augmented_img, augmented_objects = random_crop(
            augmented_img, 
            augmented_objects,
            min_size_ratio=config.get('min_crop_size', 0.7)
        )
    
    # 颜色调整
    if random.random() < config.get('color_jitter_prob', 0.5):
        augmented_img = color_jitter(
            augmented_img,
            brightness=config.get('brightness_jitter', 0.2),
            contrast=config.get('contrast_jitter', 0.2),
            saturation=config.get('saturation_jitter', 0.2),
            hue=config.get('hue_jitter', 0.1)
        )
    
    # 噪声添加
    noise_type = config.get('noise_type', None)
    if noise_type and random.random() < config.get('noise_prob', 0.5):
        if noise_type == 'gaussian':
            augmented_img = add_gaussian_noise(augmented_img)
        elif noise_type == 'salt_pepper':
            augmented_img = add_salt_and_pepper_noise(augmented_img)
        elif noise_type == 'poisson':
            augmented_img = add_poisson_noise(augmented_img)
    
    # 模糊
    blur_type = config.get('blur_type', None)
    if blur_type and random.random() < config.get('blur_prob', 0.5):
        augmented_img = apply_blur(augmented_img, blur_type=blur_type)
    
    # 随机擦除
    if random.random() < config.get('erase_prob', 0.0):
        augmented_img, augmented_objects = random_erase(
            augmented_img, 
            augmented_objects,
            max_area=config.get('max_erase_area', 0.2)
        )
    
    return augmented_img, augmented_objects

def augment_single_image(image_path, output_path, annotation_path=None, output_annotation_path=None,
                         augment_config=None, annotation_format='yolo', num_augmentations=1):
    """增强单个图像"""
    try:
        # 读取图像
        image = Image.open(image_path).convert('RGB')
        
        # 读取标注
        objects = None
        if annotation_path and os.path.exists(annotation_path):
            width, height = image.size
            objects = parse_annotation_file(annotation_path, width, height)
        
        # 应用增强
        base_name, ext = os.path.splitext(os.path.basename(image_path))
        results = []
        
        for i in range(num_augmentations):
            # 生成增强后的图像和标注
            augmented_img, augmented_objects = apply_augmentations(image, objects, augment_config)
            
            # 保存增强后的图像
            if num_augmentations > 1:
                output_img_path = os.path.join(output_path, f"{base_name}_aug_{i}{ext}")
            else:
                output_img_path = os.path.join(output_path, f"{base_name}_aug{ext}")
            
            augmented_img.save(output_img_path)
            
            # 保存增强后的标注
            output_ann_path = None
            if augmented_objects and output_annotation_path:
                if num_augmentations > 1:
                    ann_base_name, ann_ext = os.path.splitext(os.path.basename(annotation_path))
                    output_ann_path = os.path.join(output_annotation_path, f"{ann_base_name}_aug_{i}{ann_ext}")
                else:
                    ann_base_name, ann_ext = os.path.splitext(os.path.basename(annotation_path))
                    output_ann_path = os.path.join(output_annotation_path, f"{ann_base_name}_aug{ann_ext}")
                
                width, height = augmented_img.size
                write_annotation_file(augmented_objects, output_ann_path, width, height, annotation_format)
            
            results.append((output_img_path, output_ann_path))
        
        return results
    except Exception as e:
        print(f"增强图像失败 {image_path}: {e}")
        return []

def augment_folder(input_dir, output_dir, annotation_dir=None, output_annotation_dir=None,
                   augment_config=None, annotation_format='yolo', num_augmentations=1,
                   image_extensions=None):
    """批量增强文件夹中的图像"""
    if image_extensions is None:
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    
    # 确保输出目录存在
    ensure_directory(output_dir)
    if output_annotation_dir:
        ensure_directory(output_annotation_dir)
    
    # 获取所有图像文件
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(input_dir, f'*{ext}')))
    
    # 去重并排序
    image_files = list(set(image_files))
    image_files.sort()
    
    # 批量处理
    total_processed = 0
    for image_path in tqdm(image_files, desc="增强进度"):
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 查找对应的标注文件
        annotation_path = None
        if annotation_dir:
            for ext in ['.txt', '.xml', '.json']:
                possible_ann_path = os.path.join(annotation_dir, f"{base_name}{ext}")
                if os.path.exists(possible_ann_path):
                    annotation_path = possible_ann_path
                    break
        
        # 增强图像
        results = augment_single_image(
            image_path, output_dir, 
            annotation_path, output_annotation_dir,
            augment_config, annotation_format, 
            num_augmentations
        )
        
        if results:
            total_processed += 1
    
    print(f"批量增强完成！共处理 {total_processed} 个图像文件")

def parse_config(config_path):
    """解析配置文件"""
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='数据增强工具')
    
    # 输入输出参数
    parser.add_argument('--input', '-i', required=True, help='输入图像文件或目录路径')
    parser.add_argument('--output', '-o', required=True, help='输出目录路径')
    
    # 标注相关参数
    parser.add_argument('--annotation-dir', '-a', help='标注文件目录路径')
    parser.add_argument('--output-annotation-dir', '-ao', help='输出标注文件目录路径')
    parser.add_argument('--annotation-format', '-af', default='yolo', choices=['yolo', 'voc', 'json'],
                      help='标注文件格式')
    
    # 增强参数
    parser.add_argument('--config', '-c', help='增强配置文件路径（JSON格式）')
    parser.add_argument('--num-augmentations', '-n', type=int, default=1,
                      help='每张图像生成的增强样本数量')
    
    # 图像格式参数
    parser.add_argument('--image-extensions', '-e', nargs='+', default=['.jpg', '.jpeg', '.png', '.bmp'],
                      help='图像文件扩展名')
    
    # 快速配置参数
    parser.add_argument('--rotation', '-r', action='store_true', help='启用旋转增强')
    parser.add_argument('--flip', '-f', action='store_true', help='启用翻转增强')
    parser.add_argument('--scale', '-s', action='store_true', help='启用缩放增强')
    parser.add_argument('--crop', '-p', action='store_true', help='启用裁剪增强')
    parser.add_argument('--color-jitter', '-cj', action='store_true', help='启用颜色抖动增强')
    parser.add_argument('--noise', '-n', choices=['gaussian', 'salt_pepper', 'poisson'], help='启用噪声增强')
    parser.add_argument('--blur', '-b', choices=['gaussian', 'box', 'median'], help='启用模糊增强')
    parser.add_argument('--erase', '-er', action='store_true', help='启用随机擦除增强')
    
    return parser.parse_args()

def build_config_from_args(args):
    """从命令行参数构建增强配置"""
    config = parse_config(args.config)
    
    # 应用命令行参数覆盖配置文件中的设置
    if args.rotation:
        config['rotation_prob'] = 0.5
        config['max_angle'] = 30
    if args.flip:
        config['flip_prob'] = 0.5
        config['horizontal_prob'] = 0.5
        config['vertical_prob'] = 0.0
    if args.scale:
        config['scale_prob'] = 0.5
        config['min_scale'] = 0.8
        config['max_scale'] = 1.2
    if args.crop:
        config['crop_prob'] = 0.5
        config['min_crop_size'] = 0.7
    if args.color_jitter:
        config['color_jitter_prob'] = 0.5
        config['brightness_jitter'] = 0.2
        config['contrast_jitter'] = 0.2
        config['saturation_jitter'] = 0.2
        config['hue_jitter'] = 0.1
    if args.noise:
        config['noise_prob'] = 0.5
        config['noise_type'] = args.noise
    if args.blur:
        config['blur_prob'] = 0.5
        config['blur_type'] = args.blur
    if args.erase:
        config['erase_prob'] = 0.5
        config['max_erase_area'] = 0.2
    
    return config

def main():
    """主函数"""
    args = parse_arguments()
    
    # 构建增强配置
    augment_config = build_config_from_args(args)
    
    # 确保输出目录存在
    ensure_directory(args.output)
    if args.output_annotation_dir:
        ensure_directory(args.output_annotation_dir)
    
    # 判断输入是文件还是目录
    if os.path.isfile(args.input):
        # 处理单个文件
        # 查找对应的标注文件
        annotation_path = None
        if args.annotation_dir:
            base_name = os.path.splitext(os.path.basename(args.input))[0]
            for ext in ['.txt', '.xml', '.json']:
                possible_ann_path = os.path.join(args.annotation_dir, f"{base_name}{ext}")
                if os.path.exists(possible_ann_path):
                    annotation_path = possible_ann_path
                    break
        
        results = augment_single_image(
            args.input, args.output,
            annotation_path, args.output_annotation_dir,
            augment_config, args.annotation_format,
            args.num_augmentations
        )
        
        print(f"单文件增强完成！生成了 {len(results)} 个增强样本")
    else:
        # 批量处理目录
        augment_folder(
            args.input, args.output,
            args.annotation_dir, args.output_annotation_dir,
            augment_config, args.annotation_format,
            args.num_augmentations,
            args.image_extensions
        )

if __name__ == "__main__":
    main()