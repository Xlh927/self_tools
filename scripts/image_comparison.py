#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像对比可视化模块（A5）

功能：
- A/B before-after 对比
- 多模型结果对比（模型对比台）
- 差分图像高亮

支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
import glob
import json
from typing import List, Dict, Any, Optional, Tuple
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


def ensure_cv2_available() -> bool:
    """
    确保cv2可用，并配置matplotlib中文字体
    
    Returns:
        是否配置成功
    """
    try:
        # 配置matplotlib中文字体
        plt.rcParams["font.sans-serif"] = ["SimHei"]  # 用来正常显示中文标签
        plt.rcParams["axes.unicode_minus"] = False  # 用来正常显示负号
        return True
    except Exception as e:
        print(f"警告: 配置matplotlib时出错: {str(e)}")
        return False

def load_image(image_path: str) -> Optional[np.ndarray]:
    """
    加载图像
    
    Args:
        image_path: 图像路径
    
    Returns:
        加载的图像或None
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"错误: 无法读取图像 {image_path}")
        return None
    
    # 转换BGR到RGB用于matplotlib显示
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

def save_comparison_image(fig: plt.Figure, output_path: str, dpi: int = 300) -> bool:
    """
    保存对比图像
    
    Args:
        fig: matplotlib图像对象
        output_path: 输出路径
        dpi: 图像DPI
    
    Returns:
        是否保存成功
    """
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存图像
        fig.savefig(output_path, bbox_inches='tight', dpi=dpi)
        plt.close(fig)
        print(f"对比图像已保存到: {output_path}")
        return True
    except Exception as e:
        print(f"保存对比图像失败: {str(e)}")
        plt.close(fig)
        return False

def create_ab_comparison(image1: np.ndarray, image2: np.ndarray, 
                        title1: str = "Before", title2: str = "After", 
                        layout: str = "horizontal", show_diff: bool = False) -> plt.Figure:
    """
    创建A/B对比图像
    
    Args:
        image1: 第一张图像 (RGB)
        image2: 第二张图像 (RGB)
        title1: 第一张图像标题
        title2: 第二张图像标题
        layout: 布局方向 (horizontal/vertical)
        show_diff: 是否显示差分图像
    
    Returns:
        matplotlib Figure对象
    """
    # 调整图像大小以匹配
    h1, w1 = image1.shape[:2]
    h2, w2 = image2.shape[:2]
    
    # 调整为共同的高度或宽度
    if layout == "horizontal":
        # 水平布局，调整高度
        target_height = min(h1, h2)
        image1 = cv2.resize(image1, (int(w1 * target_height / h1), target_height))
        image2 = cv2.resize(image2, (int(w2 * target_height / h2), target_height))
    else:
        # 垂直布局，调整宽度
        target_width = min(w1, w2)
        image1 = cv2.resize(image1, (target_width, int(h1 * target_width / w1)))
        image2 = cv2.resize(image2, (target_width, int(h2 * target_width / w2)))
    
    # 确定图布局
    if show_diff:
        if layout == "horizontal":
            fig, axes = plt.subplots(1, 3, figsize=(21, 7))
        else:
            fig, axes = plt.subplots(3, 1, figsize=(7, 21))
    else:
        if layout == "horizontal":
            fig, axes = plt.subplots(1, 2, figsize=(14, 7))
        else:
            fig, axes = plt.subplots(2, 1, figsize=(7, 14))
    
    # 显示第一张图像
    axes[0].imshow(image1)
    axes[0].set_title(title1, fontsize=16, pad=10)
    axes[0].axis('off')
    
    # 显示第二张图像
    axes[1].imshow(image2)
    axes[1].set_title(title2, fontsize=16, pad=10)
    axes[1].axis('off')
    
    # 如果需要，显示差分图像
    if show_diff:
        # 计算差分图像
        diff = compute_diff_image(image1, image2, highlight=True)
        axes[2].imshow(diff)
        axes[2].set_title("Difference", fontsize=16, pad=10)
        axes[2].axis('off')
    
    plt.tight_layout()
    return fig

def compute_diff_image(image1: np.ndarray, image2: np.ndarray, 
                      highlight: bool = True, threshold: float = 0.1) -> np.ndarray:
    """
    计算两张图像的差分图像
    
    Args:
        image1: 第一张图像 (RGB)
        image2: 第二张图像 (RGB)
        highlight: 是否高亮差异
        threshold: 差异阈值
    
    Returns:
        差分图像
    """
    # 确保图像尺寸相同
    if image1.shape != image2.shape:
        image2 = cv2.resize(image2, (image1.shape[1], image1.shape[0]))
    
    # 转换为float类型
    img1_float = image1.astype(float) / 255.0
    img2_float = image2.astype(float) / 255.0
    
    # 计算差异
    diff = np.abs(img1_float - img2_float)
    
    # 转换回uint8
    diff_uint8 = (diff * 255).astype(np.uint8)
    
    if highlight:
        # 生成高亮的差异图像
        # 创建一个热力图效果
        hsv = np.zeros((image1.shape[0], image1.shape[1], 3), dtype=np.uint8)
        
        # 计算灰度差异
        diff_gray = cv2.cvtColor(diff_uint8, cv2.COLOR_RGB2GRAY)
        
        # 对差异进行阈值处理
        mask = diff_gray > (threshold * 255)
        
        # 设置HSV值，红色表示高差异，黄色表示中差异，绿色表示低差异
        hsv[:,:,0] = 180 - (diff_gray * 180) // 255  # 色相范围从180(红色)到0(青色)
        hsv[:,:,1] = 255  # 饱和度为最大值
        hsv[:,:,2] = np.clip(diff_gray * 2, 0, 255)  # 增加亮度
        
        # 转换HSV到RGB
        highlighted = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        # 合并原始图像和高亮图像
        result = np.zeros_like(image1)
        result[mask] = highlighted[mask]
        result[~mask] = image1[~mask] * 0.7 + image2[~mask] * 0.3  # 非差异区域混合两个图像
        
        return result.astype(np.uint8)
    else:
        return diff_uint8

def create_multi_model_comparison(images: List[np.ndarray], titles: List[str], 
                                 layout: str = "grid") -> plt.Figure:
    """
    创建多模型结果对比
    
    Args:
        images: 图像列表 (RGB)
        titles: 图像标题列表
        layout: 布局方式 (grid/horizontal/vertical)
    
    Returns:
        matplotlib Figure对象
    """
    num_images = len(images)
    
    if num_images == 0:
        raise ValueError("图像列表不能为空")
    
    # 调整所有图像大小以匹配最小尺寸
    min_height = min(img.shape[0] for img in images)
    min_width = min(img.shape[1] for img in images)
    
    resized_images = []
    for img in images:
        resized = cv2.resize(img, (min_width, min_height))
        resized_images.append(resized)
    
    # 确定布局
    if layout == "grid":
        # 计算网格尺寸
        cols = min(3, num_images)
        rows = (num_images + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 7, rows * 6))
        axes = axes.flatten() if num_images > 1 else [axes]
        
        for i, (img, title) in enumerate(zip(resized_images, titles)):
            axes[i].imshow(img)
            axes[i].set_title(title, fontsize=14, pad=10)
            axes[i].axis('off')
        
        # 隐藏多余的子图
        for i in range(num_images, len(axes)):
            axes[i].axis('off')
    
    elif layout == "horizontal":
        fig, axes = plt.subplots(1, num_images, figsize=(num_images * 6, 6))
        axes = axes.flatten() if num_images > 1 else [axes]
        
        for i, (img, title) in enumerate(zip(resized_images, titles)):
            axes[i].imshow(img)
            axes[i].set_title(title, fontsize=14, pad=10)
            axes[i].axis('off')
    
    else:  # vertical
        fig, axes = plt.subplots(num_images, 1, figsize=(6, num_images * 6))
        axes = axes.flatten() if num_images > 1 else [axes]
        
        for i, (img, title) in enumerate(zip(resized_images, titles)):
            axes[i].imshow(img)
            axes[i].set_title(title, fontsize=14, pad=10)
            axes[i].axis('off')
    
    plt.tight_layout()
    return fig

def create_diff_highlight_comparison(image1: np.ndarray, image2: np.ndarray, 
                                    threshold: float = 0.1) -> plt.Figure:
    """
    创建差分高亮对比图像
    
    Args:
        image1: 第一张图像 (RGB)
        image2: 第二张图像 (RGB)
        threshold: 差异阈值
    
    Returns:
        matplotlib Figure对象
    """
    # 确保图像尺寸相同
    if image1.shape != image2.shape:
        image2 = cv2.resize(image2, (image1.shape[1], image1.shape[0]))
    
    # 计算差分图像
    diff = compute_diff_image(image1, image2, highlight=True, threshold=threshold)
    
    # 创建四宫格布局
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(2, 2, figure=fig)
    
    # 原图1
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(image1)
    ax1.set_title("Original 1", fontsize=16, pad=10)
    ax1.axis('off')
    
    # 原图2
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(image2)
    ax2.set_title("Original 2", fontsize=16, pad=10)
    ax2.axis('off')
    
    # 高亮差异图
    ax3 = fig.add_subplot(gs[1, :])
    ax3.imshow(diff)
    ax3.set_title("Highlighted Differences", fontsize=16, pad=10)
    ax3.axis('off')
    
    # 添加统计信息
    diff_gray = cv2.cvtColor(compute_diff_image(image1, image2, highlight=False), cv2.COLOR_RGB2GRAY)
    diff_percentage = (np.sum(diff_gray > (threshold * 255)) / diff_gray.size) * 100
    max_diff = np.max(diff_gray)
    
    stats_text = f"差异统计信息:\n" \
                 f"- 差异像素百分比: {diff_percentage:.2f}%\n" \
                 f"- 最大差异值: {max_diff:.2f}\n" \
                 f"- 使用阈值: {threshold:.2f}"
    
    fig.text(0.5, 0.01, stats_text, ha='center', va='bottom', fontsize=12, 
             bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=1'))
    
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    return fig

def compare_two_images(image1_path: str, image2_path: str, output_path: str,
                      title1: str = "Before", title2: str = "After",
                      layout: str = "horizontal", show_diff: bool = False,
                      dpi: int = 300) -> bool:
    """
    对比两张图像
    
    Args:
        image1_path: 第一张图像路径
        image2_path: 第二张图像路径
        output_path: 输出路径
        title1: 第一张图像标题
        title2: 第二张图像标题
        layout: 布局方向
        show_diff: 是否显示差分
        dpi: 输出图像DPI
    
    Returns:
        是否成功
    """
    # 加载图像
    image1 = load_image(image1_path)
    image2 = load_image(image2_path)
    
    if image1 is None or image2 is None:
        return False
    
    print(f"正在比较图像: {image1_path} 和 {image2_path}")
    
    # 创建对比图像
    fig = create_ab_comparison(image1, image2, title1, title2, layout, show_diff)
    
    # 保存对比图像
    return save_comparison_image(fig, output_path, dpi)

def compare_multiple_images(image_paths: List[str], output_path: str,
                           titles: Optional[List[str]] = None,
                           layout: str = "grid", dpi: int = 300) -> bool:
    """
    对比多张图像
    
    Args:
        image_paths: 图像路径列表
        output_path: 输出路径
        titles: 图像标题列表（可选）
        layout: 布局方式
        dpi: 输出图像DPI
    
    Returns:
        是否成功
    """
    # 加载所有图像
    images = []
    valid_paths = []
    
    for path in image_paths:
        img = load_image(path)
        if img is not None:
            images.append(img)
            valid_paths.append(path)
    
    if len(images) < 2:
        print(f"错误: 至少需要两张有效的图像进行比较，当前只加载了 {len(images)} 张")
        return False
    
    # 如果没有提供标题，使用文件名
    if titles is None or len(titles) != len(valid_paths):
        titles = [os.path.splitext(os.path.basename(path))[0] for path in valid_paths]
    
    print(f"正在比较 {len(images)} 张图像")
    
    # 创建对比图像
    fig = create_multi_model_comparison(images, titles, layout)
    
    # 保存对比图像
    return save_comparison_image(fig, output_path, dpi)

def highlight_differences(image1_path: str, image2_path: str, output_path: str,
                         threshold: float = 0.1, dpi: int = 300) -> bool:
    """
    高亮显示两张图像的差异
    
    Args:
        image1_path: 第一张图像路径
        image2_path: 第二张图像路径
        output_path: 输出路径
        threshold: 差异阈值
        dpi: 输出图像DPI
    
    Returns:
        是否成功
    """
    # 加载图像
    image1 = load_image(image1_path)
    image2 = load_image(image2_path)
    
    if image1 is None or image2 is None:
        return False
    
    print(f"正在高亮图像差异: {image1_path} 和 {image2_path}")
    
    # 创建差异高亮图像
    fig = create_diff_highlight_comparison(image1, image2, threshold)
    
    # 保存对比图像
    return save_comparison_image(fig, output_path, dpi)

def batch_compare_images(input_dir1: str, input_dir2: str, output_dir: str,
                         mode: str = "ab", threshold: float = 0.1, dpi: int = 300) -> int:
    """
    批量对比两个目录中的图像
    
    Args:
        input_dir1: 第一个输入目录
        input_dir2: 第二个输入目录
        output_dir: 输出目录
        mode: 比较模式 (ab/highlight)
        threshold: 差异阈值
        dpi: 输出图像DPI
    
    Returns:
        成功比较的图像对数量
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取图像文件列表
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    # 获取两个目录中的所有图像
    images1 = {}
    for ext in image_extensions:
        pattern = os.path.join(input_dir1, f"*{ext}")
        for file_path in glob.glob(pattern):
            filename = os.path.basename(file_path)
            images1[filename] = file_path
    
    images2 = {}
    for ext in image_extensions:
        pattern = os.path.join(input_dir2, f"*{ext}")
        for file_path in glob.glob(pattern):
            filename = os.path.basename(file_path)
            images2[filename] = file_path
    
    # 找出共同的文件名
    common_files = set(images1.keys()) & set(images2.keys())
    
    if not common_files:
        print(f"错误: 两个目录中没有找到名称相同的图像文件")
        return 0
    
    print(f"找到 {len(common_files)} 对匹配的图像文件")
    
    # 批量比较
    success_count = 0
    for filename in common_files:
        img1_path = images1[filename]
        img2_path = images2[filename]
        
        # 构建输出路径
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}_comparison.png")
        
        # 根据模式执行比较
        if mode == "ab":
            success = compare_two_images(
                img1_path, img2_path, output_path,
                title1="Directory 1", title2="Directory 2",
                show_diff=True, dpi=dpi
            )
        else:  # highlight
            success = highlight_differences(
                img1_path, img2_path, output_path,
                threshold=threshold, dpi=dpi
            )
        
        if success:
            success_count += 1
    
    return success_count

def main():
    parser = argparse.ArgumentParser(description="图像对比可视化工具")
    
    # 基本参数
    parser.add_argument("-i", "--input", help="输入图像路径或目录路径")
    parser.add_argument("--input2", help="第二个输入图像路径或目录路径（用于对比）")
    parser.add_argument("-o", "--output", required=True, help="输出结果文件或目录路径")
    
    # 比较模式
    parser.add_argument("--mode", choices=["ab", "multi", "highlight"], default="ab",
                      help="比较模式: ab(两两对比)/multi(多图对比)/highlight(差异高亮)")
    
    # 对比选项
    parser.add_argument("--layout", choices=["horizontal", "vertical", "grid"], default="horizontal",
                      help="布局方式")
    parser.add_argument("--show-diff", action="store_true", help="在AB对比中显示差异图像")
    parser.add_argument("--threshold", type=float, default=0.1, help="差异检测阈值")
    parser.add_argument("--dpi", type=int, default=300, help="输出图像DPI")
    
    args = parser.parse_args()
    
    # 确保cv2可用
    ensure_cv2_available()
    
    # 根据模式处理
    if args.mode == "ab":
        # AB对比模式
        if not args.input2:
            parser.error("AB对比模式需要指定 --input2 参数")
        
        # 检查是否为文件或目录
        if os.path.isfile(args.input) and os.path.isfile(args.input2):
            # 单文件对比
            compare_two_images(
                args.input, args.input2, args.output,
                layout=args.layout, show_diff=args.show_diff,
                dpi=args.dpi
            )
            print("\n单文件对比完成。")
        elif os.path.isdir(args.input) and os.path.isdir(args.input2):
            # 目录对比
            success_count = batch_compare_images(
                args.input, args.input2, args.output,
                mode="ab", dpi=args.dpi
            )
            print(f"\n目录对比完成。成功对比 {success_count} 对图像。")
        else:
            parser.error("AB对比模式要求 --input 和 --input2 同为文件或同为目录")
    
    elif args.mode == "multi":
        # 多图对比模式
        if os.path.isdir(args.input):
            # 获取目录中的所有图像
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            image_paths = []
            
            for ext in image_extensions:
                pattern = os.path.join(args.input, f"*{ext}")
                image_paths.extend(glob.glob(pattern))
            
            if len(image_paths) < 2:
                parser.error(f"多图对比至少需要两张图像，当前目录中只找到 {len(image_paths)} 张")
            
            compare_multiple_images(image_paths, args.output, layout=args.layout, dpi=args.dpi)
            print(f"\n多图对比完成，共对比 {len(image_paths)} 张图像。")
        else:
            parser.error("多图对比模式要求 --input 为目录")
    
    elif args.mode == "highlight":
        # 差异高亮模式
        if not args.input2:
            parser.error("差异高亮模式需要指定 --input2 参数")
        
        # 检查是否为文件或目录
        if os.path.isfile(args.input) and os.path.isfile(args.input2):
            # 单文件高亮
            highlight_differences(args.input, args.input2, args.output, threshold=args.threshold, dpi=args.dpi)
            print("\n差异高亮完成。")
        elif os.path.isdir(args.input) and os.path.isdir(args.input2):
            # 目录高亮
            success_count = batch_compare_images(
                args.input, args.input2, args.output,
                mode="highlight", threshold=args.threshold, dpi=args.dpi
            )
            print(f"\n目录差异高亮完成。成功处理 {success_count} 对图像。")
        else:
            parser.error("差异高亮模式要求 --input 和 --input2 同为文件或同为目录")


if __name__ == "__main__":
    main()