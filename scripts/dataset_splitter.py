#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集拆分模块（B3）

功能：
- 随机/分层拆分（train/val/test）
- 保持类别比例
- 自动生成目录

支持单文件和批量文件夹处理
"""

import os
import sys
import random
import shutil
import argparse
import json
import xml.etree.ElementTree as ET
import glob
from typing import List, Dict, Any, Tuple, Set, Optional
import numpy as np
from collections import defaultdict, Counter
import logging

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


def read_yolo_label(label_path: str) -> List[int]:
    """
    读取YOLO格式标签，获取类别ID列表
    
    Args:
        label_path: 标签文件路径
    
    Returns:
        类别ID列表
    """
    class_ids = []
    if not os.path.exists(label_path):
        return class_ids
    
    try:
        with open(label_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    try:
                        class_id = int(float(parts[0]))
                        class_ids.append(class_id)
                    except ValueError:
                        continue
    except Exception as e:
        logger.error(f"读取YOLO标签文件失败 {label_path}: {str(e)}")
    
    return class_ids


def read_pascal_voc_label(label_path: str, class_mapping: Optional[Dict[str, int]] = None) -> List[int]:
    """
    读取Pascal VOC格式标签，获取类别ID列表
    
    Args:
        label_path: 标签文件路径
        class_mapping: 类别名称到ID的映射字典
    
    Returns:
        类别ID列表
    """
    class_ids = []
    if not os.path.exists(label_path):
        return class_ids
    
    try:
        tree = ET.parse(label_path)
        root = tree.getroot()
        
        for obj in root.findall('object'):
            name_elem = obj.find('name')
            if name_elem is not None and name_elem.text:
                class_name = name_elem.text.strip()
                if class_mapping:
                    if class_name in class_mapping:
                        class_id = class_mapping[class_name]
                        class_ids.append(class_id)
                    else:
                        logger.warning(f"类别名称 '{class_name}' 未在映射中找到")
                else:
                    # 如果没有映射，使用类别名称的哈希值作为临时ID
                    class_id = hash(class_name) % 1000
                    class_ids.append(class_id)
    except Exception as e:
        logger.error(f"读取Pascal VOC标签文件失败 {label_path}: {str(e)}")
    
    return class_ids


def read_coco_annotation(coco_json_path: str) -> Dict[str, List[int]]:
    """
    读取COCO格式的标注文件，获取每个图像的类别ID列表
    
    Args:
        coco_json_path: COCO格式的JSON文件路径
    
    Returns:
        图像ID到类别ID列表的映射
    """
    image_to_classes = defaultdict(list)
    
    try:
        with open(coco_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建图像ID到文件名的映射
        image_id_to_name = {img['id']: os.path.splitext(img['file_name'])[0] for img in data.get('images', [])}
        
        # 遍历标注，获取每个图像的类别
        for annotation in data.get('annotations', []):
            image_id = annotation.get('image_id')
            category_id = annotation.get('category_id')
            
            if image_id in image_id_to_name:
                image_name = image_id_to_name[image_id]
                image_to_classes[image_name].append(category_id)
    except Exception as e:
        logger.error(f"读取COCO标注文件失败 {coco_json_path}: {str(e)}")
    
    return image_to_classes


def load_class_distribution(
    image_paths: List[str],
    label_dir: str,
    label_format: str = 'yolo',
    coco_json_path: Optional[str] = None,
    class_mapping: Optional[Dict[str, int]] = None
) -> Tuple[Dict[str, List[int]], Dict[str, int]]:
    """
    加载数据集中每个图像的类别分布
    
    Args:
        image_paths: 图像路径列表
        label_dir: 标签目录
        label_format: 标签格式 ('yolo', 'voc', 'coco')
        coco_json_path: COCO格式的JSON文件路径
        class_mapping: 类别名称到ID的映射字典
    
    Returns:
        (图像到类别列表的映射, 全局类别统计)
    """
    image_to_classes = {}
    global_class_count = defaultdict(int)
    
    if label_format == 'coco' and coco_json_path:
        # 对于COCO格式，直接从JSON文件读取
        image_to_classes = read_coco_annotation(coco_json_path)
        # 统计全局类别数量
        for classes in image_to_classes.values():
            for class_id in classes:
                global_class_count[class_id] += 1
        
        # 确保所有图像都在映射中
        for img_path in image_paths:
            img_name = os.path.splitext(os.path.basename(img_path))[0]
            if img_name not in image_to_classes:
                image_to_classes[img_name] = []
    else:
        # 对于YOLO或VOC格式，逐个读取标签文件
        label_ext = '.txt' if label_format == 'yolo' else '.xml'
        
        for img_path in image_paths:
            img_name = os.path.splitext(os.path.basename(img_path))[0]
            label_path = get_label_path(img_path, label_dir, label_ext)
            
            if label_format == 'yolo':
                class_ids = read_yolo_label(label_path)
            else:  # voc
                class_ids = read_pascal_voc_label(label_path, class_mapping)
            
            image_to_classes[img_name] = class_ids
            
            # 更新全局类别统计
            for class_id in class_ids:
                global_class_count[class_id] += 1
    
    logger.info(f"类别分布加载完成，共有 {len(global_class_count)} 个类别")
    return image_to_classes, dict(global_class_count)


def random_split(
    image_paths: List[str],
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: Optional[int] = None
) -> Tuple[List[str], List[str], List[str]]:
    """
    随机拆分数据集
    
    Args:
        image_paths: 图像路径列表
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        seed: 随机种子
    
    Returns:
        (训练集, 验证集, 测试集) 图像路径列表
    """
    # 验证比例
    total_ratio = train_ratio + val_ratio + test_ratio
    if not np.isclose(total_ratio, 1.0):
        logger.warning(f"比例之和不为1.0 ({total_ratio:.2f})，将进行归一化")
        # 归一化比例
        train_ratio /= total_ratio
        val_ratio /= total_ratio
        test_ratio /= total_ratio
    
    # 设置随机种子
    if seed is not None:
        random.seed(seed)
        logger.info(f"使用随机种子: {seed}")
    
    # 打乱图像路径
    shuffled = image_paths.copy()
    random.shuffle(shuffled)
    
    # 计算各集合的大小
    total_count = len(shuffled)
    train_count = int(total_count * train_ratio)
    val_count = int(total_count * val_ratio)
    
    # 拆分数据集
    train_set = shuffled[:train_count]
    val_set = shuffled[train_count:train_count + val_count]
    test_set = shuffled[train_count + val_count:]
    
    logger.info(f"随机拆分完成 - 训练集: {len(train_set)}, 验证集: {len(val_set)}, 测试集: {len(test_set)}")
    return train_set, val_set, test_set


def stratified_split(
    image_paths: List[str],
    image_to_classes: Dict[str, List[int]],
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: Optional[int] = None
) -> Tuple[List[str], List[str], List[str]]:
    """
    分层拆分数据集，保持类别比例
    
    Args:
        image_paths: 图像路径列表
        image_to_classes: 图像到类别列表的映射
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        seed: 随机种子
    
    Returns:
        (训练集, 验证集, 测试集) 图像路径列表
    """
    # 验证比例
    total_ratio = train_ratio + val_ratio + test_ratio
    if not np.isclose(total_ratio, 1.0):
        logger.warning(f"比例之和不为1.0 ({total_ratio:.2f})，将进行归一化")
        # 归一化比例
        train_ratio /= total_ratio
        val_ratio /= total_ratio
        test_ratio /= total_ratio
    
    # 设置随机种子
    if seed is not None:
        random.seed(seed)
        logger.info(f"使用随机种子: {seed}")
    
    # 按类别分组
    class_to_images = defaultdict(list)
    for img_path in image_paths:
        img_name = os.path.splitext(os.path.basename(img_path))[0]
        classes = image_to_classes.get(img_name, [])
        
        if not classes:  # 处理无标签图像
            class_to_images['__unlabeled__'].append(img_path)
        else:
            # 对于多类图像，将其分配到每个类别的组中
            for class_id in set(classes):
                class_to_images[class_id].append(img_path)
    
    # 初始化结果集合
    train_set = []
    val_set = []
    test_set = []
    
    # 已分配的图像集合，避免重复分配
    assigned_images = set()
    
    # 对每个类别进行分层采样
    for class_id, class_images in class_to_images.items():
        # 去重
        unique_images = list(set(class_images))
        random.shuffle(unique_images)
        
        # 计算该类别中未分配的图像数量
        unassigned = [img for img in unique_images if img not in assigned_images]
        
        # 计算各集合大小
        count = len(unassigned)
        train_count = int(count * train_ratio)
        val_count = int(count * val_ratio)
        
        # 分配图像
        train_batch = unassigned[:train_count]
        val_batch = unassigned[train_count:train_count + val_count]
        test_batch = unassigned[train_count + val_count:]
        
        # 更新结果集合和已分配集合
        train_set.extend(train_batch)
        val_set.extend(val_batch)
        test_set.extend(test_batch)
        
        assigned_images.update(train_batch)
        assigned_images.update(val_batch)
        assigned_images.update(test_batch)
    
    # 处理未分配的图像（可能是那些没有被任何类别组选中的）
    unassigned_images = [img for img in image_paths if img not in assigned_images]
    if unassigned_images:
        logger.warning(f"有 {len(unassigned_images)} 个图像未被分配，将随机分配到训练集")
        train_set.extend(unassigned_images)
    
    # 再次去重
    train_set = list(set(train_set))
    val_set = list(set(val_set))
    test_set = list(set(test_set))
    
    # 确保集合之间没有交集
    train_set = [img for img in train_set if img not in val_set and img not in test_set]
    val_set = [img for img in val_set if img not in test_set]
    
    logger.info(f"分层拆分完成 - 训练集: {len(train_set)}, 验证集: {len(val_set)}, 测试集: {len(test_set)}")
    return train_set, val_set, test_set


def copy_files(
    file_paths: List[str],
    source_dir: str,
    target_dir: str,
    preserve_structure: bool = False
) -> int:
    """
    复制文件到目标目录
    
    Args:
        file_paths: 文件路径列表
        source_dir: 源目录
        target_dir: 目标目录
        preserve_structure: 是否保留目录结构
    
    Returns:
        成功复制的文件数
    """
    copied_count = 0
    
    for file_path in file_paths:
        try:
            # 计算相对路径
            rel_path = os.path.relpath(file_path, source_dir)
            
            if preserve_structure:
                # 保留目录结构
                target_path = os.path.join(target_dir, rel_path)
                ensure_directory(os.path.dirname(target_path))
            else:
                # 不保留目录结构，直接复制到目标目录
                target_path = os.path.join(target_dir, os.path.basename(file_path))
            
            # 复制文件
            shutil.copy2(file_path, target_path)
            copied_count += 1
        except Exception as e:
            logger.error(f"复制文件失败 {file_path} -> {target_path}: {str(e)}")
    
    return copied_count


def copy_dataset_files(
    image_sets: Tuple[List[str], List[str], List[str]],
    image_dir: str,
    label_dir: str,
    output_dir: str,
    label_format: str = 'yolo',
    preserve_structure: bool = False
) -> Dict[str, int]:
    """
    复制数据集文件到输出目录
    
    Args:
        image_sets: (训练集, 验证集, 测试集) 图像路径列表
        image_dir: 图像目录
        label_dir: 标签目录
        output_dir: 输出目录
        label_format: 标签格式
        preserve_structure: 是否保留目录结构
    
    Returns:
        复制统计信息
    """
    train_images, val_images, test_images = image_sets
    
    # 创建输出目录
    train_image_dir = os.path.join(output_dir, 'images', 'train')
    train_label_dir = os.path.join(output_dir, 'labels', 'train')
    val_image_dir = os.path.join(output_dir, 'images', 'val')
    val_label_dir = os.path.join(output_dir, 'labels', 'val')
    test_image_dir = os.path.join(output_dir, 'images', 'test')
    test_label_dir = os.path.join(output_dir, 'labels', 'test')
    
    for directory in [train_image_dir, train_label_dir, val_image_dir, val_label_dir, test_image_dir, test_label_dir]:
        ensure_directory(directory)
    
    # 复制图像文件
    stats = {}
    
    label_ext = '.txt' if label_format == 'yolo' else '.xml'
    
    # 训练集
    train_img_copied = copy_files(train_images, image_dir, train_image_dir, preserve_structure)
    train_label_paths = [get_label_path(img_path, label_dir, label_ext) for img_path in train_images]
    train_label_paths = [p for p in train_label_paths if os.path.exists(p)]
    train_label_copied = copy_files(train_label_paths, label_dir, train_label_dir, preserve_structure)
    stats['train'] = {'images': train_img_copied, 'labels': train_label_copied}
    
    # 验证集
    val_img_copied = copy_files(val_images, image_dir, val_image_dir, preserve_structure)
    val_label_paths = [get_label_path(img_path, label_dir, label_ext) for img_path in val_images]
    val_label_paths = [p for p in val_label_paths if os.path.exists(p)]
    val_label_copied = copy_files(val_label_paths, label_dir, val_label_dir, preserve_structure)
    stats['val'] = {'images': val_img_copied, 'labels': val_label_copied}
    
    # 测试集
    test_img_copied = copy_files(test_images, image_dir, test_image_dir, preserve_structure)
    test_label_paths = [get_label_path(img_path, label_dir, label_ext) for img_path in test_images]
    test_label_paths = [p for p in test_label_paths if os.path.exists(p)]
    test_label_copied = copy_files(test_label_paths, label_dir, test_label_dir, preserve_structure)
    stats['test'] = {'images': test_img_copied, 'labels': test_label_copied}
    
    # 记录类别统计信息
    logger.info(f"复制完成:")
    logger.info(f"  训练集 - 图像: {stats['train']['images']}, 标签: {stats['train']['labels']}")
    logger.info(f"  验证集 - 图像: {stats['val']['images']}, 标签: {stats['val']['labels']}")
    logger.info(f"  测试集 - 图像: {stats['test']['images']}, 标签: {stats['test']['labels']}")
    
    return stats


def generate_dataset_yaml(output_dir: str, class_names: Optional[List[str]] = None) -> str:
    """
    生成YOLO格式的数据集配置文件
    
    Args:
        output_dir: 输出目录
        class_names: 类别名称列表
    
    Returns:
        配置文件路径
    """
    yaml_path = os.path.join(output_dir, 'dataset.yaml')
    
    # 如果没有提供类别名称，使用默认值
    if class_names is None:
        class_names = []
    
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write('# YOLOv5/v8 数据集配置文件\n')
        f.write('# 生成时间: ' + str(os.path.getmtime(__file__)) + '\n')
        f.write('\n')
        
        # 训练和验证数据路径
        f.write(f'train: ../images/train\n')
        f.write(f'val: ../images/val\n')
        if os.path.exists(os.path.join(output_dir, 'images', 'test')):
            f.write(f'test: ../images/test\n')
        f.write('\n')
        
        # 类别数量
        f.write(f'nc: {len(class_names)}\n')
        f.write('\n')
        
        # 类别名称
        f.write('names: ' + json.dumps(class_names, ensure_ascii=False) + '\n')
    
    logger.info(f"生成数据集配置文件: {yaml_path}")
    return yaml_path


def split_dataset(
    image_dir: str,
    label_dir: str,
    output_dir: str,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    split_method: str = 'random',
    label_format: str = 'yolo',
    coco_json_path: Optional[str] = None,
    class_mapping_path: Optional[str] = None,
    class_names_path: Optional[str] = None,
    preserve_structure: bool = False,
    seed: Optional[int] = None,
    generate_yaml: bool = True
) -> Dict[str, Any]:
    """
    拆分数据集的主函数
    
    Args:
        image_dir: 图像目录
        label_dir: 标签目录
        output_dir: 输出目录
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        split_method: 拆分方法 ('random' 或 'stratified')
        label_format: 标签格式 ('yolo', 'voc', 'coco')
        coco_json_path: COCO格式的JSON文件路径
        class_mapping_path: 类别映射文件路径
        class_names_path: 类别名称文件路径
        preserve_structure: 是否保留目录结构
        seed: 随机种子
        generate_yaml: 是否生成YOLO数据集配置文件
    
    Returns:
        拆分结果统计信息
    """
    # 确保输入目录存在
    if not os.path.exists(image_dir):
        raise ValueError(f"图像目录不存在: {image_dir}")
    if not os.path.exists(label_dir) and label_format != 'coco':
        raise ValueError(f"标签目录不存在: {label_dir}")
    
    # 确保输出目录存在
    ensure_directory(output_dir)
    
    # 加载类别映射
    class_mapping = None
    if class_mapping_path and os.path.exists(class_mapping_path):
        try:
            with open(class_mapping_path, 'r', encoding='utf-8') as f:
                class_mapping = json.load(f)
            logger.info(f"加载类别映射: {class_mapping_path}")
        except Exception as e:
            logger.error(f"加载类别映射文件失败: {str(e)}")
    
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
    image_paths = load_image_paths(image_dir, recursive=preserve_structure)
    if not image_paths:
        logger.error(f"未找到图像文件: {image_dir}")
        return {}
    
    # 根据拆分方法进行拆分
    if split_method == 'stratified':
        # 加载类别分布
        image_to_classes, global_class_count = load_class_distribution(
            image_paths, label_dir, label_format, coco_json_path, class_mapping
        )
        
        # 显示类别统计
        logger.info("全局类别统计:")
        for class_id, count in sorted(global_class_count.items()):
            logger.info(f"  类别 {class_id}: {count} 个实例")
        
        # 分层拆分
        train_images, val_images, test_images = stratified_split(
            image_paths, image_to_classes, train_ratio, val_ratio, test_ratio, seed
        )
    else:  # random
        # 随机拆分
        train_images, val_images, test_images = random_split(
            image_paths, train_ratio, val_ratio, test_ratio, seed
        )
    
    # 复制文件到输出目录
    copy_stats = copy_dataset_files(
        (train_images, val_images, test_images),
        image_dir, label_dir, output_dir,
        label_format, preserve_structure
    )
    
    # 生成YOLO配置文件
    if generate_yaml:
        generate_dataset_yaml(output_dir, class_names)
    
    # 返回统计信息
    stats = {
        'total_images': len(image_paths),
        'split_method': split_method,
        'train_ratio': train_ratio,
        'val_ratio': val_ratio,
        'test_ratio': test_ratio,
        'seed': seed,
        'train_count': len(train_images),
        'val_count': len(val_images),
        'test_count': len(test_images),
        'copy_stats': copy_stats,
        'output_dir': output_dir
    }
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="数据集拆分工具")
    
    # 基本参数
    parser.add_argument("-i", "--image-dir", required=True, help="图像目录路径")
    parser.add_argument("-l", "--label-dir", required=True, help="标签目录路径")
    parser.add_argument("-o", "--output-dir", required=True, help="输出目录路径")
    
    # 拆分参数
    parser.add_argument("--train-ratio", type=float, default=0.7, help="训练集比例")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="验证集比例")
    parser.add_argument("--test-ratio", type=float, default=0.1, help="测试集比例")
    parser.add_argument("--method", choices=['random', 'stratified'], default='random', help="拆分方法")
    parser.add_argument("--seed", type=int, help="随机种子")
    
    # 格式参数
    parser.add_argument("--label-format", choices=['yolo', 'voc', 'coco'], default='yolo', help="标签格式")
    parser.add_argument("--coco-json", help="COCO格式的JSON标注文件路径")
    parser.add_argument("--class-mapping", help="类别映射文件路径 (JSON格式)")
    parser.add_argument("--class-names", help="类别名称文件路径 (每行一个类别)")
    
    # 其他参数
    parser.add_argument("--preserve-structure", action="store_true", help="保留目录结构")
    parser.add_argument("--no-yaml", action="store_true", help="不生成YOLO数据集配置文件")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    try:
        # 执行拆分
        stats = split_dataset(
            args.image_dir,
            args.label_dir,
            args.output_dir,
            args.train_ratio,
            args.val_ratio,
            args.test_ratio,
            args.method,
            args.label_format,
            args.coco_json,
            args.class_mapping,
            args.class_names,
            args.preserve_structure,
            args.seed,
            not args.no_yaml
        )
        
        if stats:
            # 打印总结
            print("\n" + "=" * 60)
            print("数据集拆分总结")
            print("=" * 60)
            print(f"总图像数: {stats['total_images']}")
            print(f"拆分方法: {stats['split_method']}")
            if stats['seed'] is not None:
                print(f"随机种子: {stats['seed']}")
            print("\n拆分结果:")
            print(f"  训练集: {stats['train_count']} ({stats['train_ratio']*100:.1f}%)")
            print(f"  验证集: {stats['val_count']} ({stats['val_ratio']*100:.1f}%)")
            print(f"  测试集: {stats['test_count']} ({stats['test_ratio']*100:.1f}%)")
            print("\n复制统计:")
            for split_name, split_stats in stats['copy_stats'].items():
                print(f"  {split_name} - 图像: {split_stats['images']}, 标签: {split_stats['labels']}")
            print("\n输出目录:")
            print(f"  {stats['output_dir']}")
            
            if not args.no_yaml:
                yaml_path = os.path.join(args.output_dir, 'dataset.yaml')
                print(f"\nYOLO数据集配置文件:")
                print(f"  {yaml_path}")
    
    except Exception as e:
        logger.error(f"数据集拆分失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()