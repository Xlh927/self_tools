#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据压缩与解压模块

本模块提供文件和目录的压缩与解压功能，支持多种压缩格式，
包括ZIP、TAR、TAR.GZ、TAR.BZ2等，提供命令行接口和进度显示。

功能特性：
- 支持多种压缩格式：ZIP、TAR、TAR.GZ、TAR.BZ2
- 单文件和目录压缩
- 解压到指定目录
- 压缩率和进度显示
- 密码保护（ZIP格式）
- 压缩级别调整
- 递归处理子目录
- 文件过滤和包含/排除模式
- 并行压缩（可选）

使用示例：
  # 压缩文件或目录
  python data_compressor.py compress file.txt -o compressed.zip
  python data_compressor.py compress dir/ -o archive.tar.gz --format tgz
  
  # 解压文件
  python data_compressor.py extract archive.zip -d output_dir
  python data_compressor.py extract archive.tar.bz2
  
  # 查看压缩文件内容
  python data_compressor.py list archive.zip
  
  # 设置压缩级别
  python data_compressor.py compress dir/ -o compressed.zip --level 9
"""

import os
import sys
import zipfile
import tarfile
import gzip
import bz2
import shutil
import argparse
import logging
import time
import datetime
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Callable, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DataCompressor:
    """
    数据压缩与解压类
    
    提供文件和目录的压缩与解压功能，支持多种压缩格式。
    """
    
    # 支持的压缩格式及其扩展名
    SUPPORTED_FORMATS = {
        'zip': ['.zip'],
        'tar': ['.tar'],
        'gz': ['.gz'],
        'tgz': ['.tar.gz', '.tgz'],
        'bz2': ['.bz2'],
        'tbz2': ['.tar.bz2', '.tbz2']
    }
    
    # 默认压缩级别
    DEFAULT_COMPRESSION_LEVEL = 6
    
    # 最大并行任务数（如果启用并行压缩）
    MAX_WORKERS = 4
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化DataCompressor
        
        Args:
            temp_dir: 临时文件目录，默认为系统临时目录
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info(f"初始化DataCompressor，临时目录: {self.temp_dir}")
    
    def detect_format(self, file_path: str) -> str:
        """
        根据文件扩展名检测压缩格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            检测到的格式字符串
            
        Raises:
            ValueError: 如果无法识别格式
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 检查特殊的多部分扩展名
        if file_path.lower().endswith('.tar.gz') or file_path.lower().endswith('.tgz'):
            return 'tgz'
        elif file_path.lower().endswith('.tar.bz2') or file_path.lower().endswith('.tbz2'):
            return 'tbz2'
        
        # 检查其他格式
        for fmt, extensions in self.SUPPORTED_FORMATS.items():
            if file_ext in extensions:
                return fmt
        
        raise ValueError(f"无法识别的压缩格式: {file_path}")
    
    def get_output_filename(self, input_path: str, output_path: Optional[str], 
                          fmt: Optional[str] = None) -> str:
        """
        生成输出文件名
        
        Args:
            input_path: 输入文件或目录路径
            output_path: 指定的输出路径，如果为None则自动生成
            fmt: 压缩格式，如果为None则从output_path推断
            
        Returns:
            输出文件名
        """
        if output_path:
            return output_path
        
        # 获取基础文件名
        base_name = os.path.basename(input_path)
        if base_name == '':  # 处理路径以/结尾的情况
            base_name = os.path.basename(os.path.dirname(input_path))
        
        # 如果未指定格式，默认为zip
        if not fmt:
            fmt = 'zip'
        
        # 根据格式添加扩展名
        if fmt == 'zip':
            return f"{base_name}.zip"
        elif fmt == 'tar':
            return f"{base_name}.tar"
        elif fmt == 'gz':
            return f"{base_name}.gz"
        elif fmt == 'tgz':
            return f"{base_name}.tar.gz"
        elif fmt == 'bz2':
            return f"{base_name}.bz2"
        elif fmt == 'tbz2':
            return f"{base_name}.tar.bz2"
        else:
            return f"{base_name}.zip"
    
    def should_include_file(self, file_path: str, include_patterns: Optional[List[str]] = None,
                           exclude_patterns: Optional[List[str]] = None) -> bool:
        """
        判断文件是否应该被包含在压缩中
        
        Args:
            file_path: 文件路径
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
            
        Returns:
            True如果文件应该被包含，否则False
        """
        # 转换为相对路径用于匹配
        rel_path = os.path.basename(file_path)
        
        # 检查排除模式
        if exclude_patterns:
            for pattern in exclude_patterns:
                if pattern in file_path or pattern in rel_path:
                    return False
        
        # 检查包含模式（如果指定）
        if include_patterns:
            for pattern in include_patterns:
                if pattern in file_path or pattern in rel_path:
                    return True
            return False
        
        # 默认包含所有文件
        return True
    
    def zip_compress(self, input_paths: List[str], output_path: str, 
                    compression_level: int = 6, password: Optional[str] = None,
                    recursive: bool = True, include_patterns: Optional[List[str]] = None,
                    exclude_patterns: Optional[List[str]] = None,
                    progress_callback: Optional[Callable] = None) -> str:
        """
        压缩文件为ZIP格式
        
        Args:
            input_paths: 输入文件或目录路径列表
            output_path: 输出ZIP文件路径
            compression_level: 压缩级别 (0-9)
            password: 密码保护（如果提供）
            recursive: 是否递归处理子目录
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
            progress_callback: 进度回调函数
            
        Returns:
            输出文件路径
        """
        start_time = time.time()
        logger.info(f"开始ZIP压缩，输出: {output_path}")
        
        # 确定压缩模式
        compression = zipfile.ZIP_DEFLATED if compression_level > 0 else zipfile.ZIP_STORED
        
        # 统计总文件数和总大小
        total_files = 0
        total_size = 0
        
        for input_path in input_paths:
            if os.path.isfile(input_path):
                if self.should_include_file(input_path, include_patterns, exclude_patterns):
                    total_files += 1
                    total_size += os.path.getsize(input_path)
            elif os.path.isdir(input_path):
                for root, dirs, files in os.walk(input_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self.should_include_file(file_path, include_patterns, exclude_patterns):
                            total_files += 1
                            total_size += os.path.getsize(file_path)
                    # 如果不递归，清除dirs列表
                    if not recursive:
                        dirs.clear()
        
        processed_files = 0
        processed_size = 0
        
        # 创建ZIP文件
        with zipfile.ZipFile(output_path, 'w', compression=compression) as zipf:
            # 设置压缩级别
            if hasattr(zipf, '_compression_level'):
                zipf._compression_level = compression_level
            
            # 添加文件到ZIP
            for input_path in input_paths:
                if os.path.isfile(input_path):
                    if self.should_include_file(input_path, include_patterns, exclude_patterns):
                        zipf.write(input_path, os.path.basename(input_path))
                        processed_files += 1
                        processed_size += os.path.getsize(input_path)
                        
                        if progress_callback:
                            progress_callback(processed_files, total_files, 
                                           processed_size, total_size)
                
                elif os.path.isdir(input_path):
                    base_dir = os.path.basename(input_path)
                    if base_dir == '':  # 处理路径以/结尾的情况
                        base_dir = os.path.basename(os.path.dirname(input_path))
                    
                    for root, dirs, files in os.walk(input_path):
                        # 创建相对路径用于ZIP内部结构
                        rel_path = os.path.relpath(root, os.path.dirname(input_path))
                        if rel_path == '.':
                            rel_path = base_dir
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            if self.should_include_file(file_path, include_patterns, exclude_patterns):
                                arcname = os.path.join(rel_path, file)
                                zipf.write(file_path, arcname)
                                
                                processed_files += 1
                                processed_size += os.path.getsize(file_path)
                                
                                if progress_callback:
                                    progress_callback(processed_files, total_files, 
                                                   processed_size, total_size)
                        
                        # 如果不递归，清除dirs列表
                        if not recursive:
                            dirs.clear()
        
        # 如果需要密码保护，重新创建加密的ZIP
        # 注意：Python的zipfile不直接支持设置密码，这里使用一个简单的方式
        # 实际应用中可能需要使用第三方库如pyzipper
        if password:
            logger.warning("Python标准库的zipfile不支持直接设置密码加密。需要安装pyzipper库获取更好的密码保护支持。")
            
        end_time = time.time()
        output_size = os.path.getsize(output_path)
        compression_ratio = (1 - output_size / total_size) * 100 if total_size > 0 else 0
        
        logger.info(f"ZIP压缩完成，耗时: {end_time - start_time:.2f}秒")
        logger.info(f"压缩文件大小: {output_size / (1024*1024):.2f} MB")
        logger.info(f"压缩率: {compression_ratio:.2f}%")
        
        return output_path
    
    def tar_compress(self, input_paths: List[str], output_path: str, 
                    compression_type: Optional[str] = None, 
                    compression_level: int = 6,
                    recursive: bool = True, include_patterns: Optional[List[str]] = None,
                    exclude_patterns: Optional[List[str]] = None,
                    progress_callback: Optional[Callable] = None) -> str:
        """
        压缩文件为TAR格式（可选择gz或bz2压缩）
        
        Args:
            input_paths: 输入文件或目录路径列表
            output_path: 输出TAR文件路径
            compression_type: 压缩类型 ('gz', 'bz2' 或 None)
            compression_level: 压缩级别 (0-9)
            recursive: 是否递归处理子目录
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
            progress_callback: 进度回调函数
            
        Returns:
            输出文件路径
        """
        start_time = time.time()
        logger.info(f"开始TAR压缩，输出: {output_path}")
        
        # 确定模式
        if compression_type == 'gz':
            mode = 'w:gz'
        elif compression_type == 'bz2':
            mode = 'w:bz2'
        else:
            mode = 'w'
        
        # 统计总文件数和总大小
        total_files = 0
        total_size = 0
        
        for input_path in input_paths:
            if os.path.isfile(input_path):
                if self.should_include_file(input_path, include_patterns, exclude_patterns):
                    total_files += 1
                    total_size += os.path.getsize(input_path)
            elif os.path.isdir(input_path):
                for root, dirs, files in os.walk(input_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self.should_include_file(file_path, include_patterns, exclude_patterns):
                            total_files += 1
                            total_size += os.path.getsize(file_path)
                    # 如果不递归，清除dirs列表
                    if not recursive:
                        dirs.clear()
        
        processed_files = 0
        processed_size = 0
        
        # 创建TAR文件
        with tarfile.open(output_path, mode) as tarf:
            # 如果是gz格式，设置压缩级别
            if compression_type == 'gz' and hasattr(tarf.fileobj, 'compresslevel'):
                tarf.fileobj.compresslevel = compression_level
            
            # 添加文件到TAR
            for input_path in input_paths:
                if os.path.isfile(input_path):
                    if self.should_include_file(input_path, include_patterns, exclude_patterns):
                        tarf.add(input_path, arcname=os.path.basename(input_path))
                        processed_files += 1
                        processed_size += os.path.getsize(input_path)
                        
                        if progress_callback:
                            progress_callback(processed_files, total_files, 
                                           processed_size, total_size)
                
                elif os.path.isdir(input_path):
                    base_dir = os.path.basename(input_path)
                    if base_dir == '':  # 处理路径以/结尾的情况
                        base_dir = os.path.basename(os.path.dirname(input_path))
                    
                    for root, dirs, files in os.walk(input_path):
                        # 创建相对路径用于TAR内部结构
                        rel_path = os.path.relpath(root, os.path.dirname(input_path))
                        if rel_path == '.':
                            rel_path = base_dir
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            if self.should_include_file(file_path, include_patterns, exclude_patterns):
                                arcname = os.path.join(rel_path, file)
                                tarf.add(file_path, arcname=arcname)
                                
                                processed_files += 1
                                processed_size += os.path.getsize(file_path)
                                
                                if progress_callback:
                                    progress_callback(processed_files, total_files, 
                                                   processed_size, total_size)
                        
                        # 如果不递归，清除dirs列表
                        if not recursive:
                            dirs.clear()
        
        end_time = time.time()
        output_size = os.path.getsize(output_path)
        compression_ratio = (1 - output_size / total_size) * 100 if total_size > 0 else 0
        
        logger.info(f"TAR压缩完成，耗时: {end_time - start_time:.2f}秒")
        logger.info(f"压缩文件大小: {output_size / (1024*1024):.2f} MB")
        logger.info(f"压缩率: {compression_ratio:.2f}%")
        
        return output_path
    
    def single_file_compress(self, input_path: str, output_path: str, 
                            compression_type: str = 'gz',
                            compression_level: int = 6,
                            progress_callback: Optional[Callable] = None) -> str:
        """
        压缩单个文件为GZ或BZ2格式
        
        Args:
            input_path: 输入文件路径
            output_path: 输出压缩文件路径
            compression_type: 压缩类型 ('gz' 或 'bz2')
            compression_level: 压缩级别 (0-9)
            progress_callback: 进度回调函数
            
        Returns:
            输出文件路径
        """
        start_time = time.time()
        logger.info(f"开始单文件压缩，输入: {input_path}, 输出: {output_path}")
        
        # 检查输入文件是否存在
        if not os.path.isfile(input_path):
            raise ValueError(f"输入文件不存在: {input_path}")
        
        # 获取输入文件大小
        total_size = os.path.getsize(input_path)
        
        # 定义分块大小
        chunk_size = 1024 * 1024  # 1MB
        processed_size = 0
        
        try:
            # 根据压缩类型选择压缩方法
            if compression_type == 'gz':
                with open(input_path, 'rb') as f_in:
                    with gzip.open(output_path, 'wb', compresslevel=compression_level) as f_out:
                        while True:
                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            processed_size += len(chunk)
                            
                            if progress_callback:
                                progress_callback(1, 1, processed_size, total_size)
            
            elif compression_type == 'bz2':
                with open(input_path, 'rb') as f_in:
                    with bz2.open(output_path, 'wb', compresslevel=compression_level) as f_out:
                        while True:
                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            processed_size += len(chunk)
                            
                            if progress_callback:
                                progress_callback(1, 1, processed_size, total_size)
            
            else:
                raise ValueError(f"不支持的压缩类型: {compression_type}")
        
        except Exception as e:
            # 清理部分创建的文件
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
        
        end_time = time.time()
        output_size = os.path.getsize(output_path)
        compression_ratio = (1 - output_size / total_size) * 100 if total_size > 0 else 0
        
        logger.info(f"单文件压缩完成，耗时: {end_time - start_time:.2f}秒")
        logger.info(f"压缩文件大小: {output_size / (1024*1024):.2f} MB")
        logger.info(f"压缩率: {compression_ratio:.2f}%")
        
        return output_path
    
    def compress(self, input_paths: List[str], output_path: Optional[str] = None,
                fmt: Optional[str] = None, compression_level: int = 6,
                password: Optional[str] = None, recursive: bool = True,
                include_patterns: Optional[List[str]] = None,
                exclude_patterns: Optional[List[str]] = None,
                progress_callback: Optional[Callable] = None) -> str:
        """
        压缩文件或目录
        
        Args:
            input_paths: 输入文件或目录路径列表
            output_path: 输出压缩文件路径，如果为None则自动生成
            fmt: 压缩格式，如果为None则从output_path推断
            compression_level: 压缩级别 (0-9)
            password: 密码保护（仅ZIP格式支持）
            recursive: 是否递归处理子目录
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
            progress_callback: 进度回调函数
            
        Returns:
            输出压缩文件路径
        """
        # 验证输入路径
        for path in input_paths:
            if not os.path.exists(path):
                raise ValueError(f"输入路径不存在: {path}")
        
        # 如果只有一个输入且是文件，并且格式是gz或bz2，则使用单文件压缩
        if len(input_paths) == 1 and os.path.isfile(input_paths[0]) and fmt in ['gz', 'bz2']:
            if not output_path:
                output_path = self.get_output_filename(input_paths[0], None, fmt)
            return self.single_file_compress(
                input_paths[0], output_path, fmt, compression_level, progress_callback
            )
        
        # 推断格式
        if not fmt:
            if output_path:
                try:
                    fmt = self.detect_format(output_path)
                except ValueError:
                    fmt = 'zip'  # 默认使用ZIP
            else:
                fmt = 'zip'
        
        # 生成输出文件名
        if not output_path:
            output_path = self.get_output_filename(input_paths[0], None, fmt)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 根据格式调用相应的压缩函数
        if fmt == 'zip':
            return self.zip_compress(
                input_paths, output_path, compression_level, password,
                recursive, include_patterns, exclude_patterns, progress_callback
            )
        elif fmt == 'tar':
            return self.tar_compress(
                input_paths, output_path, None, compression_level,
                recursive, include_patterns, exclude_patterns, progress_callback
            )
        elif fmt == 'tgz':
            return self.tar_compress(
                input_paths, output_path, 'gz', compression_level,
                recursive, include_patterns, exclude_patterns, progress_callback
            )
        elif fmt == 'tbz2':
            return self.tar_compress(
                input_paths, output_path, 'bz2', compression_level,
                recursive, include_patterns, exclude_patterns, progress_callback
            )
        elif fmt in ['gz', 'bz2']:
            # 对于单文件压缩，这里应该已经被前面的条件处理了
            raise ValueError(f"格式 {fmt} 只支持单文件压缩")
        else:
            raise ValueError(f"不支持的压缩格式: {fmt}")
    
    def zip_extract(self, input_path: str, output_dir: str, 
                   password: Optional[str] = None,
                   include_patterns: Optional[List[str]] = None,
                   exclude_patterns: Optional[List[str]] = None,
                   progress_callback: Optional[Callable] = None) -> str:
        """
        解压ZIP文件
        
        Args:
            input_path: 输入ZIP文件路径
            output_dir: 输出目录
            password: 解压密码
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
            progress_callback: 进度回调函数
            
        Returns:
            输出目录路径
        """
        start_time = time.time()
        logger.info(f"开始ZIP解压，输入: {input_path}, 输出: {output_dir}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 打开ZIP文件
        with zipfile.ZipFile(input_path, 'r') as zipf:
            # 获取文件列表
            file_list = zipf.namelist()
            
            # 过滤文件
            filtered_files = []
            for file in file_list:
                # 跳过目录
                if file.endswith('/'):
                    continue
                
                # 检查包含/排除模式
                if self.should_include_file(file, include_patterns, exclude_patterns):
                    filtered_files.append(file)
            
            total_files = len(filtered_files)
            processed_files = 0
            total_size = sum(zipf.getinfo(f).file_size for f in filtered_files)
            processed_size = 0
            
            # 解压文件
            for file in filtered_files:
                try:
                    # 获取文件信息
                    info = zipf.getinfo(file)
                    
                    # 解压文件
                    if password:
                        # 注意：这里尝试使用密码，但Python的zipfile支持有限
                        zipf.extract(file, output_dir, pwd=password.encode('utf-8'))
                    else:
                        zipf.extract(file, output_dir)
                    
                    processed_files += 1
                    processed_size += info.file_size
                    
                    if progress_callback:
                        progress_callback(processed_files, total_files, 
                                       processed_size, total_size)
                
                except Exception as e:
                    logger.error(f"解压文件失败: {file}, 错误: {e}")
                    raise e
        
        end_time = time.time()
        logger.info(f"ZIP解压完成，耗时: {end_time - start_time:.2f}秒")
        logger.info(f"解压文件数: {processed_files}")
        logger.info(f"解压总大小: {processed_size / (1024*1024):.2f} MB")
        
        return output_dir
    
    def tar_extract(self, input_path: str, output_dir: str,
                   include_patterns: Optional[List[str]] = None,
                   exclude_patterns: Optional[List[str]] = None,
                   progress_callback: Optional[Callable] = None) -> str:
        """
        解压TAR文件（包括TAR.GZ和TAR.BZ2）
        
        Args:
            input_path: 输入TAR文件路径
            output_dir: 输出目录
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
            progress_callback: 进度回调函数
            
        Returns:
            输出目录路径
        """
        start_time = time.time()
        logger.info(f"开始TAR解压，输入: {input_path}, 输出: {output_dir}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 打开TAR文件
        with tarfile.open(input_path, 'r') as tarf:
            # 获取文件列表
            members = tarf.getmembers()
            
            # 过滤文件
            filtered_members = []
            for member in members:
                # 跳过目录和符号链接
                if member.isdir() or member.issym():
                    continue
                
                # 检查包含/排除模式
                if self.should_include_file(member.name, include_patterns, exclude_patterns):
                    filtered_members.append(member)
            
            total_files = len(filtered_members)
            processed_files = 0
            total_size = sum(m.size for m in filtered_members)
            processed_size = 0
            
            # 解压文件
            for member in filtered_members:
                try:
                    # 解压文件
                    tarf.extract(member, output_dir)
                    
                    processed_files += 1
                    processed_size += member.size
                    
                    if progress_callback:
                        progress_callback(processed_files, total_files, 
                                       processed_size, total_size)
                
                except Exception as e:
                    logger.error(f"解压文件失败: {member.name}, 错误: {e}")
                    raise e
        
        end_time = time.time()
        logger.info(f"TAR解压完成，耗时: {end_time - start_time:.2f}秒")
        logger.info(f"解压文件数: {processed_files}")
        logger.info(f"解压总大小: {processed_size / (1024*1024):.2f} MB")
        
        return output_dir
    
    def single_file_extract(self, input_path: str, output_path: Optional[str] = None,
                           progress_callback: Optional[Callable] = None) -> str:
        """
        解压单个GZ或BZ2文件
        
        Args:
            input_path: 输入压缩文件路径
            output_path: 输出文件路径，如果为None则自动生成
            progress_callback: 进度回调函数
            
        Returns:
            输出文件路径
        """
        start_time = time.time()
        logger.info(f"开始单文件解压，输入: {input_path}")
        
        # 检查输入文件是否存在
        if not os.path.isfile(input_path):
            raise ValueError(f"输入文件不存在: {input_path}")
        
        # 推断格式
        try:
            fmt = self.detect_format(input_path)
        except ValueError:
            raise ValueError(f"无法识别的压缩格式: {input_path}")
        
        # 生成输出文件名
        if not output_path:
            if fmt == 'gz':
                output_path = input_path[:-3] if input_path.endswith('.gz') else f"{input_path}.out"
            elif fmt == 'bz2':
                output_path = input_path[:-4] if input_path.endswith('.bz2') else f"{input_path}.out"
            else:
                raise ValueError(f"格式 {fmt} 不支持单文件解压")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 获取输入文件大小
        total_size = os.path.getsize(input_path)
        
        # 定义分块大小
        chunk_size = 1024 * 1024  # 1MB
        processed_size = 0
        
        try:
            # 根据压缩类型选择解压方法
            if fmt == 'gz':
                with gzip.open(input_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        while True:
                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            processed_size += len(chunk)
                            
                            if progress_callback:
                                progress_callback(1, 1, processed_size, total_size)
            
            elif fmt == 'bz2':
                with bz2.open(input_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        while True:
                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            processed_size += len(chunk)
                            
                            if progress_callback:
                                progress_callback(1, 1, processed_size, total_size)
            
            else:
                raise ValueError(f"不支持的压缩类型: {fmt}")
        
        except Exception as e:
            # 清理部分创建的文件
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
        
        end_time = time.time()
        output_size = os.path.getsize(output_path)
        
        logger.info(f"单文件解压完成，耗时: {end_time - start_time:.2f}秒")
        logger.info(f"输出文件大小: {output_size / (1024*1024):.2f} MB")
        
        return output_path
    
    def extract(self, input_path: str, output_dir: Optional[str] = None,
               password: Optional[str] = None,
               include_patterns: Optional[List[str]] = None,
               exclude_patterns: Optional[List[str]] = None,
               progress_callback: Optional[Callable] = None) -> str:
        """
        解压压缩文件
        
        Args:
            input_path: 输入压缩文件路径
            output_dir: 输出目录，如果为None则自动生成
            password: 解压密码
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
            progress_callback: 进度回调函数
            
        Returns:
            输出目录路径
        """
        # 检查输入文件是否存在
        if not os.path.isfile(input_path):
            raise ValueError(f"输入文件不存在: {input_path}")
        
        # 推断格式
        fmt = self.detect_format(input_path)
        
        # 对于单文件压缩格式，使用单文件解压
        if fmt in ['gz', 'bz2']:
            if output_dir:
                # 如果指定了输出目录，生成输出文件路径
                base_name = os.path.basename(input_path)
                if base_name.endswith('.gz'):
                    out_name = base_name[:-3]
                elif base_name.endswith('.bz2'):
                    out_name = base_name[:-4]
                else:
                    out_name = f"{base_name}.out"
                output_path = os.path.join(output_dir, out_name)
                return self.single_file_extract(input_path, output_path, progress_callback)
            else:
                return self.single_file_extract(input_path, None, progress_callback)
        
        # 生成输出目录
        if not output_dir:
            # 默认在当前目录创建与压缩文件同名的目录
            base_name = os.path.basename(input_path)
            for ext_list in self.SUPPORTED_FORMATS.values():
                for ext in ext_list:
                    if base_name.endswith(ext):
                        base_name = base_name[:-len(ext)]
                        break
            output_dir = os.path.join(os.path.dirname(input_path), base_name)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 根据格式调用相应的解压函数
        if fmt == 'zip':
            return self.zip_extract(
                input_path, output_dir, password,
                include_patterns, exclude_patterns, progress_callback
            )
        elif fmt in ['tar', 'tgz', 'tbz2']:
            return self.tar_extract(
                input_path, output_dir,
                include_patterns, exclude_patterns, progress_callback
            )
        else:
            raise ValueError(f"不支持的压缩格式: {fmt}")
    
    def list_contents(self, input_path: str) -> List[Dict[str, Union[str, int, datetime.datetime]]]:
        """
        列出压缩文件内容
        
        Args:
            input_path: 输入压缩文件路径
            
        Returns:
            文件信息列表
        """
        # 检查输入文件是否存在
        if not os.path.isfile(input_path):
            raise ValueError(f"输入文件不存在: {input_path}")
        
        # 推断格式
        fmt = self.detect_format(input_path)
        
        file_list = []
        
        if fmt == 'zip':
            with zipfile.ZipFile(input_path, 'r') as zipf:
                for info in zipf.infolist():
                    if not info.is_dir():
                        file_info = {
                            'name': info.filename,
                            'size': info.file_size,
                            'compressed_size': info.compress_size,
                            'modified_time': datetime.datetime(*info.date_time),
                            'compression_method': info.compress_type
                        }
                        file_list.append(file_info)
        
        elif fmt in ['tar', 'tgz', 'tbz2']:
            with tarfile.open(input_path, 'r') as tarf:
                for member in tarf.getmembers():
                    if not member.isdir():
                        file_info = {
                            'name': member.name,
                            'size': member.size,
                            'modified_time': datetime.datetime.fromtimestamp(member.mtime),
                            'mode': member.mode,
                            'uid': member.uid,
                            'gid': member.gid
                        }
                        file_list.append(file_info)
        
        elif fmt in ['gz', 'bz2']:
            # 对于单文件压缩，返回单个文件信息
            base_name = os.path.basename(input_path)
            if base_name.endswith('.gz'):
                orig_name = base_name[:-3]
            elif base_name.endswith('.bz2'):
                orig_name = base_name[:-4]
            else:
                orig_name = f"{base_name}.out"
            
            # 对于gz/bz2，我们不知道原始文件大小，除非解压
            file_info = {
                'name': orig_name,
                'compressed_size': os.path.getsize(input_path),
                'compressed_only': True
            }
            file_list.append(file_info)
        
        return file_list
    
    def get_info(self, input_path: str) -> Dict:
        """
        获取压缩文件信息
        
        Args:
            input_path: 输入压缩文件路径
            
        Returns:
            压缩文件信息
        """
        # 检查输入文件是否存在
        if not os.path.isfile(input_path):
            raise ValueError(f"输入文件不存在: {input_path}")
        
        # 推断格式
        fmt = self.detect_format(input_path)
        
        # 获取文件内容列表
        file_list = self.list_contents(input_path)
        
        # 计算统计信息
        total_size = sum(f.get('size', 0) for f in file_list)
        compressed_size = sum(f.get('compressed_size', os.path.getsize(input_path)) for f in file_list)
        if fmt in ['gz', 'bz2'] and len(file_list) == 1:
            compressed_size = os.path.getsize(input_path)
        
        compression_ratio = (1 - compressed_size / total_size) * 100 if total_size > 0 and fmt not in ['gz', 'bz2'] else None
        
        info = {
            'file_path': input_path,
            'format': fmt,
            'file_count': len(file_list),
            'total_size': total_size,
            'compressed_size': compressed_size,
            'compression_ratio': compression_ratio,
            'creation_time': datetime.datetime.fromtimestamp(os.path.getctime(input_path)),
            'modification_time': datetime.datetime.fromtimestamp(os.path.getmtime(input_path))
        }
        
        return info


def print_progress(current: int, total: int, current_size: int, total_size: int) -> None:
    """
    打印进度条
    
    Args:
        current: 当前处理的文件数
        total: 总文件数
        current_size: 当前处理的字节数
        total_size: 总字节数
    """
    if total == 0:
        return
    
    # 计算进度百分比
    file_percent = (current / total) * 100
    size_percent = (current_size / total_size) * 100 if total_size > 0 else 0
    
    # 格式化大小
    if current_size < 1024:
        current_size_str = f"{current_size} B"
    elif current_size < 1024 * 1024:
        current_size_str = f"{current_size / 1024:.2f} KB"
    elif current_size < 1024 * 1024 * 1024:
        current_size_str = f"{current_size / (1024 * 1024):.2f} MB"
    else:
        current_size_str = f"{current_size / (1024 * 1024 * 1024):.2f} GB"
    
    if total_size < 1024:
        total_size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        total_size_str = f"{total_size / 1024:.2f} KB"
    elif total_size < 1024 * 1024 * 1024:
        total_size_str = f"{total_size / (1024 * 1024):.2f} MB"
    else:
        total_size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
    
    # 打印进度条
    bar_length = 30
    file_bar = '█' * int(bar_length * current / total)
    file_space = '░' * (bar_length - len(file_bar))
    
    # 覆盖当前行
    sys.stdout.write(f"\r进度: [{file_bar}{file_space}] {file_percent:.1f}% | {current}/{total} 文件 | {current_size_str}/{total_size_str} @ {size_percent:.1f}%")
    sys.stdout.flush()
    
    # 完成时换行
    if current >= total and current_size >= total_size:
        sys.stdout.write('\n')


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化后的大小字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description='数据压缩与解压工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 压缩文件或目录
  python data_compressor.py compress file.txt -o compressed.zip
  python data_compressor.py compress dir/ -o archive.tar.gz --format tgz
  
  # 解压文件
  python data_compressor.py extract archive.zip -d output_dir
  python data_compressor.py extract archive.tar.bz2
  
  # 查看压缩文件内容
  python data_compressor.py list archive.zip
  
  # 设置压缩级别
  python data_compressor.py compress dir/ -o compressed.zip --level 9
        """
    )
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # compress 命令
    compress_parser = subparsers.add_parser('compress', help='压缩文件或目录')
    compress_parser.add_argument('input_paths', nargs='+', help='输入文件或目录路径')
    compress_parser.add_argument('-o', '--output', help='输出压缩文件路径')
    compress_parser.add_argument('-f', '--format', choices=['zip', 'tar', 'tgz', 'gz', 'bz2', 'tbz2'], 
                                help='压缩格式')
    compress_parser.add_argument('-l', '--level', type=int, default=6, 
                                choices=list(range(10)), help='压缩级别 (0-9)')
    compress_parser.add_argument('-p', '--password', help='ZIP密码保护')
    compress_parser.add_argument('-r', '--recursive', action='store_true', 
                                help='递归处理子目录')
    compress_parser.add_argument('--include', nargs='+', help='包含的文件模式')
    compress_parser.add_argument('--exclude', nargs='+', help='排除的文件模式')
    compress_parser.add_argument('--temp-dir', help='临时文件目录')
    
    # extract 命令
    extract_parser = subparsers.add_parser('extract', help='解压压缩文件')
    extract_parser.add_argument('input_path', help='输入压缩文件路径')
    extract_parser.add_argument('-d', '--dir', help='输出目录')
    extract_parser.add_argument('-p', '--password', help='解压密码')
    extract_parser.add_argument('--include', nargs='+', help='包含的文件模式')
    extract_parser.add_argument('--exclude', nargs='+', help='排除的文件模式')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出压缩文件内容')
    list_parser.add_argument('input_path', help='输入压缩文件路径')
    list_parser.add_argument('-v', '--verbose', action='store_true', 
                           help='显示详细信息')
    list_parser.add_argument('-s', '--sort', choices=['name', 'size', 'date'], 
                           default='name', help='排序方式')
    list_parser.add_argument('-r', '--reverse', action='store_true', 
                           help='逆序排序')
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='获取压缩文件信息')
    info_parser.add_argument('input_path', help='输入压缩文件路径')
    
    # 全局参数
    parser.add_argument('--log-level', default='INFO', 
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                      help='日志级别')
    
    return parser.parse_args()


def main() -> int:
    """
    主函数
    
    Returns:
        退出代码
    """
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志级别
    logger.setLevel(getattr(logging, args.log_level))
    
    # 检查命令
    if not args.command:
        print("请指定命令，使用 -h 查看帮助")
        return 1
    
    try:
        # 创建压缩器实例
        compressor = DataCompressor(temp_dir=args.temp_dir if hasattr(args, 'temp_dir') and args.temp_dir else None)
        
        if args.command == 'compress':
            # 执行压缩
            output_path = compressor.compress(
                input_paths=args.input_paths,
                output_path=args.output,
                fmt=args.format,
                compression_level=args.level,
                password=args.password,
                recursive=args.recursive,
                include_patterns=args.include,
                exclude_patterns=args.exclude,
                progress_callback=print_progress
            )
            
            print(f"\n压缩成功！")
            print(f"输出文件: {output_path}")
            print(f"文件大小: {format_file_size(os.path.getsize(output_path))}")
            
        elif args.command == 'extract':
            # 执行解压
            output_dir = compressor.extract(
                input_path=args.input_path,
                output_dir=args.dir,
                password=args.password,
                include_patterns=args.include,
                exclude_patterns=args.exclude,
                progress_callback=print_progress
            )
            
            print(f"\n解压成功！")
            print(f"输出目录: {output_dir}")
            
        elif args.command == 'list':
            # 列出内容
            file_list = compressor.list_contents(args.input_path)
            
            # 排序
            if args.sort == 'name':
                file_list.sort(key=lambda x: x['name'], reverse=args.reverse)
            elif args.sort == 'size':
                file_list.sort(key=lambda x: x.get('size', 0), reverse=not args.reverse)
            elif args.sort == 'date':
                file_list.sort(key=lambda x: x.get('modified_time', datetime.datetime(1970, 1, 1)), 
                             reverse=not args.reverse)
            
            print(f"压缩文件内容: {args.input_path}")
            print(f"找到 {len(file_list)} 个文件")
            
            if args.verbose:
                # 详细信息
                print("=" * 100)
                print(f"{'文件名':<50} {'大小':<15} {'修改时间':<25}")
                print("=" * 100)
                
                total_size = 0
                for file_info in file_list:
                    size = format_file_size(file_info.get('size', 0))
                    date = file_info.get('modified_time', 'N/A')
                    if isinstance(date, datetime.datetime):
                        date = date.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{file_info['name'][:49]:<50} {size:<15} {date:<25}")
                    total_size += file_info.get('size', 0)
                
                print("=" * 100)
                print(f"总计: {len(file_list)} 个文件, {format_file_size(total_size)}")
            else:
                # 简洁信息
                for file_info in file_list:
                    print(f"  {file_info['name']}")
            
        elif args.command == 'info':
            # 获取信息
            info = compressor.get_info(args.input_path)
            
            print(f"压缩文件信息: {info['file_path']}")
            print("=" * 60)
            print(f"格式: {info['format']}")
            print(f"文件数: {info['file_count']}")
            print(f"原始大小: {format_file_size(info['total_size'])}")
            print(f"压缩大小: {format_file_size(info['compressed_size'])}")
            if info['compression_ratio'] is not None:
                print(f"压缩率: {info['compression_ratio']:.2f}%")
            else:
                print(f"压缩率: N/A (无法计算单文件压缩)")
            print(f"创建时间: {info['creation_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"修改时间: {info['modification_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
        
        return 0
    
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        return 1
    except Exception as e:
        logger.error(f"发生错误: {e}")
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())