#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础图像处理模块（A1）

功能：
- 图像裁剪、缩放、旋转
- 亮度/对比度/饱和度调整
- 去噪、锐化、模糊
- 灰度化/色彩转换

支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
from tqdm import tqdm
from PIL import Image, ImageEnhance

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

def crop_image(image, x, y, width, height):
    """裁剪图像"""
    h, w = image.shape[:2]
    # 确保裁剪区域有效
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    width = min(width, w - x)
    height = min(height, h - y)
    
    return image[y:y+height, x:x+width]

def resize_image(image, width=None, height=None, keep_ratio=True):
    """调整图像大小"""
    h, w = image.shape[:2]
    
    if keep_ratio and (width or height):
        if width and not height:
            ratio = width / w
            height = int(h * ratio)
        elif height and not width:
            ratio = height / h
            width = int(w * ratio)
    
    if not width and not height:
        return image
    
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)

def rotate_image(image, angle, keep_size=True, center=None):
    """旋转图像"""
    h, w = image.shape[:2]
    
    if center is None:
        center = (w // 2, h // 2)
    
    # 计算旋转矩阵
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    if keep_size:
        # 计算旋转后的新尺寸
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # 调整旋转矩阵以保持图像中心
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        return cv2.warpAffine(image, M, (new_w, new_h), borderMode=cv2.BORDER_REPLICATE)
    else:
        return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

def adjust_brightness(image, factor):
    """调整亮度"""
    # 转换为PIL图像进行亮度调整
    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Brightness(pil_img)
    enhanced_img = enhancer.enhance(factor)
    # 转回OpenCV格式
    return cv2.cvtColor(np.array(enhanced_img), cv2.COLOR_RGB2BGR)

def adjust_contrast(image, factor):
    """调整对比度"""
    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Contrast(pil_img)
    enhanced_img = enhancer.enhance(factor)
    return cv2.cvtColor(np.array(enhanced_img), cv2.COLOR_RGB2BGR)

def adjust_saturation(image, factor):
    """调整饱和度"""
    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Color(pil_img)
    enhanced_img = enhancer.enhance(factor)
    return cv2.cvtColor(np.array(enhanced_img), cv2.COLOR_RGB2BGR)

def denoise_image(image, method='gaussian', kernel_size=3, strength=10):
    """图像去噪"""
    if method == 'gaussian':
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    elif method == 'median':
        return cv2.medianBlur(image, kernel_size)
    elif method == 'bilateral':
        return cv2.bilateralFilter(image, kernel_size, strength, strength//2)
    elif method == 'nonlocal_means':
        if len(image.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(image, h=strength)
        else:
            return cv2.fastNlMeansDenoising(image, h=strength)
    else:
        print(f"未知的去噪方法: {method}")
        return image

def sharpen_image(image, strength=1.0):
    """图像锐化"""
    # 创建锐化核
    kernel = np.array([[-1, -1, -1],
                       [-1, 9 + strength, -1],
                       [-1, -1, -1]]) / (9 + strength)
    
    return cv2.filter2D(image, -1, kernel)

def blur_image(image, method='gaussian', kernel_size=5):
    """图像模糊"""
    if method == 'gaussian':
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    elif method == 'median':
        return cv2.medianBlur(image, kernel_size)
    elif method == 'box':
        return cv2.blur(image, (kernel_size, kernel_size))
    elif method == 'bilateral':
        return cv2.bilateralFilter(image, kernel_size, 75, 75)
    else:
        print(f"未知的模糊方法: {method}")
        return image

def to_grayscale(image):
    """转换为灰度图"""
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image

def convert_color_space(image, src_space, dst_space):
    """色彩空间转换"""
    color_conversion = {
        ('BGR', 'RGB'): cv2.COLOR_BGR2RGB,
        ('RGB', 'BGR'): cv2.COLOR_RGB2BGR,
        ('BGR', 'HSV'): cv2.COLOR_BGR2HSV,
        ('HSV', 'BGR'): cv2.COLOR_HSV2BGR,
        ('BGR', 'LAB'): cv2.COLOR_BGR2LAB,
        ('LAB', 'BGR'): cv2.COLOR_LAB2BGR,
        ('BGR', 'GRAY'): cv2.COLOR_BGR2GRAY,
        ('RGB', 'GRAY'): cv2.COLOR_RGB2GRAY,
        ('GRAY', 'BGR'): cv2.COLOR_GRAY2BGR,
        ('GRAY', 'RGB'): cv2.COLOR_GRAY2RGB
    }
    
    key = (src_space, dst_space)
    if key in color_conversion:
        return cv2.cvtColor(image, color_conversion[key])
    else:
        print(f"不支持的色彩空间转换: {src_space} -> {dst_space}")
        return image

def process_single_image(input_path, output_path, operations):
    """处理单个图像"""
    image = load_image(input_path)
    if image is None:
        return False
    
    # 应用操作
    for op in operations:
        op_type = op['type']
        
        if op_type == 'crop':
            image = crop_image(image, **op['params'])
        elif op_type == 'resize':
            image = resize_image(image, **op['params'])
        elif op_type == 'rotate':
            image = rotate_image(image, **op['params'])
        elif op_type == 'brightness':
            image = adjust_brightness(image, **op['params'])
        elif op_type == 'contrast':
            image = adjust_contrast(image, **op['params'])
        elif op_type == 'saturation':
            image = adjust_saturation(image, **op['params'])
        elif op_type == 'denoise':
            image = denoise_image(image, **op['params'])
        elif op_type == 'sharpen':
            image = sharpen_image(image, **op['params'])
        elif op_type == 'blur':
            image = blur_image(image, **op['params'])
        elif op_type == 'grayscale':
            image = to_grayscale(image)
        elif op_type == 'color_convert':
            image = convert_color_space(image, **op['params'])
    
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
    parser = argparse.ArgumentParser(description='基础图像处理工具')
    parser.add_argument('--input', '-i', required=True, help='输入图像或目录路径')
    parser.add_argument('--output', '-o', required=True, help='输出图像或目录路径')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    # 裁剪参数
    parser.add_argument('--crop', nargs=4, type=int, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'),
                      help='裁剪参数: x, y, width, height')
    
    # 调整大小参数
    parser.add_argument('--resize', nargs='+', type=int, metavar=('WIDTH', 'HEIGHT'),
                      help='调整大小参数: width [height]')
    parser.add_argument('--keep-ratio', action='store_true', help='保持宽高比')
    
    # 旋转参数
    parser.add_argument('--rotate', type=float, help='旋转角度')
    parser.add_argument('--keep-size', action='store_true', help='旋转后保持原始大小')
    
    # 亮度/对比度/饱和度参数
    parser.add_argument('--brightness', type=float, help='亮度调整因子 (0.0-2.0)')
    parser.add_argument('--contrast', type=float, help='对比度调整因子 (0.0-2.0)')
    parser.add_argument('--saturation', type=float, help='饱和度调整因子 (0.0-2.0)')
    
    # 去噪参数
    parser.add_argument('--denoise', type=str, choices=['gaussian', 'median', 'bilateral', 'nonlocal_means'],
                      help='去噪方法')
    parser.add_argument('--denoise-kernel', type=int, default=3, help='去噪核大小')
    parser.add_argument('--denoise-strength', type=int, default=10, help='去噪强度')
    
    # 锐化参数
    parser.add_argument('--sharpen', type=float, default=1.0, help='锐化强度')
    
    # 模糊参数
    parser.add_argument('--blur', type=str, choices=['gaussian', 'median', 'box', 'bilateral'],
                      help='模糊方法')
    parser.add_argument('--blur-kernel', type=int, default=5, help='模糊核大小')
    
    # 灰度化
    parser.add_argument('--grayscale', action='store_true', help='转换为灰度图')
    
    # 色彩转换
    parser.add_argument('--color-convert', nargs=2, metavar=('SRC', 'DST'),
                      help='色彩空间转换: 源空间 目标空间')
    
    return parser.parse_args()

def build_operations(args):
    """根据命令行参数构建操作列表"""
    operations = []
    
    if args.crop:
        x, y, width, height = args.crop
        operations.append({'type': 'crop', 'params': {'x': x, 'y': y, 'width': width, 'height': height}})
    
    if args.resize:
        params = {'keep_ratio': args.keep_ratio}
        if len(args.resize) == 1:
            params['width'] = args.resize[0]
        else:
            params['width'] = args.resize[0]
            params['height'] = args.resize[1]
        operations.append({'type': 'resize', 'params': params})
    
    if args.rotate is not None:
        operations.append({'type': 'rotate', 'params': {'angle': args.rotate, 'keep_size': args.keep_size}})
    
    if args.brightness is not None:
        operations.append({'type': 'brightness', 'params': {'factor': args.brightness}})
    
    if args.contrast is not None:
        operations.append({'type': 'contrast', 'params': {'factor': args.contrast}})
    
    if args.saturation is not None:
        operations.append({'type': 'saturation', 'params': {'factor': args.saturation}})
    
    if args.denoise:
        operations.append({'type': 'denoise', 'params': {
            'method': args.denoise,
            'kernel_size': args.denoise_kernel,
            'strength': args.denoise_strength
        }})
    
    if args.sharpen is not None:
        operations.append({'type': 'sharpen', 'params': {'strength': args.sharpen}})
    
    if args.blur:
        operations.append({'type': 'blur', 'params': {
            'method': args.blur,
            'kernel_size': args.blur_kernel
        }})
    
    if args.grayscale:
        operations.append({'type': 'grayscale', 'params': {}})
    
    if args.color_convert:
        src_space, dst_space = args.color_convert
        operations.append({'type': 'color_convert', 'params': {
            'src_space': src_space.upper(),
            'dst_space': dst_space.upper()
        }})
    
    return operations

def main():
    """主函数"""
    args = parse_arguments()
    operations = build_operations(args)
    
    if not operations:
        print("没有指定任何图像处理操作")
        return
    
    if os.path.isfile(args.input):
        # 处理单个文件
        if process_single_image(args.input, args.output, operations):
            print(f"图像已成功处理并保存到: {args.output}")
        else:
            print("图像处理失败")
    elif os.path.isdir(args.input):
        # 处理目录
        process_directory(args.input, args.output, operations, args.recursive)
    else:
        print(f"输入路径不存在: {args.input}")

if __name__ == "__main__":
    main()