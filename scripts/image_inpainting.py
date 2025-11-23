#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像修复/生成模块（A3）

功能：
- Inpainting（Lama/Diffusers）
- 擦除红框/遮挡物
- 背景替换（自动抠图）

支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
import glob
from typing import List, Tuple, Optional, Union

# 尝试导入深度学习相关库
HAS_DIFFUSERS = False
try:
    from diffusers import StableDiffusionInpaintPipeline
    import torch
    HAS_DIFFUSERS = True
except ImportError:
    print("警告: 未安装diffusers库，将无法使用基于Diffusers的Inpainting功能")


def create_mask_from_red_boxes(image: np.ndarray, threshold: int = 100) -> np.ndarray:
    """
    从图像中检测并创建红框区域的掩码
    
    Args:
        image: 输入图像 (BGR格式)
        threshold: 红色检测阈值
    
    Returns:
        二值掩码，红框区域为255，其他区域为0
    """
    # 转换到HSV色彩空间以便更好地检测红色
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 红色在HSV中的范围（处理红色的环绕性质）
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([179, 255, 255])
    
    # 创建红色掩码
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 | mask2
    
    # 形态学操作以增强掩码
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # 寻找轮廓并填充
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled_mask = np.zeros_like(mask)
    
    for contour in contours:
        # 只填充较大的轮廓（可能是红框）
        if cv2.contourArea(contour) > threshold:
            cv2.drawContours(filled_mask, [contour], -1, 255, -1)
    
    return filled_mask


def inpaint_with_opencv(
    image: np.ndarray, 
    mask: np.ndarray,
    method: str = 'telea',
    radius: int = 3
) -> np.ndarray:
    """
    使用OpenCV进行图像修复
    
    Args:
        image: 输入图像 (BGR格式)
        mask: 修复掩码，需要修复的区域为255，其他区域为0
        method: 修复方法 ('telea' 或 'ns')
        radius: 修复半径
    
    Returns:
        修复后的图像
    """
    if method == 'telea':
        method_code = cv2.INPAINT_TELEA
    elif method == 'ns':
        method_code = cv2.INPAINT_NS
    else:
        raise ValueError("修复方法必须是'telea'或'ns'")
    
    return cv2.inpaint(image, mask, radius, method_code)


def inpaint_with_diffusers(
    image: np.ndarray,
    mask: np.ndarray,
    prompt: str = "",
    model_id: str = "runwayml/stable-diffusion-inpainting"
) -> Optional[np.ndarray]:
    """
    使用Diffusers库进行基于AI的图像修复
    
    Args:
        image: 输入图像 (BGR格式)
        mask: 修复掩码
        prompt: 修复提示词
        model_id: 使用的模型ID
    
    Returns:
        修复后的图像，失败返回None
    """
    if not HAS_DIFFUSERS:
        print("错误: 未安装diffusers库，请运行 'pip install diffusers transformers accelerate'")
        return None
    
    try:
        # 确保有可用的设备
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 加载模型
        pipeline = StableDiffusionInpaintPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        ).to(device)
        
        # 转换图像格式
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 调整图像大小以适应模型要求
        height, width = image.shape[:2]
        target_size = (512, 512)  # SD inpainting模型通常需要512x512输入
        
        resized_image = cv2.resize(image_rgb, target_size)
        resized_mask = cv2.resize(mask, target_size)
        
        # 执行inpainting
        result = pipeline(
            prompt=prompt or "修复此图像中的缺失部分，使其看起来自然",
            image=resized_image,
            mask_image=resized_mask,
            guidance_scale=7.5,
            num_inference_steps=50
        ).images[0]
        
        # 转换回BGR并调整回原始大小
        result_np = np.array(result)
        result_bgr = cv2.cvtColor(result_np, cv2.COLOR_RGB2BGR)
        result_resized = cv2.resize(result_bgr, (width, height))
        
        return result_resized
    except Exception as e:
        print(f"Diffusers inpainting失败: {str(e)}")
        return None


def remove_red_boxes(
    image: np.ndarray,
    method: str = 'opencv',
    opencv_method: str = 'telea',
    prompt: str = ""
) -> np.ndarray:
    """
    检测并移除图像中的红框
    
    Args:
        image: 输入图像 (BGR格式)
        method: 修复方法 ('opencv' 或 'diffusers')
        opencv_method: OpenCV修复方法 ('telea' 或 'ns')
        prompt: Diffusers修复提示词
    
    Returns:
        移除红框后的图像
    """
    # 创建红框掩码
    mask = create_mask_from_red_boxes(image)
    
    # 如果没有检测到红框，返回原图
    if not np.any(mask):
        return image.copy()
    
    # 执行修复
    if method == 'diffusers' and HAS_DIFFUSERS:
        result = inpaint_with_diffusers(image, mask, prompt)
        if result is not None:
            return result
    
    # 如果Diffusers失败或未指定，回退到OpenCV方法
    return inpaint_with_opencv(image, mask, opencv_method)


def simple_background_removal(
    image: np.ndarray,
    threshold: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    """
    简单的背景移除（基于边缘检测和GrabCut）
    
    Args:
        image: 输入图像 (BGR格式)
        threshold: 边缘检测阈值
    
    Returns:
        (前景图像, 掩码)
    """
    # 创建掩码和临时数组
    mask = np.zeros(image.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    
    # 尝试使用边缘检测来帮助前景提取
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, threshold, threshold * 2)
    
    # 膨胀边缘以创建更连通的区域
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    edges = cv2.morphologyEx(edges, cv2.MORPH_DILATE, kernel)
    
    # 找到最大的轮廓作为前景
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # 找到最大的轮廓
        largest_contour = max(contours, key=cv2.contourArea)
        
        # 创建包围矩形
        x, y, w, h = cv2.boundingRect(largest_contour)
        rect = (x, y, w, h)
        
        # 使用GrabCut算法
        cv2.grabCut(image, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    
    # 创建二进制掩码
    binary_mask = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8') * 255
    
    # 应用掩码到原图
    foreground = cv2.bitwise_and(image, image, mask=binary_mask)
    
    return foreground, binary_mask


def replace_background(
    image: np.ndarray,
    new_background: Union[str, np.ndarray],
    resize_method: str = 'fit'
) -> np.ndarray:
    """
    替换图像背景
    
    Args:
        image: 输入图像 (BGR格式)
        new_background: 新背景图像路径或BGR数组
        resize_method: 背景调整方法 ('fit', 'cover')
    
    Returns:
        背景替换后的图像
    """
    # 获取前景和掩码
    foreground, mask = simple_background_removal(image)
    
    # 读取或使用新背景
    if isinstance(new_background, str):
        bg_image = cv2.imread(new_background)
        if bg_image is None:
            raise FileNotFoundError(f"无法读取背景图像: {new_background}")
    else:
        bg_image = new_background.copy()
    
    # 获取前景尺寸
    h, w = image.shape[:2]
    
    # 调整背景大小
    bg_h, bg_w = bg_image.shape[:2]
    
    if resize_method == 'fit':
        # 等比例缩放背景以适应前景
        scale = min(w / bg_w, h / bg_h)
        new_bg_w = int(bg_w * scale)
        new_bg_h = int(bg_h * scale)
        resized_bg = cv2.resize(bg_image, (new_bg_w, new_bg_h))
        
        # 创建与前景相同大小的背景
        final_bg = np.zeros_like(image)
        x_offset = (w - new_bg_w) // 2
        y_offset = (h - new_bg_h) // 2
        final_bg[y_offset:y_offset+new_bg_h, x_offset:x_offset+new_bg_w] = resized_bg
    else:  # 'cover'
        # 等比例缩放背景以覆盖前景
        scale = max(w / bg_w, h / bg_h)
        new_bg_w = int(bg_w * scale)
        new_bg_h = int(bg_h * scale)
        resized_bg = cv2.resize(bg_image, (new_bg_w, new_bg_h))
        
        # 裁剪以匹配前景大小
        x_start = (new_bg_w - w) // 2
        y_start = (new_bg_h - h) // 2
        final_bg = resized_bg[y_start:y_start+h, x_start:x_start+w]
    
    # 创建逆掩码
    mask_inv = cv2.bitwise_not(mask)
    
    # 从背景中提取前景区域
    bg_part = cv2.bitwise_and(final_bg, final_bg, mask=mask_inv)
    
    # 合并前景和背景
    result = cv2.add(foreground, bg_part)
    
    return result


def process_single_image(
    input_path: str,
    output_path: str,
    operation: str,
    **kwargs
) -> bool:
    """
    处理单个图像
    
    Args:
        input_path: 输入图像路径
        output_path: 输出图像路径
        operation: 操作类型 ('inpaint', 'remove_red_boxes', 'replace_background')
        **kwargs: 其他参数
    
    Returns:
        是否处理成功
    """
    # 读取图像
    image = cv2.imread(input_path)
    if image is None:
        print(f"错误: 无法读取图像 {input_path}")
        return False
    
    try:
        # 执行相应操作
        if operation == 'inpaint':
            # 检查是否提供了掩码
            mask_path = kwargs.get('mask_path')
            if mask_path:
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is None:
                    print(f"错误: 无法读取掩码 {mask_path}")
                    return False
            else:
                # 如果没有提供掩码，尝试检测红框
                mask = create_mask_from_red_boxes(image)
            
            # 选择修复方法
            method = kwargs.get('method', 'opencv')
            if method == 'diffusers' and HAS_DIFFUSERS:
                result = inpaint_with_diffusers(image, mask, kwargs.get('prompt', ''))
                if result is None:
                    # 回退到OpenCV
                    result = inpaint_with_opencv(image, mask, kwargs.get('opencv_method', 'telea'))
            else:
                result = inpaint_with_opencv(image, mask, kwargs.get('opencv_method', 'telea'))
        
        elif operation == 'remove_red_boxes':
            result = remove_red_boxes(
                image,
                method=kwargs.get('method', 'opencv'),
                opencv_method=kwargs.get('opencv_method', 'telea'),
                prompt=kwargs.get('prompt', '')
            )
        
        elif operation == 'replace_background':
            bg_path = kwargs.get('background_path')
            if not bg_path:
                print("错误: 替换背景需要指定背景图像路径")
                return False
            result = replace_background(image, bg_path, kwargs.get('resize_method', 'fit'))
        
        else:
            print(f"错误: 未知操作 {operation}")
            return False
        
        # 保存结果
        cv2.imwrite(output_path, result)
        print(f"处理成功: {input_path} -> {output_path}")
        return True
    
    except Exception as e:
        print(f"处理失败 {input_path}: {str(e)}")
        return False


def batch_process(
    input_path: str,
    output_dir: str,
    operation: str,
    recursive: bool = False,
    **kwargs
) -> int:
    """
    批量处理图像
    
    Args:
        input_path: 输入文件或目录路径
        output_dir: 输出目录路径
        operation: 操作类型
        recursive: 是否递归处理子目录
        **kwargs: 其他参数
    
    Returns:
        成功处理的文件数量
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取文件列表
    if os.path.isfile(input_path):
        file_list = [input_path]
    else:
        if recursive:
            glob_pattern = os.path.join(input_path, "**", "*.???")
        else:
            glob_pattern = os.path.join(input_path, "*.???")
        
        # 筛选常见图像格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        file_list = [
            f for f in glob.glob(glob_pattern, recursive=recursive)
            if os.path.isfile(f) and os.path.splitext(f)[1].lower() in image_extensions
        ]
    
    # 处理每个文件
    success_count = 0
    for file_path in file_list:
        # 构建输出路径
        base_name = os.path.basename(file_path)
        output_path = os.path.join(output_dir, base_name)
        
        # 处理文件
        if process_single_image(file_path, output_path, operation, **kwargs):
            success_count += 1
    
    return success_count


def main():
    parser = argparse.ArgumentParser(description="图像修复/生成工具")
    
    # 基本参数
    parser.add_argument("-i", "--input", required=True, help="输入图像或目录路径")
    parser.add_argument("-o", "--output", required=True, help="输出图像或目录路径")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    # 功能选择组
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inpaint", action="store_true", help="图像修复")
    group.add_argument("--remove-red-boxes", action="store_true", help="移除红框")
    group.add_argument("--replace-background", action="store_true", help="替换背景")
    
    # Inpainting参数
    parser.add_argument("--mask", help="修复掩码图像路径")
    parser.add_argument("--method", choices=["opencv", "diffusers"], default="opencv", help="修复方法")
    parser.add_argument("--opencv-method", choices=["telea", "ns"], default="telea", help="OpenCV修复算法")
    parser.add_argument("--prompt", help="AI修复提示词")
    
    # 背景替换参数
    parser.add_argument("--background", help="新背景图像路径")
    parser.add_argument("--resize-method", choices=["fit", "cover"], default="fit", help="背景调整方法")
    
    args = parser.parse_args()
    
    # 确定操作类型
    if args.inpaint:
        operation = "inpaint"
    elif args.remove_red_boxes:
        operation = "remove_red_boxes"
    elif args.replace_background:
        operation = "replace_background"
    
    # 准备参数
    kwargs = {
        "method": args.method,
        "opencv_method": args.opencv_method,
        "prompt": args.prompt
    }
    
    if operation == "inpaint":
        kwargs["mask_path"] = args.mask
    elif operation == "replace_background":
        if not args.background:
            parser.error("替换背景时必须指定 --background 参数")
        kwargs["background_path"] = args.background
        kwargs["resize_method"] = args.resize_method
    
    # 执行处理
    if os.path.isfile(args.input):
        # 单文件处理
        if os.path.isdir(args.output):
            # 如果输出是目录，生成输出文件名
            base_name = os.path.basename(args.input)
            output_path = os.path.join(args.output, base_name)
            os.makedirs(args.output, exist_ok=True)
        else:
            # 确保输出目录存在
            output_dir = os.path.dirname(args.output)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            output_path = args.output
        
        success = process_single_image(args.input, output_path, operation, **kwargs)
        print(f"处理完成。{'成功' if success else '失败'}")
    else:
        # 批量处理
        success_count = batch_process(
            args.input,
            args.output,
            operation,
            args.recursive,
            **kwargs
        )
        print(f"\n批量处理完成。成功处理 {success_count} 个文件。")


if __name__ == "__main__":
    main()