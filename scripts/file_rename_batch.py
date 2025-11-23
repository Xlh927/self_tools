#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件重命名/批处理模块（C1）

功能：
- 正则/批量重命名
- 自动序号
- 替换文件扩展名

支持单文件和批量文件夹处理
"""

import os
import re
import argparse
import glob
from typing import List, Tuple, Optional


def batch_rename_files(
    input_path: str,
    pattern: str,
    replacement: str,
    recursive: bool = False,
    file_extensions: Optional[List[str]] = None,
    start_number: int = 1,
    number_format: str = "%04d",
    replace_extension: Optional[str] = None,
    output_dir: Optional[str] = None
) -> List[Tuple[str, str]]:
    """
    批量重命名文件
    
    Args:
        input_path: 输入文件或目录路径
        pattern: 匹配模式（正则表达式）
        replacement: 替换模式
        recursive: 是否递归处理子目录
        file_extensions: 过滤的文件扩展名列表，None表示所有文件
        start_number: 自动序号的起始数字
        number_format: 序号格式字符串
        replace_extension: 替换的扩展名，None表示不替换
        output_dir: 输出目录，None表示在原位置重命名
    
    Returns:
        重命名的文件列表，每个元素为(原文件路径, 新文件路径)
    """
    renamed_files = []
    current_number = start_number
    
    # 检查输入路径是否存在
    if not os.path.exists(input_path):
        print(f"错误：路径不存在 - {input_path}")
        return renamed_files
    
    # 处理单文件
    if os.path.isfile(input_path):
        file_list = [input_path]
    else:
        # 处理目录
        if recursive:
            glob_pattern = os.path.join(input_path, "**", "*")
        else:
            glob_pattern = os.path.join(input_path, "*")
        
        file_list = [f for f in glob.glob(glob_pattern, recursive=recursive) if os.path.isfile(f)]
        
        # 按扩展名过滤
        if file_extensions:
            file_list = [
                f for f in file_list 
                if any(f.lower().endswith(f".{ext.lower()}") for ext in file_extensions)
            ]
    
    # 确保输出目录存在
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    for file_path in file_list:
        dir_name, base_name = os.path.split(file_path)
        file_name, ext = os.path.splitext(base_name)
        
        # 应用正则替换
        new_name = re.sub(pattern, replacement, file_name)
        
        # 处理序号替换
        if "{number}" in new_name:
            new_name = new_name.replace("{number}", number_format % current_number)
            current_number += 1
        
        # 处理扩展名替换
        if replace_extension:
            new_ext = f".{replace_extension.lstrip('.')}"
        else:
            new_ext = ext
        
        # 构建新文件名
        new_base_name = f"{new_name}{new_ext}"
        
        # 构建输出路径
        if output_dir:
            new_dir = output_dir
        else:
            new_dir = dir_name
        
        new_path = os.path.join(new_dir, new_base_name)
        
        # 避免覆盖现有文件
        counter = 1
        base_new_path, base_new_ext = os.path.splitext(new_path)
        while os.path.exists(new_path) and new_path != file_path:
            new_path = f"{base_new_path}_{counter}{base_new_ext}"
            counter += 1
        
        try:
            # 重命名文件
            if output_dir:
                import shutil
                shutil.copy2(file_path, new_path)
            else:
                os.rename(file_path, new_path)
            renamed_files.append((file_path, new_path))
            print(f"重命名: {file_path} -> {new_path}")
        except Exception as e:
            print(f"重命名失败 {file_path}: {str(e)}")
    
    return renamed_files


def auto_rename_with_sequence(
    input_dir: str,
    prefix: str,
    start_number: int = 1,
    number_format: str = "%04d",
    file_extensions: Optional[List[str]] = None,
    recursive: bool = False,
    output_dir: Optional[str] = None
) -> List[Tuple[str, str]]:
    """
    使用序号自动重命名文件
    
    Args:
        input_dir: 输入目录路径
        prefix: 文件名前缀
        start_number: 起始序号
        number_format: 序号格式
        file_extensions: 过滤的文件扩展名列表
        recursive: 是否递归处理子目录
        output_dir: 输出目录
    
    Returns:
        重命名的文件列表
    """
    if not os.path.isdir(input_dir):
        print(f"错误：输入路径不是目录 - {input_dir}")
        return []
    
    # 构建替换模式
    pattern = ".*"  # 匹配任何文件名
    replacement = f"{prefix}{{number}}"
    
    return batch_rename_files(
        input_path=input_dir,
        pattern=pattern,
        replacement=replacement,
        recursive=recursive,
        file_extensions=file_extensions,
        start_number=start_number,
        number_format=number_format,
        replace_extension=None,
        output_dir=output_dir
    )


def replace_file_extensions(
    input_path: str,
    new_extension: str,
    recursive: bool = False,
    file_extensions: Optional[List[str]] = None,
    output_dir: Optional[str] = None
) -> List[Tuple[str, str]]:
    """
    批量替换文件扩展名
    
    Args:
        input_path: 输入文件或目录路径
        new_extension: 新的扩展名
        recursive: 是否递归处理子目录
        file_extensions: 过滤的文件扩展名列表，None表示所有文件
        output_dir: 输出目录
    
    Returns:
        重命名的文件列表
    """
    # 对于扩展名替换，不需要修改文件名，只修改扩展名
    pattern = ".*"  # 匹配任何文件名
    replacement = "\\0"  # 保留原文件名
    
    return batch_rename_files(
        input_path=input_path,
        pattern=pattern,
        replacement=replacement,
        recursive=recursive,
        file_extensions=file_extensions,
        replace_extension=new_extension,
        output_dir=output_dir
    )


def main():
    parser = argparse.ArgumentParser(description="文件重命名/批处理工具")
    
    # 基本参数
    parser.add_argument("-i", "--input", required=True, help="输入文件或目录路径")
    parser.add_argument("-o", "--output", help="输出目录路径")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    parser.add_argument("--ext", nargs="+", help="过滤的文件扩展名列表")
    
    # 功能选择组
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--regex", action="store_true", help="使用正则表达式重命名")
    group.add_argument("--auto", action="store_true", help="使用序号自动重命名")
    group.add_argument("--replace-ext", help="替换文件扩展名")
    
    # 正则重命名参数
    parser.add_argument("--pattern", help="匹配模式（正则表达式）")
    parser.add_argument("--replacement", help="替换模式")
    
    # 自动序号参数
    parser.add_argument("--prefix", help="自动重命名的前缀")
    parser.add_argument("--start", type=int, default=1, help="起始序号")
    parser.add_argument("--format", default="%04d", help="序号格式")
    
    args = parser.parse_args()
    
    renamed_files = []
    
    if args.regex:
        if not args.pattern or not args.replacement:
            parser.error("使用正则重命名时，必须指定 --pattern 和 --replacement")
        
        renamed_files = batch_rename_files(
            input_path=args.input,
            pattern=args.pattern,
            replacement=args.replacement,
            recursive=args.recursive,
            file_extensions=args.ext,
            output_dir=args.output
        )
    
    elif args.auto:
        if not args.prefix:
            parser.error("使用自动序号重命名时，必须指定 --prefix")
        
        if not os.path.isdir(args.input):
            parser.error("使用自动序号重命名时，--input 必须是目录")
        
        renamed_files = auto_rename_with_sequence(
            input_dir=args.input,
            prefix=args.prefix,
            start_number=args.start,
            number_format=args.format,
            file_extensions=args.ext,
            recursive=args.recursive,
            output_dir=args.output
        )
    
    elif args.replace_ext:
        renamed_files = replace_file_extensions(
            input_path=args.input,
            new_extension=args.replace_ext,
            recursive=args.recursive,
            file_extensions=args.ext,
            output_dir=args.output
        )
    
    print(f"\n处理完成。共重命名 {len(renamed_files)} 个文件。")


if __name__ == "__main__":
    main()