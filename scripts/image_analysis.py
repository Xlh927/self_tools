#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像分析工具模块（A4）

功能：
- 亮度/直方图分析
- 模糊度检测
- 噪声估计
- 区域统计（ROI 分析）

支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
import glob
import json
from typing import List, Dict, Any, Optional, Tuple


def analyze_brightness(image: np.ndarray) -> Dict[str, float]:
    """
    分析图像亮度
    
    Args:
        image: 输入图像 (BGR格式)
    
    Returns:
        包含亮度统计信息的字典
    """
    # 转换到HSV色彩空间
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    value_channel = hsv[:, :, 2]  # V通道表示亮度
    
    # 计算亮度统计信息
    stats = {
        "mean_brightness": float(np.mean(value_channel)),
        "min_brightness": float(np.min(value_channel)),
        "max_brightness": float(np.max(value_channel)),
        "std_brightness": float(np.std(value_channel)),
        "percentile_10": float(np.percentile(value_channel, 10)),
        "percentile_90": float(np.percentile(value_channel, 90)),
        "brightness_class": classify_brightness(np.mean(value_channel))
    }
    
    return stats

def classify_brightness(mean_brightness: float) -> str:
    """
    根据平均亮度分类图像
    
    Args:
        mean_brightness: 平均亮度值 (0-255)
    
    Returns:
        亮度分类
    """
    if mean_brightness < 50:
        return "dark"
    elif mean_brightness < 100:
        return "dim"
    elif mean_brightness < 180:
        return "normal"
    elif mean_brightness < 230:
        return "bright"
    else:
        return "overexposed"

def compute_histogram(image: np.ndarray, channels: List[int] = None, bins: int = 256) -> Dict[str, List[float]]:
    """
    计算图像直方图
    
    Args:
        image: 输入图像 (BGR格式)
        channels: 要计算的通道列表
        bins: 直方图分箱数量
    
    Returns:
        包含直方图数据的字典
    """
    # 默认计算所有通道
    if channels is None:
        channels = [0, 1, 2]
    
    histograms = {}
    channel_names = ["blue", "green", "red"]
    
    # 计算每个通道的直方图
    for channel in channels:
        hist = cv2.calcHist([image], [channel], None, [bins], [0, 256])
        histograms[channel_names[channel]] = hist.flatten().tolist()
    
    # 计算灰度直方图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hist_gray = cv2.calcHist([gray], [0], None, [bins], [0, 256])
    histograms["gray"] = hist_gray.flatten().tolist()
    
    return histograms

def detect_blur_laplacian(image: np.ndarray, threshold: float = 100.0) -> Dict[str, Any]:
    """
    使用拉普拉斯算子检测图像模糊度
    
    Args:
        image: 输入图像 (BGR格式)
        threshold: 模糊度阈值
    
    Returns:
        包含模糊度信息的字典
    """
    # 转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 计算拉普拉斯方差
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()
    is_blur = variance < threshold
    
    # 模糊度评分 (0-100)，值越高越清晰
    blur_score = min(100, max(0, 100 * variance / 200))
    
    return {
        "laplacian_variance": float(variance),
        "blur_score": float(blur_score),
        "is_blur": is_blur,
        "blur_level": classify_blur_level(variance)
    }

def classify_blur_level(variance: float) -> str:
    """
    根据拉普拉斯方差分类模糊程度
    
    Args:
        variance: 拉普拉斯方差
    
    Returns:
        模糊程度分类
    """
    if variance < 30:
        return "very_blurry"
    elif variance < 70:
        return "blurry"
    elif variance < 150:
        return "slightly_blurry"
    elif variance < 250:
        return "focused"
    else:
        return "very_focused"

def estimate_noise(image: np.ndarray) -> Dict[str, float]:
    """
    估计图像噪声
    
    Args:
        image: 输入图像 (BGR格式)
    
    Returns:
        包含噪声估计的字典
    """
    # 转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 使用中值滤波去除噪声，然后计算差值作为噪声估计
    median_blur = cv2.medianBlur(gray, 3)
    noise = gray.astype(float) - median_blur.astype(float)
    
    # 计算噪声统计
    noise_stats = {
        "mean_noise": float(np.mean(np.abs(noise))),
        "std_noise": float(np.std(noise)),
        "max_noise": float(np.max(np.abs(noise))),
        "noise_level": classify_noise_level(np.std(noise))
    }
    
    # 计算不同频率区域的噪声
    # 分离图像为低频和高频成分
    low_freq = cv2.GaussianBlur(gray, (5, 5), 0)
    high_freq = gray.astype(float) - low_freq.astype(float)
    
    low_freq_noise = np.std(high_freq)
    noise_stats["low_freq_noise"] = float(low_freq_noise)
    
    return noise_stats

def classify_noise_level(noise_std: float) -> str:
    """
    分类噪声级别
    
    Args:
        noise_std: 噪声标准差
    
    Returns:
        噪声级别分类
    """
    if noise_std < 5:
        return "very_low"
    elif noise_std < 10:
        return "low"
    elif noise_std < 20:
        return "moderate"
    elif noise_std < 35:
        return "high"
    else:
        return "very_high"

def analyze_roi(image: np.ndarray, roi: Tuple[int, int, int, int]) -> Dict[str, Any]:
    """
    分析图像区域(ROI)的统计信息
    
    Args:
        image: 输入图像 (BGR格式)
        roi: 区域坐标 (x, y, width, height)
    
    Returns:
        包含ROI统计信息的字典
    """
    x, y, w, h = roi
    
    # 确保ROI在图像范围内
    h_img, w_img = image.shape[:2]
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = min(w, w_img - x)
    h = min(h, h_img - y)
    
    # 提取ROI
    roi_img = image[y:y+h, x:x+w]
    
    # 计算RGB统计
    b, g, r = cv2.split(roi_img)
    rgb_stats = {
        "mean_blue": float(np.mean(b)),
        "mean_green": float(np.mean(g)),
        "mean_red": float(np.mean(r)),
        "std_blue": float(np.std(b)),
        "std_green": float(np.std(g)),
        "std_red": float(np.std(r))
    }
    
    # 转换到HSV并计算统计
    hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    hsv_stats = {
        "mean_hue": float(np.mean(h)),
        "mean_saturation": float(np.mean(s)),
        "mean_value": float(np.mean(v)),
        "std_hue": float(np.std(h)),
        "std_saturation": float(np.std(s)),
        "std_value": float(np.std(v))
    }
    
    # 计算灰度统计
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    gray_stats = {
        "mean_gray": float(np.mean(gray)),
        "std_gray": float(np.std(gray)),
        "min_gray": float(np.min(gray)),
        "max_gray": float(np.max(gray))
    }
    
    return {
        "roi_coordinates": roi,
        "roi_size": {"width": w, "height": h, "area": w * h},
        "rgb_stats": rgb_stats,
        "hsv_stats": hsv_stats,
        "gray_stats": gray_stats
    }

def analyze_entire_image(image: np.ndarray, roi: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
    """
    分析整个图像的所有特征
    
    Args:
        image: 输入图像 (BGR格式)
        roi: 可选的ROI区域
    
    Returns:
        包含所有分析结果的字典
    """
    # 基本图像信息
    h, w = image.shape[:2]
    results = {
        "image_info": {
            "width": w,
            "height": h,
            "channels": image.shape[2] if len(image.shape) > 2 else 1,
            "aspect_ratio": round(w / h, 4)
        }
    }
    
    # 亮度分析
    results["brightness"] = analyze_brightness(image)
    
    # 模糊度检测
    results["blur_detection"] = detect_blur_laplacian(image)
    
    # 噪声估计
    results["noise_estimation"] = estimate_noise(image)
    
    # ROI分析（如果指定了ROI）
    if roi:
        results["roi_analysis"] = analyze_roi(image, roi)
    
    # 直方图分析（可选，可能会很大）
    # results["histogram"] = compute_histogram(image)
    
    return results

def save_analysis_results(results: Dict[str, Any], output_path: str, format: str = "json") -> bool:
    """
    保存分析结果
    
    Args:
        results: 分析结果
        output_path: 输出文件路径
        format: 输出格式 (json)
    
    Returns:
        是否保存成功
    """
    try:
        if format == "json":
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存为JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"分析结果已保存到: {output_path}")
            return True
        else:
            print(f"不支持的输出格式: {format}")
            return False
    except Exception as e:
        print(f"保存分析结果失败: {str(e)}")
        return False

def analyze_single_image(
    input_path: str,
    output_path: str = None,
    roi: Optional[Tuple[int, int, int, int]] = None,
    save_histogram: bool = False
) -> Dict[str, Any]:
    """
    分析单个图像
    
    Args:
        input_path: 输入图像路径
        output_path: 输出结果路径
        roi: 可选的ROI区域
        save_histogram: 是否保存直方图数据
    
    Returns:
        分析结果
    """
    # 读取图像
    image = cv2.imread(input_path)
    if image is None:
        print(f"错误: 无法读取图像 {input_path}")
        return {}
    
    print(f"正在分析图像: {input_path}")
    
    # 执行分析
    results = analyze_entire_image(image, roi)
    results["file_path"] = input_path
    
    # 如果需要，添加直方图数据
    if save_histogram:
        results["histogram"] = compute_histogram(image)
    
    # 保存结果
    if output_path:
        save_analysis_results(results, output_path)
    
    # 打印简要结果
    print(f"图像尺寸: {results['image_info']['width']}x{results['image_info']['height']}")
    print(f"亮度分类: {results['brightness']['brightness_class']} (均值: {results['brightness']['mean_brightness']:.2f})")
    print(f"模糊程度: {results['blur_detection']['blur_level']} (评分: {results['blur_detection']['blur_score']:.2f})")
    print(f"噪声级别: {results['noise_estimation']['noise_level']} (标准差: {results['noise_estimation']['std_noise']:.2f})")
    print("=" * 50)
    
    return results

def batch_analyze_images(
    input_dir: str,
    output_dir: str,
    recursive: bool = False,
    save_histogram: bool = False
) -> int:
    """
    批量分析图像
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        recursive: 是否递归处理子目录
        save_histogram: 是否保存直方图数据
    
    Returns:
        成功分析的图像数量
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取图像文件列表
    if recursive:
        glob_pattern = os.path.join(input_dir, "**", "*.???")
    else:
        glob_pattern = os.path.join(input_dir, "*.???")
    
    # 常见图像格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_files = [
        f for f in glob.glob(glob_pattern, recursive=recursive)
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in image_extensions
    ]
    
    # 分析每个图像
    success_count = 0
    for image_path in image_files:
        # 构建输出文件路径
        rel_path = os.path.relpath(image_path, input_dir)
        output_path = os.path.join(output_dir, f"{os.path.splitext(rel_path)[0]}_analysis.json")
        
        # 确保输出子目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 分析图像
        results = analyze_single_image(image_path, output_path, save_histogram=save_histogram)
        if results:
            success_count += 1
    
    return success_count

def parse_roi(roi_str: str) -> Tuple[int, int, int, int]:
    """
    解析ROI字符串
    
    Args:
        roi_str: ROI字符串，格式为 "x,y,width,height"
    
    Returns:
        ROI元组
    """
    try:
        parts = list(map(int, roi_str.split(',')))
        if len(parts) != 4:
            raise ValueError("ROI格式应为 'x,y,width,height'")
        return tuple(parts)
    except Exception as e:
        raise ValueError(f"无效的ROI格式: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="图像分析工具")
    
    # 基本参数
    parser.add_argument("-i", "--input", required=True, help="输入图像或目录路径")
    parser.add_argument("-o", "--output", help="输出结果文件或目录路径")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    # 分析选项
    parser.add_argument("--roi", help="指定ROI区域 (格式: x,y,width,height)")
    parser.add_argument("--histogram", action="store_true", help="保存直方图数据")
    
    args = parser.parse_args()
    
    # 解析ROI（如果指定）
    roi = parse_roi(args.roi) if args.roi else None
    
    # 确定是单文件还是批量处理
    if os.path.isfile(args.input):
        # 单文件处理
        if not args.output:
            # 如果未指定输出路径，默认在输入文件同目录下生成
            base_name = os.path.splitext(args.input)[0]
            output_path = f"{base_name}_analysis.json"
        else:
            # 如果输出是目录，生成文件名
            if os.path.isdir(args.output):
                base_name = os.path.splitext(os.path.basename(args.input))[0]
                output_path = os.path.join(args.output, f"{base_name}_analysis.json")
                os.makedirs(args.output, exist_ok=True)
            else:
                output_path = args.output
        
        analyze_single_image(args.input, output_path, roi, args.histogram)
        print(f"\n单文件分析完成。")
    else:
        # 批量处理
        if not args.output:
            parser.error("批量处理时必须指定输出目录")
        
        success_count = batch_analyze_images(
            args.input, 
            args.output, 
            args.recursive, 
            args.histogram
        )
        print(f"\n批量分析完成。成功分析 {success_count} 个图像。")


if __name__ == "__main__":
    main()