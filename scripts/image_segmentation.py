#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像分割模块（A3）

功能：
- 支持多种图像分割算法（语义分割、实例分割）
- 支持基于阈值的分割
- 支持基于边缘的分割
- 支持基于区域的分割
- 支持基于深度学习的分割（可集成常见模型）
- 支持自定义分割参数
- 支持分割结果可视化和导出
- 支持批量处理图像
- 支持分割结果后处理（如形态学操作）

作者: AI助手
日期: 2024
"""

import os
import sys
import cv2
import numpy as np
import argparse
import logging
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("image_segmentation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImageSegmentationTool:
    """图像分割工具类"""
    
    def __init__(self):
        self.supported_algorithms = [
            'threshold',      # 阈值分割
            'adaptive_threshold',  # 自适应阈值分割
            'otsu',           # Otsu阈值分割
            'canny',          # Canny边缘检测
            'watershed',      # 分水岭算法
            'kmeans',         # K均值聚类分割
            'grabcut',        # GrabCut分割
            'mean_shift'      # 均值漂移分割
        ]
        self.colormap = self._generate_colormap()
    
    def _generate_colormap(self):
        """生成用于分割结果可视化的颜色映射"""
        # 创建256种不同的颜色
        colormap = np.zeros((256, 3), dtype=np.uint8)
        for i in range(256):
            # 使用HSV颜色空间生成均匀分布的颜色
            hue = i / 256.0
            colormap[i] = np.array(plt.cm.hsv(hue)[:3]) * 255
        return colormap
    
    def segment_image(self, image_path, algorithm='threshold', **kwargs):
        """
        对单张图像进行分割
        
        Args:
            image_path: 图像路径
            algorithm: 分割算法名称
            **kwargs: 算法特定参数
            
        Returns:
            tuple: (原始图像, 分割掩码, 分割结果叠加图)
        """
        if not os.path.isfile(image_path):
            logger.error(f"图像文件不存在: {image_path}")
            return None, None, None
        
        if algorithm not in self.supported_algorithms:
            logger.error(f"不支持的分割算法: {algorithm}")
            return None, None, None
        
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"无法读取图像: {image_path}")
                return None, None, None
            
            # 根据算法选择分割函数
            if algorithm == 'threshold':
                mask = self._threshold_segmentation(image, **kwargs)
            elif algorithm == 'adaptive_threshold':
                mask = self._adaptive_threshold_segmentation(image, **kwargs)
            elif algorithm == 'otsu':
                mask = self._otsu_segmentation(image, **kwargs)
            elif algorithm == 'canny':
                mask = self._canny_edge_detection(image, **kwargs)
            elif algorithm == 'watershed':
                mask = self._watershed_segmentation(image, **kwargs)
            elif algorithm == 'kmeans':
                mask = self._kmeans_segmentation(image, **kwargs)
            elif algorithm == 'grabcut':
                mask = self._grabcut_segmentation(image, **kwargs)
            elif algorithm == 'mean_shift':
                mask = self._mean_shift_segmentation(image, **kwargs)
            
            # 生成分割结果叠加图
            overlay = self._create_overlay(image, mask)
            
            return image, mask, overlay
            
        except Exception as e:
            logger.error(f"图像分割失败 {image_path}: {str(e)}")
            return None, None, None
    
    def batch_segment_images(self, input_dir, output_dir, algorithm='threshold', recursive=True, 
                            num_workers=4, file_patterns=None, **kwargs):
        """
        批量分割图像
        
        Args:
            input_dir: 输入图像目录
            output_dir: 输出结果目录
            algorithm: 分割算法名称
            recursive: 是否递归处理子目录
            num_workers: 并行工作线程数
            file_patterns: 要处理的文件模式列表
            **kwargs: 算法特定参数
            
        Returns:
            dict: {图像路径: 处理结果}
        """
        if not os.path.isdir(input_dir):
            logger.error(f"输入目录不存在: {input_dir}")
            return {}
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 收集要处理的图像文件
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        image_files = []
        
        for root, _, files in os.walk(input_dir):
            for file in files:
                file_ext = Path(file).suffix.lower()
                # 检查文件扩展名
                if file_ext in image_extensions:
                    # 如果指定了文件模式，检查是否匹配
                    if file_patterns:
                        if any(pattern in file for pattern in file_patterns):
                            image_files.append(os.path.join(root, file))
                    else:
                        image_files.append(os.path.join(root, file))
            
            # 是否递归处理子目录
            if not recursive:
                break
        
        total_files = len(image_files)
        logger.info(f"找到 {total_files} 个图像文件需要处理")
        
        # 使用线程池并行处理图像
        results = {}
        processed_files = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # 提交所有任务
            future_to_file = {executor.submit(self.segment_image, image_path, algorithm, **kwargs): image_path 
                             for image_path in image_files}
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                image_path = future_to_file[future]
                try:
                    image, mask, overlay = future.result()
                    if image is not None:
                        # 生成输出文件路径
                        rel_path = os.path.relpath(image_path, input_dir)
                        output_base = os.path.join(output_dir, os.path.splitext(rel_path)[0])
                        
                        # 确保输出子目录存在
                        os.makedirs(os.path.dirname(output_base), exist_ok=True)
                        
                        # 保存结果
                        mask_path = f"{output_base}_mask.png"
                        overlay_path = f"{output_base}_overlay.png"
                        
                        cv2.imwrite(mask_path, mask)
                        cv2.imwrite(overlay_path, overlay)
                        
                        results[image_path] = {
                            'mask_path': mask_path,
                            'overlay_path': overlay_path
                        }
                        
                except Exception as e:
                    logger.error(f"处理图像时出错 {image_path}: {str(e)}")
                
                # 更新进度
                processed_files += 1
                self._show_progress(processed_files, total_files, start_time)
        
        logger.info(f"批量分割完成: 成功 {len(results)}/{total_files}")
        return results
    
    def _threshold_segmentation(self, image, threshold=128, max_value=255, type='binary'):
        """基于阈值的分割"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 选择阈值类型
        if type == 'binary':
            threshold_type = cv2.THRESH_BINARY
        elif type == 'binary_inv':
            threshold_type = cv2.THRESH_BINARY_INV
        elif type == 'trunc':
            threshold_type = cv2.THRESH_TRUNC
        elif type == 'tozero':
            threshold_type = cv2.THRESH_TOZERO
        elif type == 'tozero_inv':
            threshold_type = cv2.THRESH_TOZERO_INV
        else:
            threshold_type = cv2.THRESH_BINARY
        
        # 应用阈值
        _, mask = cv2.threshold(gray, threshold, max_value, threshold_type)
        return mask
    
    def _adaptive_threshold_segmentation(self, image, max_value=255, adaptive_method='gaussian', 
                                       threshold_type='binary', block_size=11, c=2):
        """自适应阈值分割"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 选择自适应方法
        if adaptive_method == 'gaussian':
            method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
        elif adaptive_method == 'mean':
            method = cv2.ADAPTIVE_THRESH_MEAN_C
        else:
            method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
        
        # 选择阈值类型
        if threshold_type == 'binary':
            type_flag = cv2.THRESH_BINARY
        elif threshold_type == 'binary_inv':
            type_flag = cv2.THRESH_BINARY_INV
        else:
            type_flag = cv2.THRESH_BINARY
        
        # 应用自适应阈值
        mask = cv2.adaptiveThreshold(gray, max_value, method, type_flag, block_size, c)
        return mask
    
    def _otsu_segmentation(self, image, max_value=255, type='binary'):
        """Otsu阈值分割"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 选择阈值类型
        if type == 'binary':
            threshold_type = cv2.THRESH_BINARY
        elif type == 'binary_inv':
            threshold_type = cv2.THRESH_BINARY_INV
        else:
            threshold_type = cv2.THRESH_BINARY
        
        # 应用Otsu阈值
        _, mask = cv2.threshold(gray, 0, max_value, threshold_type + cv2.THRESH_OTSU)
        return mask
    
    def _canny_edge_detection(self, image, low_threshold=50, high_threshold=150, aperture_size=3, 
                            l2_gradient=False):
        """Canny边缘检测"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 应用Canny边缘检测
        edges = cv2.Canny(gray, low_threshold, high_threshold, apertureSize=aperture_size, 
                         L2gradient=l2_gradient)
        return edges
    
    def _watershed_segmentation(self, image, mark_mode='auto', markers=None):
        """分水岭算法分割"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 自适应阈值处理
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 噪声去除
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # 确定背景区域
        sure_bg = cv2.dilate(opening, kernel, iterations=3)
        
        # 寻找前景区域
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.7 * dist_transform.max(), 255, 0)
        
        # 找到未知区域
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        # 标记连通区域
        _, markers = cv2.connectedComponents(sure_fg)
        
        # 为所有区域加上1，确保背景不是0而是1
        markers = markers + 1
        
        # 标记未知区域为0
        markers[unknown == 255] = 0
        
        # 应用分水岭算法
        markers = cv2.watershed(image, markers)
        
        # 边界标记为-1，我们将其设为255以便可视化
        markers[markers == -1] = 255
        
        return markers.astype(np.uint8)
    
    def _kmeans_segmentation(self, image, k=2, attempts=10, max_iterations=100):
        """K均值聚类分割"""
        # 将图像数据重塑为二维数组
        Z = image.reshape((-1, 3))
        
        # 转换为float32类型
        Z = np.float32(Z)
        
        # 定义K-means参数
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, max_iterations, 1.0)
        
        # 应用K-means聚类
        _, label, center = cv2.kmeans(Z, k, None, criteria, attempts, cv2.KMEANS_RANDOM_CENTERS)
        
        # 将中心转换为uint8类型
        center = np.uint8(center)
        
        # 应用标签
        res = center[label.flatten()]
        
        # 重塑回原始图像形状
        segmented_image = res.reshape((image.shape))
        
        # 为了返回掩码，我们使用标签
        mask = label.reshape((image.shape[0], image.shape[1]))
        
        return mask.astype(np.uint8)
    
    def _grabcut_segmentation(self, image, rectangle=None, iterations=5, mode='rect'):
        """GrabCut分割算法"""
        # 如果没有提供矩形，使用整个图像
        if rectangle is None:
            h, w = image.shape[:2]
            rectangle = (10, 10, w-20, h-20)
        
        # 创建掩码和临时数组
        mask = np.zeros(image.shape[:2], np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        
        # 应用GrabCut算法
        cv2.grabCut(image, mask, rectangle, bgdModel, fgdModel, iterations, cv2.GC_INIT_WITH_RECT)
        
        # 创建掩码：0和2设为0，1和3设为1
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        # 将掩码扩展为3通道以便与原图相乘
        result = mask2 * 255
        
        return result
    
    def _mean_shift_segmentation(self, image, spatial_radius=10, color_radius=10, max_level=1):
        """均值漂移分割"""
        # 应用均值漂移分割
        shifted = cv2.pyrMeanShiftFiltering(image, spatial_radius, color_radius, maxLevel=max_level)
        
        # 转换为灰度图用于阈值分割
        gray = cv2.cvtColor(shifted, cv2.COLOR_BGR2GRAY)
        
        # 使用Otsu阈值分割获取掩码
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return mask
    
    def _create_overlay(self, image, mask):
        """创建分割结果的叠加图"""
        # 创建颜色映射的掩码
        colored_mask = self.colormap[mask % 256]
        colored_mask = colored_mask.astype(np.uint8)
        
        # 调整掩码大小以匹配原图
        h, w = image.shape[:2]
        if colored_mask.shape[:2] != (h, w):
            colored_mask = cv2.resize(colored_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # 创建叠加图
        overlay = cv2.addWeighted(image, 0.7, colored_mask, 0.3, 0)
        
        return overlay
    
    def post_process_mask(self, mask, operation='none', kernel_size=3, iterations=1):
        """
        对分割掩码进行后处理
        
        Args:
            mask: 分割掩码
            operation: 形态学操作类型 ('none', 'erosion', 'dilation', 'opening', 'closing')
            kernel_size: 形态学操作的核大小
            iterations: 形态学操作的迭代次数
            
        Returns:
            ndarray: 处理后的掩码
        """
        if operation == 'none':
            return mask
        
        # 创建形态学操作的核
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        # 应用形态学操作
        if operation == 'erosion':
            result = cv2.erode(mask, kernel, iterations=iterations)
        elif operation == 'dilation':
            result = cv2.dilate(mask, kernel, iterations=iterations)
        elif operation == 'opening':
            result = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)
        elif operation == 'closing':
            result = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=iterations)
        else:
            logger.warning(f"未知的形态学操作: {operation}")
            result = mask
        
        return result
    
    def save_segmentation_results(self, image_path, image, mask, overlay, output_dir):
        """
        保存分割结果
        
        Args:
            image_path: 原始图像路径
            image: 原始图像
            mask: 分割掩码
            overlay: 叠加图
            output_dir: 输出目录
            
        Returns:
            dict: 包含保存路径的字典
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 保存结果
        mask_path = os.path.join(output_dir, f"{base_name}_mask.png")
        overlay_path = os.path.join(output_dir, f"{base_name}_overlay.png")
        
        cv2.imwrite(mask_path, mask)
        cv2.imwrite(overlay_path, overlay)
        
        logger.info(f"分割结果已保存: {mask_path}, {overlay_path}")
        
        return {
            'mask_path': mask_path,
            'overlay_path': overlay_path
        }
    
    def _show_progress(self, processed, total, start_time):
        """
        显示进度条
        
        Args:
            processed: 已处理数量
            total: 总数量
            start_time: 开始时间
        """
        if total == 0:
            return
        
        progress = min(100, (processed / total) * 100)
        elapsed_time = time.time() - start_time
        
        # 估计剩余时间
        if progress > 0:
            estimated_total_time = elapsed_time * 100 / progress
            remaining_time = estimated_total_time - elapsed_time
        else:
            remaining_time = 0
        
        # 格式化进度条
        bar_length = 30
        filled_length = int(bar_length * processed // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # 显示进度
        sys.stdout.write(f'\r进度: |{bar}| {progress:.1f}% [{processed}/{total}] ')
        sys.stdout.write(f'已用时间: {elapsed_time:.1f}s 剩余时间: {remaining_time:.1f}s')
        sys.stdout.flush()
        
        # 完成时换行
        if processed >= total:
            sys.stdout.write('\n')
    
    def analyze_segmentation(self, mask):
        """
        分析分割结果
        
        Args:
            mask: 分割掩码
            
        Returns:
            dict: 包含分割统计信息的字典
        """
        # 计算不同区域的面积
        unique_values, counts = np.unique(mask, return_counts=True)
        
        analysis = {
            'total_regions': len(unique_values),
            'region_areas': {int(val): int(count) for val, count in zip(unique_values, counts)}
        }
        
        # 计算最大区域和最小区域
        if len(counts) > 0:
            analysis['largest_region_value'] = int(unique_values[np.argmax(counts)])
            analysis['largest_region_area'] = int(np.max(counts))
            analysis['smallest_region_value'] = int(unique_values[np.argmin(counts)])
            analysis['smallest_region_area'] = int(np.min(counts))
        
        return analysis


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='图像分割工具')
    
    # 输入输出参数
    parser.add_argument('-i', '--input', type=str, required=True, help='输入图像文件或目录路径')
    parser.add_argument('-o', '--output', type=str, required=True, help='输出目录路径')
    
    # 分割算法参数
    parser.add_argument('-a', '--algorithm', type=str, default='threshold', 
                      help=f'分割算法 ({" ".join(ImageSegmentationTool().supported_algorithms)})')
    
    # 批量处理参数
    parser.add_argument('-r', '--recursive', action='store_true', default=False, 
                      help='递归处理子目录')
    parser.add_argument('-w', '--workers', type=int, default=4, help='并行工作线程数')
    parser.add_argument('--patterns', type=str, nargs='+', help='文件匹配模式')
    
    # 阈值分割参数
    parser.add_argument('--threshold', type=int, default=128, help='阈值分割的阈值')
    parser.add_argument('--max-value', type=int, default=255, help='阈值分割的最大值')
    parser.add_argument('--threshold-type', type=str, default='binary', 
                      choices=['binary', 'binary_inv', 'trunc', 'tozero', 'tozero_inv'], 
                      help='阈值分割类型')
    
    # 自适应阈值参数
    parser.add_argument('--adaptive-method', type=str, default='gaussian', 
                      choices=['gaussian', 'mean'], help='自适应阈值方法')
    parser.add_argument('--block-size', type=int, default=11, help='自适应阈值的块大小')
    parser.add_argument('--c', type=int, default=2, help='自适应阈值的常数')
    
    # Canny边缘检测参数
    parser.add_argument('--low-threshold', type=int, default=50, help='Canny低阈值')
    parser.add_argument('--high-threshold', type=int, default=150, help='Canny高阈值')
    parser.add_argument('--aperture-size', type=int, default=3, help='Sobel算子的孔径大小')
    parser.add_argument('--l2-gradient', action='store_true', default=False, 
                      help='是否使用L2范数计算梯度')
    
    # K-means分割参数
    parser.add_argument('--k', type=int, default=2, help='K-means聚类的簇数')
    parser.add_argument('--attempts', type=int, default=10, help='K-means尝试次数')
    parser.add_argument('--max-iterations', type=int, default=100, help='K-means最大迭代次数')
    
    # GrabCut分割参数
    parser.add_argument('--rect', type=int, nargs=4, help='GrabCut矩形区域 (x, y, width, height)')
    parser.add_argument('--grabcut-iterations', type=int, default=5, help='GrabCut迭代次数')
    
    # 均值漂移参数
    parser.add_argument('--spatial-radius', type=int, default=10, help='空间窗口半径')
    parser.add_argument('--color-radius', type=int, default=10, help='颜色窗口半径')
    parser.add_argument('--max-level', type=int, default=1, help='金字塔最大层级')
    
    # 后处理参数
    parser.add_argument('--post-process', type=str, default='none', 
                      choices=['none', 'erosion', 'dilation', 'opening', 'closing'], 
                      help='形态学后处理操作')
    parser.add_argument('--kernel-size', type=int, default=3, help='形态学操作的核大小')
    parser.add_argument('--post-iterations', type=int, default=1, help='后处理迭代次数')
    
    # 分析参数
    parser.add_argument('--analyze', action='store_true', default=False, help='分析分割结果')
    parser.add_argument('--save-analysis', type=str, help='保存分析结果的文件路径')
    
    return parser.parse_args()


def get_algorithm_kwargs(args):
    """根据命令行参数生成算法特定的参数字典"""
    kwargs = {}
    
    # 阈值分割参数
    if args.algorithm in ['threshold']:
        kwargs['threshold'] = args.threshold
        kwargs['max_value'] = args.max_value
        kwargs['type'] = args.threshold_type
    
    # 自适应阈值参数
    elif args.algorithm in ['adaptive_threshold']:
        kwargs['max_value'] = args.max_value
        kwargs['adaptive_method'] = args.adaptive_method
        kwargs['threshold_type'] = args.threshold_type
        kwargs['block_size'] = args.block_size
        kwargs['c'] = args.c
    
    # Otsu阈值参数
    elif args.algorithm in ['otsu']:
        kwargs['max_value'] = args.max_value
        kwargs['type'] = args.threshold_type
    
    # Canny边缘检测参数
    elif args.algorithm in ['canny']:
        kwargs['low_threshold'] = args.low_threshold
        kwargs['high_threshold'] = args.high_threshold
        kwargs['aperture_size'] = args.aperture_size
        kwargs['l2_gradient'] = args.l2_gradient
    
    # K-means分割参数
    elif args.algorithm in ['kmeans']:
        kwargs['k'] = args.k
        kwargs['attempts'] = args.attempts
        kwargs['max_iterations'] = args.max_iterations
    
    # GrabCut分割参数
    elif args.algorithm in ['grabcut']:
        kwargs['rectangle'] = args.rect
        kwargs['iterations'] = args.grabcut_iterations
    
    # 均值漂移参数
    elif args.algorithm in ['mean_shift']:
        kwargs['spatial_radius'] = args.spatial_radius
        kwargs['color_radius'] = args.color_radius
        kwargs['max_level'] = args.max_level
    
    return kwargs


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 初始化分割工具
    tool = ImageSegmentationTool()
    
    # 获取算法特定参数
    algorithm_kwargs = get_algorithm_kwargs(args)
    
    try:
        # 确保输出目录存在
        os.makedirs(args.output, exist_ok=True)
        
        # 处理单文件或目录
        if os.path.isfile(args.input):
            # 处理单个图像
            image, mask, overlay = tool.segment_image(args.input, args.algorithm, **algorithm_kwargs)
            
            if image is not None:
                # 后处理
                if args.post_process != 'none':
                    mask = tool.post_process_mask(mask, args.post_process, args.kernel_size, args.post_iterations)
                    # 重新生成叠加图
                    overlay = tool._create_overlay(image, mask)
                
                # 保存结果
                tool.save_segmentation_results(args.input, image, mask, overlay, args.output)
                
                # 分析分割结果
                if args.analyze:
                    analysis = tool.analyze_segmentation(mask)
                    logger.info(f"分割分析结果: {analysis}")
                    
                    # 保存分析结果
                    if args.save_analysis:
                        with open(args.save_analysis, 'w', encoding='utf-8') as f:
                            json.dump(analysis, f, ensure_ascii=False, indent=2)
                        logger.info(f"分析结果已保存到: {args.save_analysis}")
                
                logger.info("图像分割完成")
                return 0
            else:
                return 1
        
        elif os.path.isdir(args.input):
            # 批量处理图像
            results = tool.batch_segment_images(
                args.input,
                args.output,
                args.algorithm,
                args.recursive,
                args.workers,
                args.patterns,
                **algorithm_kwargs
            )
            
            # 后处理（如果需要）
            if args.post_process != 'none' and results:
                logger.info(f"对 {len(results)} 个分割结果进行后处理...")
                
                # 读取每个结果并进行后处理
                for image_path, paths in results.items():
                    if 'mask_path' in paths:
                        mask = cv2.imread(paths['mask_path'], cv2.IMREAD_GRAYSCALE)
                        if mask is not None:
                            # 应用后处理
                            processed_mask = tool.post_process_mask(
                                mask, 
                                args.post_process, 
                                args.kernel_size, 
                                args.post_iterations
                            )
                            
                            # 读取原始图像
                            image = cv2.imread(image_path)
                            if image is not None:
                                # 重新生成叠加图
                                overlay = tool._create_overlay(image, processed_mask)
                                
                                # 保存处理后的结果
                                cv2.imwrite(paths['mask_path'], processed_mask)
                                cv2.imwrite(paths['overlay_path'], overlay)
            
            logger.info(f"批量分割完成: 成功处理 {len(results)} 个图像")
            return 0 if results else 1
        
        else:
            logger.error(f"输入路径不存在: {args.input}")
            return 1
        
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        return 1
    except Exception as e:
        logger.error(f"发生未预期的错误: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
