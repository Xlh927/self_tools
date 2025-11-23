#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集采样模块（B4）

功能：
- 随机采样（有放回/无放回）
- 分层采样（按类别、按图像尺寸等）
- 基于图像特征的智能采样
- 支持各种采样策略（均匀、按比例、逆频率等）
- 采样结果可视化
- 支持保存采样结果和索引
- 支持多种数据格式（图像、标注等）
- 支持单文件和批量文件夹处理

本模块用于从大规模数据集中高效地采样出代表性子集，适用于模型训练、验证和测试。
"""

import os
import sys
import random
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

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatasetSampler:
    """
    数据集采样器类
    """
    
    def __init__(self, output_dir=None, random_seed=42):
        """
        初始化采样器
        
        Args:
            output_dir: 输出目录
            random_seed: 随机种子，用于可重复采样
        """
        self.output_dir = output_dir or "sampling_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置随机种子
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        # 支持的图像格式
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'}
        # 支持的标注格式
        self.annotation_extensions = {'.txt', '.xml', '.json', '.csv'}
    
    def collect_files(self, input_path, recursive=False):
        """
        收集文件列表
        
        Args:
            input_path: 输入文件或目录路径
            recursive: 是否递归搜索子目录
        
        Returns:
            文件路径列表
        """
        files = []
        
        if os.path.isfile(input_path):
            files.append(input_path)
        elif os.path.isdir(input_path):
            for root, dirs, filenames in os.walk(input_path):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
                if not recursive:
                    break
        
        logger.info(f"总共收集到 {len(files)} 个文件")
        return files
    
    def split_files_by_type(self, file_list):
        """
        按文件类型分割文件列表
        
        Args:
            file_list: 文件路径列表
        
        Returns:
            (图像文件列表, 标注文件列表, 其他文件列表)
        """
        image_files = []
        annotation_files = []
        other_files = []
        
        for file_path in file_list:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in self.image_extensions:
                image_files.append(file_path)
            elif ext in self.annotation_extensions:
                annotation_files.append(file_path)
            else:
                other_files.append(file_path)
        
        logger.info(f"图像文件: {len(image_files)}, 标注文件: {len(annotation_files)}, 其他文件: {len(other_files)}")
        return image_files, annotation_files, other_files
    
    def random_sampling(self, file_list, sample_size, with_replacement=False):
        """
        随机采样
        
        Args:
            file_list: 文件路径列表
            sample_size: 采样数量
            with_replacement: 是否有放回采样
        
        Returns:
            采样后的文件路径列表
        """
        if sample_size > len(file_list) and not with_replacement:
            logger.warning(f"采样数量 {sample_size} 超过文件总数 {len(file_list)}，将返回全部文件")
            return file_list.copy()
        
        if with_replacement:
            sampled = random.choices(file_list, k=sample_size)
        else:
            sampled = random.sample(file_list, k=sample_size)
        
        logger.info(f"随机采样完成: 从 {len(file_list)} 个文件中采样 {len(sampled)} 个文件")
        return sampled
    
    def stratified_sampling_by_class(self, image_files, label_dir, sample_size, label_format='yolo', 
                                     coco_json_path=None, class_names=None, strategy='proportional'):
        """
        按类别进行分层采样
        
        Args:
            image_files: 图像文件列表
            label_dir: 标签目录
            sample_size: 采样数量
            label_format: 标签格式 ('yolo', 'voc', 'coco')
            coco_json_path: COCO格式的JSON文件路径
            class_names: 类别名称列表
            strategy: 采样策略 ('proportional': 按比例, 'equal': 等比例, 'inverse': 逆频率)
        
        Returns:
            采样后的图像文件路径列表
        """
        # 按类别分组图像
        class_to_images = self._group_images_by_class(image_files, label_dir, label_format, 
                                                     coco_json_path, class_names)
        
        # 计算各类别的采样数量
        if strategy == 'proportional':
            # 按比例采样
            total_images = sum(len(images) for images in class_to_images.values())
            class_sample_sizes = {cls: int(sample_size * len(images) / total_images) 
                                 for cls, images in class_to_images.items()}
        elif strategy == 'equal':
            # 等比例采样
            num_classes = len(class_to_images)
            class_sample_sizes = {cls: max(1, sample_size // num_classes) 
                                 for cls in class_to_images}
        elif strategy == 'inverse':
            # 逆频率采样
            total_images = sum(len(images) for images in class_to_images.values())
            class_frequencies = {cls: len(images) / total_images 
                               for cls, images in class_to_images.items()}
            # 计算逆频率权重
            inverse_weights = {cls: 1.0 / max(freq, 0.001) for cls, freq in class_frequencies.items()}
            total_weight = sum(inverse_weights.values())
            class_sample_sizes = {cls: int(sample_size * inverse_weights[cls] / total_weight) 
                                 for cls in class_to_images}
        else:
            raise ValueError(f"不支持的采样策略: {strategy}")
        
        # 确保采样数量总和接近目标
        total_assigned = sum(class_sample_sizes.values())
        if total_assigned < sample_size:
            # 分配剩余样本
            remaining = sample_size - total_assigned
            for _ in range(remaining):
                # 随机选择一个类别添加一个样本
                cls = random.choice(list(class_to_images.keys()))
                class_sample_sizes[cls] += 1
        
        # 执行分层采样
        sampled_images = []
        for cls, images in class_to_images.items():
            sample_count = min(class_sample_sizes.get(cls, 0), len(images))
            if sample_count > 0:
                sampled = random.sample(images, sample_count)
                sampled_images.extend(sampled)
                logger.info(f"类别 {cls}: 采样 {sample_count}/{len(images)} 个图像")
        
        # 打乱顺序
        random.shuffle(sampled_images)
        logger.info(f"分层采样完成: 从 {len(image_files)} 个图像中采样 {len(sampled_images)} 个图像")
        return sampled_images
    
    def feature_based_sampling(self, image_files, sample_size, feature_type='diversity', 
                              n_clusters=100):
        """
        基于图像特征的采样
        
        Args:
            image_files: 图像文件列表
            sample_size: 采样数量
            feature_type: 特征类型 ('diversity': 多样性采样, 'coverage': 覆盖采样)
            n_clusters: 聚类数量（用于多样性采样）
        
        Returns:
            采样后的图像文件路径列表
        """
        if sample_size >= len(image_files):
            logger.warning(f"采样数量 {sample_size} 大于等于文件总数 {len(image_files)}，将返回全部文件")
            return image_files.copy()
        
        # 提取图像特征
        logger.info(f"提取图像特征: {len(image_files)} 个图像")
        features = []
        valid_files = []
        
        for img_path in tqdm(image_files):
            try:
                # 使用简单的直方图特征
                feature = self._extract_image_feature(img_path)
                features.append(feature)
                valid_files.append(img_path)
            except Exception as e:
                logger.error(f"提取特征失败 {img_path}: {str(e)}")
        
        if not features:
            logger.error("无法提取图像特征，将使用随机采样")
            return self.random_sampling(image_files, sample_size)
        
        # 转换为numpy数组
        features_array = np.array(features)
        
        # 特征标准化
        features_array = self._normalize_features(features_array)
        
        if feature_type == 'diversity':
            # 使用K-means聚类进行多样性采样
            sampled_indices = self._diversity_sampling(features_array, sample_size, n_clusters)
        elif feature_type == 'coverage':
            # 使用最远点优先策略进行覆盖采样
            sampled_indices = self._coverage_sampling(features_array, sample_size)
        else:
            raise ValueError(f"不支持的特征类型: {feature_type}")
        
        # 获取采样的图像文件
        sampled_images = [valid_files[i] for i in sampled_indices]
        logger.info(f"特征采样完成: 从 {len(image_files)} 个图像中采样 {len(sampled_images)} 个图像")
        return sampled_images
    
    def _group_images_by_class(self, image_files, label_dir, label_format, coco_json_path, class_names):
        """
        按类别分组图像
        """
        class_to_images = defaultdict(list)
        
        if label_format == 'coco' and coco_json_path:
            # 处理COCO格式
            with open(coco_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 创建图像ID到文件名的映射
            image_id_to_file = {}
            for img_path in image_files:
                img_name = os.path.basename(img_path)
                image_id_to_file[img_name] = img_path
            
            # 创建图像ID到类别的映射
            image_id_to_classes = defaultdict(set)
            for ann in data.get('annotations', []):
                image_id = ann.get('image_id')
                category_id = ann.get('category_id')
                image_id_to_classes[image_id].add(category_id)
            
            # 按类别分组
            for img_info in data.get('images', []):
                img_name = os.path.basename(img_info.get('file_name', ''))
                img_path = image_id_to_file.get(img_name)
                if img_path:
                    img_id = img_info.get('id')
                    for class_id in image_id_to_classes[img_id]:
                        class_to_images[class_id].append(img_path)
        else:
            # 处理YOLO或VOC格式
            label_ext = '.txt' if label_format == 'yolo' else '.xml'
            
            for img_path in image_files:
                # 获取对应的标签文件
                img_name = os.path.splitext(os.path.basename(img_path))[0]
                label_path = os.path.join(label_dir, img_name + label_ext)
                
                if os.path.exists(label_path):
                    if label_format == 'yolo':
                        # 读取YOLO格式标签
                        try:
                            with open(label_path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    parts = line.strip().split()
                                    if parts:
                                        class_id = int(float(parts[0]))
                                        class_to_images[class_id].append(img_path)
                        except Exception as e:
                            logger.error(f"读取标签文件失败 {label_path}: {str(e)}")
                    else:  # voc
                        # 读取VOC格式标签
                        try:
                            tree = ET.parse(label_path)
                            root = tree.getroot()
                            for obj in root.findall('object'):
                                name_elem = obj.find('name')
                                if name_elem is not None and name_elem.text:
                                    class_name = name_elem.text.strip()
                                    class_to_images[class_name].append(img_path)
                        except Exception as e:
                            logger.error(f"读取标签文件失败 {label_path}: {str(e)}")
        
        return class_to_images
    
    def _extract_image_feature(self, image_path):
        """
        提取图像特征
        """
        # 使用OpenCV读取图像
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        # 调整大小以统一尺寸
        img_resized = cv2.resize(img, (128, 128))
        
        # 计算HSV颜色直方图
        hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
        
        # 计算各通道的直方图
        hist_h = cv2.calcHist([hsv], [0], None, [8], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [8], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [8], [0, 256])
        
        # 归一化直方图
        hist_h = cv2.normalize(hist_h, hist_h).flatten()
        hist_s = cv2.normalize(hist_s, hist_s).flatten()
        hist_v = cv2.normalize(hist_v, hist_v).flatten()
        
        # 合并特征
        feature = np.concatenate([hist_h, hist_s, hist_v])
        return feature.tolist()
    
    def _normalize_features(self, features):
        """
        标准化特征
        """
        # 计算均值和标准差
        mean = np.mean(features, axis=0)
        std = np.std(features, axis=0)
        
        # 避免除零
        std[std == 0] = 1.0
        
        # 标准化
        normalized = (features - mean) / std
        return normalized
    
    def _diversity_sampling(self, features, sample_size, n_clusters=100):
        """
        多样性采样
        """
        from sklearn.cluster import KMeans
        
        # 确保聚类数量不超过特征数量
        n_clusters = min(n_clusters, len(features) - 1, sample_size * 2)
        
        # K-means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features)
        
        # 按聚类中心距离选择样本
        sampled_indices = []
        cluster_indices = defaultdict(list)
        
        # 按聚类分组索引
        for i, label in enumerate(labels):
            cluster_indices[label].append(i)
        
        # 计算每个聚类需要的样本数量
        samples_per_cluster = max(1, sample_size // len(cluster_indices))
        
        # 从每个聚类中选择样本
        for cluster_id, indices in cluster_indices.items():
            # 计算每个样本到聚类中心的距离
            center = kmeans.cluster_centers_[cluster_id]
            distances = np.linalg.norm(features[indices] - center, axis=1)
            
            # 选择最近的样本（更能代表聚类）
            sorted_indices = sorted(range(len(indices)), key=lambda i: distances[i])
            selected = sorted_indices[:min(samples_per_cluster, len(indices))]
            sampled_indices.extend([indices[i] for i in selected])
        
        # 确保达到目标样本数量
        if len(sampled_indices) < sample_size:
            # 随机选择剩余样本
            all_indices = set(range(len(features)))
            remaining = list(all_indices - set(sampled_indices))
            additional = random.sample(remaining, min(sample_size - len(sampled_indices), len(remaining)))
            sampled_indices.extend(additional)
        elif len(sampled_indices) > sample_size:
            # 随机减少到目标数量
            sampled_indices = random.sample(sampled_indices, sample_size)
        
        return sampled_indices
    
    def _coverage_sampling(self, features, sample_size):
        """
        覆盖采样（最远点优先）
        """
        # 初始化：随机选择第一个点
        sampled_indices = [random.randint(0, len(features) - 1)]
        
        # 逐个添加最远的点
        while len(sampled_indices) < sample_size:
            max_distance = -1
            farthest_index = 0
            
            # 对每个未选中的点，计算到最近已选点的距离
            for i in range(len(features)):
                if i not in sampled_indices:
                    min_dist = float('inf')
                    for j in sampled_indices:
                        dist = np.linalg.norm(features[i] - features[j])
                        if dist < min_dist:
                            min_dist = dist
                    
                    # 更新最远点
                    if min_dist > max_distance:
                        max_distance = min_dist
                        farthest_index = i
            
            sampled_indices.append(farthest_index)
        
        return sampled_indices
    
    def copy_sampled_files(self, sampled_files, output_dir):
        """
        复制采样的文件到输出目录
        
        Args:
            sampled_files: 采样的文件路径列表
            output_dir: 输出目录
        
        Returns:
            复制后的文件路径列表
        """
        copied_files = []
        
        for file_path in tqdm(sampled_files, desc="复制文件"):
            try:
                # 保持相对路径结构
                rel_path = os.path.basename(file_path)
                output_path = os.path.join(output_dir, rel_path)
                
                # 复制文件
                import shutil
                shutil.copy2(file_path, output_path)
                copied_files.append(output_path)
            except Exception as e:
                logger.error(f"复制文件失败 {file_path}: {str(e)}")
        
        logger.info(f"文件复制完成: {len(copied_files)}/{len(sampled_files)} 个文件")
        return copied_files
    
    def save_sampling_results(self, sampled_files, method_name):
        """
        保存采样结果
        
        Args:
            sampled_files: 采样的文件路径列表
            method_name: 采样方法名称
        """
        # 保存索引文件
        index_path = os.path.join(self.output_dir, f"sampled_indices_{method_name}.json")
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(sampled_files, f, ensure_ascii=False, indent=2)
        
        logger.info(f"采样结果已保存: {index_path}")
        return index_path
    
    def visualize_sampling(self, original_files, sampled_files, method_name):
        """
        可视化采样结果
        
        Args:
            original_files: 原始文件列表
            sampled_files: 采样的文件列表
            method_name: 采样方法名称
        """
        # 仅可视化图像文件
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        original_images = [f for f in original_files if os.path.splitext(f)[1].lower() in image_extensions]
        sampled_images = [f for f in sampled_files if os.path.splitext(f)[1].lower() in image_extensions]
        
        if len(sampled_images) < 4:
            logger.warning("采样的图像数量过少，无法生成可视化")
            return None
        
        # 选择4张随机采样的图像
        selected_images = random.sample(sampled_images, min(4, len(sampled_images)))
        
        # 创建可视化
        plt.figure(figsize=(12, 10))
        
        for i, img_path in enumerate(selected_images):
            plt.subplot(2, 2, i + 1)
            try:
                img = cv2.imread(img_path)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    plt.imshow(img)
                    plt.title(f"Sample {i+1}: {os.path.basename(img_path)}")
                else:
                    plt.title(f"Sample {i+1}: 无法读取")
            except Exception as e:
                plt.title(f"Sample {i+1}: 错误")
            plt.axis('off')
        
        plt.suptitle(f"采样结果可视化 - {method_name} (采样率: {len(sampled_images)}/{len(original_images)})")
        plt.tight_layout()
        
        # 保存可视化结果
        viz_path = os.path.join(self.output_dir, f"sampling_visualization_{method_name}.png")
        plt.savefig(viz_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"可视化结果已保存: {viz_path}")
        return viz_path


def ensure_directory(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"创建目录: {directory}")


def sample_dataset(
    input_path: str,
    output_dir: str,
    sample_size: int,
    method: str = 'random',
    recursive: bool = False,
    label_dir: Optional[str] = None,
    label_format: str = 'yolo',
    coco_json_path: Optional[str] = None,
    class_names_path: Optional[str] = None,
    strategy: str = 'proportional',
    with_replacement: bool = False,
    copy_files: bool = True,
    visualize: bool = True,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    采样数据集的主函数
    
    Args:
        input_path: 输入文件或目录路径
        output_dir: 输出目录
        sample_size: 采样数量
        method: 采样方法 ('random': 随机, 'stratified': 分层, 'feature': 基于特征)
        recursive: 是否递归处理子目录
        label_dir: 标签目录（分层采样需要）
        label_format: 标签格式 ('yolo', 'voc', 'coco')
        coco_json_path: COCO格式的JSON文件路径
        class_names_path: 类别名称文件路径
        strategy: 分层采样策略 ('proportional', 'equal', 'inverse')
        with_replacement: 是否有放回采样
        copy_files: 是否复制文件
        visualize: 是否可视化结果
        random_seed: 随机种子
    
    Returns:
        采样结果信息
    """
    # 确保输入路径存在
    if not os.path.exists(input_path):
        raise ValueError(f"输入路径不存在: {input_path}")
    
    # 确保输出目录存在
    ensure_directory(output_dir)
    
    # 加载类别名称
    class_names = None
    if class_names_path and os.path.exists(class_names_path):
        try:
            with open(class_names_path, 'r', encoding='utf-8') as f:
                class_names = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"加载类别名称文件失败: {str(e)}")
    
    # 初始化采样器
    sampler = DatasetSampler(output_dir=output_dir, random_seed=random_seed)
    
    # 收集文件
    logger.info(f"收集文件: {input_path}")
    all_files = sampler.collect_files(input_path, recursive=recursive)
    
    if not all_files:
        logger.error(f"未找到文件: {input_path}")
        return {}
    
    # 分割文件类型
    image_files, annotation_files, other_files = sampler.split_files_by_type(all_files)
    
    # 执行采样
    sampled_files = []
    
    if method == 'random':
        # 随机采样
        logger.info(f"执行随机采样: {sample_size} 个文件")
        sampled_files = sampler.random_sampling(all_files, sample_size, with_replacement)
    
    elif method == 'stratified':
        # 分层采样
        if not label_dir:
            raise ValueError("分层采样需要指定标签目录 --label-dir")
        
        logger.info(f"执行分层采样: {sample_size} 个图像，策略: {strategy}")
        sampled_images = sampler.stratified_sampling_by_class(
            image_files, label_dir, sample_size, label_format, coco_json_path, class_names, strategy
        )
        
        # 对于分层采样，我们需要找到对应的标注文件
        sampled_files = sampled_images.copy()
        
        # 查找对应的标注文件
        for img_path in sampled_images:
            img_name = os.path.splitext(os.path.basename(img_path))[0]
            # 尝试找到匹配的标注文件
            for ext in ['.txt', '.xml', '.json']:
                possible_anno = os.path.join(os.path.dirname(img_path), img_name + ext)
                if possible_anno in annotation_files:
                    sampled_files.append(possible_anno)
                # 也在标签目录中查找
                if label_dir:
                    possible_anno = os.path.join(label_dir, img_name + ext)
                    if possible_anno in annotation_files:
                        sampled_files.append(possible_anno)
    
    elif method == 'feature':
        # 基于特征的采样
        logger.info(f"执行基于特征的采样: {sample_size} 个图像")
        sampled_images = sampler.feature_based_sampling(image_files, sample_size)
        sampled_files = sampled_images.copy()
    
    else:
        raise ValueError(f"不支持的采样方法: {method}")
    
    # 确保采样文件唯一
    sampled_files = list(set(sampled_files))
    logger.info(f"最终采样数量: {len(sampled_files)} 个文件")
    
    # 保存采样结果
    index_path = sampler.save_sampling_results(sampled_files, method)
    
    # 复制文件
    copied_files = []
    if copy_files:
        copied_files = sampler.copy_sampled_files(sampled_files, output_dir)
    
    # 可视化结果
    viz_path = None
    if visualize and image_files:
        viz_path = sampler.visualize_sampling(image_files, sampled_files, method)
    
    # 生成统计信息
    stats = {
        'input_path': input_path,
        'output_dir': output_dir,
        'sample_method': method,
        'sample_size_requested': sample_size,
        'sample_size_actual': len(sampled_files),
        'total_files': len(all_files),
        'total_images': len(image_files),
        'total_annotations': len(annotation_files),
        'sampled_images': sum(1 for f in sampled_files if os.path.splitext(f)[1].lower() in sampler.image_extensions),
        'sampled_annotations': sum(1 for f in sampled_files if os.path.splitext(f)[1].lower() in sampler.annotation_extensions),
        'sampling_ratio': len(sampled_files) / max(1, len(all_files)),
        'index_path': index_path,
        'visualization_path': viz_path
    }
    
    # 保存统计信息
    stats_path = os.path.join(output_dir, 'sampling_statistics.json')
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    logger.info(f"采样统计已保存: {stats_path}")
    
    return stats


def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='数据集采样工具')
    
    parser.add_argument('-i', '--input', required=True, help='输入文件或目录路径')
    parser.add_argument('-o', '--output', required=True, help='输出目录')
    parser.add_argument('-n', '--sample-size', type=int, required=True, help='采样数量')
    parser.add_argument('-m', '--method', type=str, choices=['random', 'stratified', 'feature'], 
                        default='random', help='采样方法')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    parser.add_argument('-l', '--label-dir', help='标签目录（分层采样需要）')
    parser.add_argument('--label-format', type=str, choices=['yolo', 'voc', 'coco'], 
                        default='yolo', help='标签格式')
    parser.add_argument('--coco-json', help='COCO格式的JSON标注文件路径')
    parser.add_argument('--class-names', help='类别名称文件路径 (每行一个类别)')
    parser.add_argument('--strategy', type=str, choices=['proportional', 'equal', 'inverse'], 
                        default='proportional', help='分层采样策略')
    parser.add_argument('--with-replacement', action='store_true', help='有放回采样')
    parser.add_argument('--no-copy', action='store_true', help='不复制文件，只生成索引')
    parser.add_argument('--no-visualize', action='store_true', help='不生成可视化结果')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')
    parser.add_argument('--log-level', type=str, choices=['debug', 'info', 'warning', 'error'], 
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
        # 执行采样
        results = sample_dataset(
            input_path=args.input,
            output_dir=args.output,
            sample_size=args.sample_size,
            method=args.method,
            recursive=args.recursive,
            label_dir=args.label_dir,
            label_format=args.label_format,
            coco_json_path=args.coco_json,
            class_names_path=args.class_names,
            strategy=args.strategy,
            with_replacement=args.with_replacement,
            copy_files=not args.no_copy,
            visualize=not args.no_visualize,
            random_seed=args.seed
        )
        
        if results:
            # 输出简短统计信息
            print("\n=== 数据集采样完成 ===")
            print(f"采样方法: {results.get('sample_method', 'N/A')}")
            print(f"请求采样数: {results.get('sample_size_requested', 0)}")
            print(f"实际采样数: {results.get('sample_size_actual', 0)}")
            print(f"采样率: {results.get('sampling_ratio', 0):.2%}")
            print(f"采样图像: {results.get('sampled_images', 0)}")
            print(f"采样标注: {results.get('sampled_annotations', 0)}")
            print(f"输出目录: {results.get('output_dir', 'N/A')}")
            if results.get('visualization_path'):
                print(f"可视化结果: {results['visualization_path']}")
            print(f"统计信息: {os.path.join(results['output_dir'], 'sampling_statistics.json')}")
            print("=======================")
            
    except KeyboardInterrupt:
        print("\n用户中断采样")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {str(e)}")
        logger.error(f"运行失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()