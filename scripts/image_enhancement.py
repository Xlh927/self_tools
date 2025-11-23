#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像增强模块（A2）

功能：
- 暗光增强（Gamma + CLAHE）
- 去雾、HDR增强
- 自动质量优化（亮度/模糊度检测）

支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
from tqdm import tqdm
import math
from PIL import Image, ImageFilter

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

def gamma_correction(image, gamma=1.0):
    """Gamma校正"""
    # 构建查找表
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    
    # 应用查找表
    return cv2.LUT(image, table)

def clahe_enhancement(image, clip_limit=2.0, grid_size=(8, 8)):
    """应用CLAHE增强"""
    # 转换为LAB色彩空间
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # 对L通道应用CLAHE
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    cl = clahe.apply(l)
    
    # 合并通道并转回BGR
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def low_light_enhancement(image, gamma=1.5, clahe_clip_limit=2.0, clahe_grid_size=(8, 8)):
    """暗光增强（Gamma + CLAHE）"""
    # 先应用Gamma校正提升亮度
    gamma_enhanced = gamma_correction(image, gamma)
    
    # 再应用CLAHE增强对比度
    return clahe_enhancement(gamma_enhanced, clahe_clip_limit, clahe_grid_size)

def dehaze(image, omega=0.95, t_min=0.1):
    """单图像去雾算法"""
    # 转换为浮点型
    img = image.astype(np.float64) / 255.0
    
    # 计算暗通道
    min_img = np.min(img, axis=2)
    
    # 估计大气光 A
    # 取暗通道中最亮的0.1%像素的平均值
    flat_min_img = min_img.flatten()
    num_pixels = int(flat_min_img.size * 0.001)
    if num_pixels < 1:  # 防止除零
        num_pixels = 1
    indices = np.argsort(flat_min_img)[-num_pixels:]
    brightest_pixels = flat_min_img[indices]
    A = np.mean(brightest_pixels)
    
    # 估计透射率 t
    t = 1 - omega * min_img
    
    # 限制t的最小值
    t = np.maximum(t, t_min)
    
    # 恢复无雾图像
    result = np.zeros_like(img)
    for i in range(3):
        result[:, :, i] = (img[:, :, i] - A) / t + A
    
    # 裁剪到有效范围
    result = np.clip(result, 0, 1) * 255
    return result.astype(np.uint8)

def hdr_enhancement(image, clip_limit=3.0, grid_size=(8, 8), sigma_s=10, sigma_r=0.15):
    """HDR增强（结合CLAHE和双边滤波）"""
    # 应用CLAHE增强对比度
    clahe_img = clahe_enhancement(image, clip_limit, grid_size)
    
    # 使用双边滤波保持边缘细节
    # 先转换为float32以避免溢出
    img_float = clahe_img.astype(np.float32) / 255.0
    
    # 双边滤波
    bilateral = cv2.bilateralFilter(img_float, -1, sigma_r, sigma_s)
    
    # 转回uint8
    result = (bilateral * 255).astype(np.uint8)
    
    # 调整饱和度
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.2, 0, 255)  # 增加饱和度
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    return result

def estimate_brightness(image):
    """估计图像亮度"""
    # 转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 计算平均亮度
    mean_brightness = np.mean(gray)
    
    # 归一化到0-1范围
    normalized_brightness = mean_brightness / 255.0
    
    return normalized_brightness

def estimate_blurriness(image):
    """估计图像模糊度"""
    # 转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 使用拉普拉斯算子计算图像清晰度
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blurriness = np.var(laplacian)
    
    return blurriness

def auto_quality_optimization(image, brightness_threshold_low=0.3, brightness_threshold_high=0.7, 
                             blur_threshold=100.0):
    """自动质量优化"""
    result = image.copy()
    
    # 估计亮度
    brightness = estimate_brightness(image)
    
    # 估计模糊度
    blurriness = estimate_blurriness(image)
    
    # 根据亮度自动调整
    if brightness < brightness_threshold_low:
        # 图像过暗，应用暗光增强
        result = low_light_enhancement(result, gamma=1.5 + (brightness_threshold_low - brightness) * 2)
    elif brightness > brightness_threshold_high:
        # 图像过亮，降低亮度
        result = gamma_correction(result, gamma=0.8)
    
    # 根据模糊度自动调整
    if blurriness < blur_threshold:
        # 图像模糊，应用锐化
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        result = cv2.filter2D(result, -1, kernel)
    
    # 自动对比度调整
    result = cv2.normalize(result, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    
    return result

def process_single_image(input_path, output_path, operations):
    """处理单个图像"""
    image = load_image(input_path)
    if image is None:
        return False
    
    # 应用操作
    for op in operations:
        op_type = op['type']
        
        if op_type == 'low_light':
            image = low_light_enhancement(image, **op['params'])
        elif op_type == 'dehaze':
            image = dehaze(image, **op['params'])
        elif op_type == 'hdr':
            image = hdr_enhancement(image, **op['params'])
        elif op_type == 'auto_optimize':
            image = auto_quality_optimization(image, **op['params'])
        elif op_type == 'gamma':
            image = gamma_correction(image, **op['params'])
        elif op_type == 'clahe':
            image = clahe_enhancement(image, **op['params'])
    
    return save_image(image, output_path)

def process_directory(input_dir, output_dir, operations, recursive=False, image_extensions=None):
    """批量处理目录中的图像"""
    if image_extensions is None:
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
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
                
                if process_single_image(input_path, output_path, operations):
                    processed_count += 1
                else:
                    failed_count += 1
    
    print(f"处理完成! 成功: {processed_count}, 失败: {failed_count}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='图像增强工具')
    parser.add_argument('--input', '-i', required=True, help='输入图像或目录路径')
    parser.add_argument('--output', '-o', required=True, help='输出图像或目录路径')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    # 暗光增强参数
    parser.add_argument('--low-light', action='store_true', help='应用暗光增强')
    parser.add_argument('--gamma', type=float, default=1.5, help='Gamma校正参数')
    parser.add_argument('--clahe-clip', type=float, default=2.0, help='CLAHE裁剪限制')
    parser.add_argument('--clahe-grid', type=int, nargs=2, default=(8, 8), help='CLAHE网格大小')
    
    # 去雾参数
    parser.add_argument('--dehaze', action='store_true', help='应用去雾算法')
    parser.add_argument('--omega', type=float, default=0.95, help='去雾算法中的omega参数')
    parser.add_argument('--t-min', type=float, default=0.1, help='去雾算法中的最小透射率')
    
    # HDR增强参数
    parser.add_argument('--hdr', action='store_true', help='应用HDR增强')
    parser.add_argument('--hdr-clip', type=float, default=3.0, help='HDR中的CLAHE裁剪限制')
    parser.add_argument('--hdr-grid', type=int, nargs=2, default=(8, 8), help='HDR中的CLAHE网格大小')
    parser.add_argument('--sigma-s', type=int, default=10, help='双边滤波空间sigma')
    parser.add_argument('--sigma-r', type=float, default=0.15, help='双边滤波范围sigma')
    
    # 自动优化参数
    parser.add_argument('--auto-optimize', action='store_true', help='应用自动质量优化')
    parser.add_argument('--brightness-low', type=float, default=0.3, help='亮度低阈值')
    parser.add_argument('--brightness-high', type=float, default=0.7, help='亮度高阈值')
    parser.add_argument('--blur-threshold', type=float, default=100.0, help='模糊度阈值')
    
    # 单独的gamma和clahe
    parser.add_argument('--only-gamma', action='store_true', help='仅应用gamma校正')
    parser.add_argument('--only-clahe', action='store_true', help='仅应用CLAHE增强')
    
    return parser.parse_args()

def build_operations(args):
    """根据命令行参数构建操作列表"""
    operations = []
    
    if args.low_light:
        operations.append({'type': 'low_light', 'params': {
            'gamma': args.gamma,
            'clahe_clip_limit': args.clahe_clip,
            'clahe_grid_size': tuple(args.clahe_grid)
        }})
    
    if args.dehaze:
        operations.append({'type': 'dehaze', 'params': {
            'omega': args.omega,
            't_min': args.t_min
        }})
    
    if args.hdr:
        operations.append({'type': 'hdr', 'params': {
            'clip_limit': args.hdr_clip,
            'grid_size': tuple(args.hdr_grid),
            'sigma_s': args.sigma_s,
            'sigma_r': args.sigma_r
        }})
    
    if args.auto_optimize:
        operations.append({'type': 'auto_optimize', 'params': {
            'brightness_threshold_low': args.brightness_low,
            'brightness_threshold_high': args.brightness_high,
            'blur_threshold': args.blur_threshold
        }})
    
    if args.only_gamma:
        operations.append({'type': 'gamma', 'params': {'gamma': args.gamma}})
    
    if args.only_clahe:
        operations.append({'type': 'clahe', 'params': {
            'clip_limit': args.clahe_clip,
            'grid_size': tuple(args.clahe_grid)
        }})
    
    return operations

def main():
    """主函数"""
    args = parse_arguments()
    operations = build_operations(args)
    
    if not operations:
        print("没有指定任何图像增强操作")
        return
    
    if os.path.isfile(args.input):
        # 处理单个文件
        if process_single_image(args.input, args.output, operations):
            print(f"图像已成功增强并保存到: {args.output}")
        else:
            print("图像增强失败")
    elif os.path.isdir(args.input):
        # 处理目录
        process_directory(args.input, args.output, operations, args.recursive)
    else:
        print(f"输入路径不存在: {args.input}")

if __name__ == "__main__":
    main()