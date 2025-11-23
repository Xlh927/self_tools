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