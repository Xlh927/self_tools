#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
哈希校验与文件去重模块（C5）

功能：
- 支持多种哈希算法计算文件哈希值（MD5、SHA1、SHA256、SHA512等）
- 文件去重功能（根据内容相似度识别重复文件）
- 支持单文件哈希计算和批量文件哈希计算
- 支持大文件分块处理
- 支持哈希值批量导出（JSON、CSV、TXT格式）
- 支持自定义哈希值存储和加载
- 支持文件去重后的操作（删除、移动、硬链接等）
- 支持按文件大小、修改时间等条件过滤
- 支持重复文件报告生成

作者: AI助手
日期: 2024
"""

import os
import sys
import hashlib
import json
import csv
import shutil
import argparse
import logging
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import tempfile

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("file_hash_duplicate_detector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FileHashDuplicateDetector:
    """文件哈希与重复检测工具类"""
    
    def __init__(self):
        self.supported_algorithms = ['md5', 'sha1', 'sha256', 'sha512', 'blake2b', 'blake2s']
        self.chunk_size = 65536  # 64KB块大小
    
    def calculate_file_hash(self, file_path, algorithm='md5'):
        """
        计算单个文件的哈希值
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法名称
            
        Returns:
            str: 计算得到的哈希值
        """
        if not os.path.isfile(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
        
        if algorithm not in self.supported_algorithms:
            logger.error(f"不支持的哈希算法: {algorithm}")
            return None
        
        try:
            # 创建哈希对象
            hash_obj = hashlib.new(algorithm)
            
            # 分块读取文件计算哈希
            with open(file_path, 'rb') as f:
                while chunk := f.read(self.chunk_size):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {str(e)}")
            return None
    
    def calculate_directory_hashes(self, dir_path, algorithm='md5', recursive=True, exclude_patterns=None, 
                                 min_size=0, max_size=None, num_workers=4, filter_extensions=None):
        """
        批量计算目录中所有文件的哈希值
        
        Args:
            dir_path: 目录路径
            algorithm: 哈希算法名称
            recursive: 是否递归处理子目录
            exclude_patterns: 要排除的文件模式列表
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            num_workers: 线程池大小
            filter_extensions: 要过滤的文件扩展名列表
            
        Returns:
            dict: {文件路径: 哈希值}
        """
        if not os.path.isdir(dir_path):
            logger.error(f"目录不存在: {dir_path}")
            return {}
        
        if algorithm not in self.supported_algorithms:
            logger.error(f"不支持的哈希算法: {algorithm}")
            return {}
        
        # 收集要处理的文件列表
        file_list = []
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # 检查文件大小
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size < min_size:
                        continue
                    if max_size is not None and file_size > max_size:
                        continue
                except Exception as e:
                    logger.warning(f"无法获取文件大小 {file_path}: {str(e)}")
                    continue
                
                # 检查文件扩展名
                if filter_extensions:
                    file_ext = Path(file).suffix.lower()
                    if file_ext not in [ext.lower() for ext in filter_extensions]:
                        continue
                
                # 检查排除模式
                if exclude_patterns:
                    skip = False
                    for pattern in exclude_patterns:
                        if pattern in file_path:
                            skip = True
                            break
                    if skip:
                        continue
                
                file_list.append(file_path)
            
            # 是否递归处理子目录
            if not recursive:
                break
        
        total_files = len(file_list)
        logger.info(f"找到 {total_files} 个符合条件的文件需要计算哈希")
        
        # 使用线程池并行计算哈希
        results = {}
        processed_files = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # 提交所有任务
            future_to_file = {executor.submit(self.calculate_file_hash, file_path, algorithm): file_path 
                             for file_path in file_list}
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    file_hash = future.result()
                    if file_hash:
                        results[file_path] = file_hash
                except Exception as e:
                    logger.error(f"处理文件时出错 {file_path}: {str(e)}")
                
                # 更新进度
                processed_files += 1
                self._show_progress(processed_files, total_files, start_time)
        
        logger.info(f"哈希计算完成: 成功 {len(results)}/{total_files}")
        return results
    
    def find_duplicate_files(self, hash_dict, min_duplicates=2):
        """
        根据哈希值查找重复文件
        
        Args:
            hash_dict: {文件路径: 哈希值} 的字典
            min_duplicates: 最小重复次数
            
        Returns:
            dict: {哈希值: [重复文件路径列表]}
        """
        # 按哈希值分组
        hash_to_files = defaultdict(list)
        for file_path, file_hash in hash_dict.items():
            if file_hash:
                hash_to_files[file_hash].append(file_path)
        
        # 过滤出重复文件
        duplicate_files = {}
        for file_hash, files in hash_to_files.items():
            if len(files) >= min_duplicates:
                duplicate_files[file_hash] = sorted(files)
        
        logger.info(f"找到 {len(duplicate_files)} 组重复文件")
        return duplicate_files
    
    def export_hash_results(self, hash_dict, output_file, format='json'):
        """
        导出哈希计算结果
        
        Args:
            hash_dict: {文件路径: 哈希值} 的字典
            output_file: 输出文件路径
            format: 输出格式 ('json', 'csv', 'txt')
            
        Returns:
            bool: 导出是否成功
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            if format.lower() == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(hash_dict, f, ensure_ascii=False, indent=2)
            
            elif format.lower() == 'csv':
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['文件路径', '哈希值'])
                    for file_path, file_hash in hash_dict.items():
                        writer.writerow([file_path, file_hash])
            
            elif format.lower() == 'txt':
                with open(output_file, 'w', encoding='utf-8') as f:
                    for file_path, file_hash in hash_dict.items():
                        f.write(f"{file_hash}  {file_path}\n")
            
            else:
                logger.error(f"不支持的导出格式: {format}")
                return False
            
            logger.info(f"哈希结果已导出到: {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"导出哈希结果失败: {str(e)}")
            return False
    
    def load_hash_results(self, input_file):
        """
        从文件加载哈希计算结果
        
        Args:
            input_file: 输入文件路径
            
        Returns:
            dict: {文件路径: 哈希值}
        """
        if not os.path.isfile(input_file):
            logger.error(f"哈希结果文件不存在: {input_file}")
            return {}
        
        try:
            file_ext = Path(input_file).suffix.lower()
            
            if file_ext == '.json':
                with open(input_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            elif file_ext == '.csv':
                hash_dict = {}
                with open(input_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # 跳过标题行
                    for row in reader:
                        if len(row) >= 2:
                            hash_dict[row[0]] = row[1]
                return hash_dict
            
            elif file_ext == '.txt':
                hash_dict = {}
                with open(input_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            # 假设格式为 "哈希值  文件路径"
                            parts = line.split(None, 1)
                            if len(parts) == 2:
                                file_hash, file_path = parts
                                hash_dict[file_path] = file_hash
                return hash_dict
            
            else:
                logger.error(f"不支持的文件格式: {file_ext}")
                return {}
        
        except Exception as e:
            logger.error(f"加载哈希结果失败: {str(e)}")
            return {}
    
    def process_duplicate_files(self, duplicate_files, action='report', keep_strategy='newest', 
                              output_dir=None, dry_run=False):
        """
        处理重复文件
        
        Args:
            duplicate_files: {哈希值: [重复文件路径列表]} 的字典
            action: 处理动作 ('report', 'delete', 'move', 'link')
            keep_strategy: 保留策略 ('newest', 'oldest', 'smallest', 'largest', 'first', 'last')
            output_dir: 移动文件的目标目录
            dry_run: 是否只模拟操作而不实际执行
            
        Returns:
            dict: {哈希值: (保留的文件, 处理的文件列表)}
        """
        results = {}
        total_processed = 0
        total_duplicate_groups = len(duplicate_files)
        
        for file_hash, file_list in duplicate_files.items():
            # 选择要保留的文件
            keep_file = self._select_file_to_keep(file_list, keep_strategy)
            
            # 确定要处理的文件
            files_to_process = [f for f in file_list if f != keep_file]
            
            # 处理文件
            processed_files = []
            for file_path in files_to_process:
                if action == 'delete':
                    if not dry_run:
                        try:
                            os.remove(file_path)
                            logger.info(f"已删除重复文件: {file_path}")
                        except Exception as e:
                            logger.error(f"删除文件失败 {file_path}: {str(e)}")
                            continue
                    else:
                        logger.info(f"[模拟] 将删除重复文件: {file_path}")
                    processed_files.append(file_path)
                
                elif action == 'move':
                    if not output_dir:
                        logger.error("移动操作需要指定输出目录")
                        continue
                    
                    # 创建目标目录（如果不存在）
                    if not dry_run:
                        os.makedirs(output_dir, exist_ok=True)
                    
                    # 生成目标文件名
                    base_name = os.path.basename(file_path)
                    target_path = os.path.join(output_dir, base_name)
                    
                    # 如果文件名冲突，添加数字后缀
                    counter = 1
                    while os.path.exists(target_path):
                        name, ext = os.path.splitext(base_name)
                        target_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    if not dry_run:
                        try:
                            shutil.move(file_path, target_path)
                            logger.info(f"已移动重复文件: {file_path} -> {target_path}")
                        except Exception as e:
                            logger.error(f"移动文件失败 {file_path}: {str(e)}")
                            continue
                    else:
                        logger.info(f"[模拟] 将移动重复文件: {file_path} -> {target_path}")
                    processed_files.append(file_path)
                
                elif action == 'link':
                    # 创建硬链接
                    if not dry_run:
                        try:
                            # 确保目标文件不存在
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            os.link(keep_file, file_path)
                            logger.info(f"已创建硬链接: {file_path} -> {keep_file}")
                        except Exception as e:
                            logger.error(f"创建硬链接失败 {file_path}: {str(e)}")
                            continue
                    else:
                        logger.info(f"[模拟] 将创建硬链接: {file_path} -> {keep_file}")
                    processed_files.append(file_path)
                
                elif action == 'report':
                    # 仅报告模式
                    logger.info(f"重复文件: {file_path} (保留: {keep_file})")
                    processed_files.append(file_path)
                
                else:
                    logger.error(f"不支持的操作: {action}")
                    continue
            
            results[file_hash] = (keep_file, processed_files)
            total_processed += len(processed_files)
            
            # 显示进度
            progress = (len(results) / total_duplicate_groups) * 100
            logger.info(f"处理进度: {progress:.1f}% - 已处理 {len(results)}/{total_duplicate_groups} 组")
        
        logger.info(f"重复文件处理完成: 共处理 {total_processed} 个重复文件")
        return results
    
    def generate_duplicate_report(self, duplicate_files, output_file=None):
        """
        生成重复文件报告
        
        Args:
            duplicate_files: {哈希值: [重复文件路径列表]} 的字典
            output_file: 输出文件路径（如果为None则只输出到控制台）
            
        Returns:
            bool: 报告生成是否成功
        """
        report_lines = []
        
        # 报告标题
        report_lines.append("===== 重复文件检测报告 =====")
        report_lines.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"检测到的重复文件组数量: {len(duplicate_files)}")
        
        total_duplicate_files = sum(len(files) for files in duplicate_files.values())
        total_unique_files = len(duplicate_files)
        potential_space_saved = 0
        
        # 详细列出每组重复文件
        report_lines.append("\n详细信息:")
        report_lines.append("-" * 80)
        
        group_num = 1
        for file_hash, file_list in duplicate_files.items():
            report_lines.append(f"\n组 {group_num}: 哈希值 = {file_hash}")
            report_lines.append(f"包含 {len(file_list)} 个重复文件:")
            
            # 计算文件大小和总空间
            if file_list:
                first_file_size = os.path.getsize(file_list[0])
                space_saved = first_file_size * (len(file_list) - 1)
                potential_space_saved += space_saved
            
            for file_path in file_list:
                try:
                    file_size = os.path.getsize(file_path)
                    mtime = os.path.getmtime(file_path)
                    mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
                    report_lines.append(f"  - {file_path} (大小: {self._format_size(file_size)}, 修改时间: {mtime_str})")
                except Exception as e:
                    report_lines.append(f"  - {file_path} (无法获取文件信息: {str(e)})")
            
            group_num += 1
        
        # 统计信息
        report_lines.append("\n" + "=" * 80)
        report_lines.append("统计信息:")
        report_lines.append(f"- 总重复文件数量: {total_duplicate_files}")
        report_lines.append(f"- 唯一文件数量: {total_unique_files}")
        report_lines.append(f"- 潜在可节省空间: {self._format_size(potential_space_saved)}")
        report_lines.append("=" * 80)
        
        # 输出报告
        report = "\n".join(report_lines)
        
        # 输出到控制台
        logger.info("\n" + report)
        
        # 保存到文件
        if output_file:
            try:
                # 确保输出目录存在
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # 保存报告
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                logger.info(f"重复文件报告已保存到: {output_file}")
                return True
            
            except Exception as e:
                logger.error(f"保存重复文件报告失败: {str(e)}")
                return False
        
        return True
    
    def verify_file_hash(self, file_path, expected_hash, algorithm='md5'):
        """
        验证文件哈希值
        
        Args:
            file_path: 文件路径
            expected_hash: 期望的哈希值
            algorithm: 哈希算法名称
            
        Returns:
            bool: 验证是否通过
        """
        calculated_hash = self.calculate_file_hash(file_path, algorithm)
        if calculated_hash is None:
            return False
        
        is_match = calculated_hash.lower() == expected_hash.lower()
        
        if is_match:
            logger.info(f"哈希验证通过: {file_path}")
        else:
            logger.error(f"哈希验证失败: {file_path} (计算: {calculated_hash}, 期望: {expected_hash})")
        
        return is_match
    
    def _select_file_to_keep(self, file_list, strategy='newest'):
        """
        根据策略选择要保留的文件
        
        Args:
            file_list: 文件路径列表
            strategy: 保留策略
            
        Returns:
            str: 要保留的文件路径
        """
        if not file_list:
            return None
        
        if len(file_list) == 1:
            return file_list[0]
        
        try:
            if strategy == 'newest':
                # 保留最新修改的文件
                return max(file_list, key=os.path.getmtime)
            
            elif strategy == 'oldest':
                # 保留最早修改的文件
                return min(file_list, key=os.path.getmtime)
            
            elif strategy == 'smallest':
                # 保留最小的文件
                return min(file_list, key=os.path.getsize)
            
            elif strategy == 'largest':
                # 保留最大的文件
                return max(file_list, key=os.path.getsize)
            
            elif strategy == 'first':
                # 保留第一个文件
                return file_list[0]
            
            elif strategy == 'last':
                # 保留最后一个文件
                return file_list[-1]
            
            else:
                logger.error(f"不支持的保留策略: {strategy}")
                return file_list[0]
        
        except Exception as e:
            logger.error(f"选择保留文件时出错: {str(e)}")
            return file_list[0]
    
    def _format_size(self, size_bytes):
        """
        格式化文件大小显示
        
        Args:
            size_bytes: 字节大小
            
        Returns:
            str: 格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
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


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='哈希校验与文件去重工具')
    
    # 操作模式选择
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('-c', '--calculate', action='store_true', help='计算文件哈希值')
    mode_group.add_argument('-v', '--verify', action='store_true', help='验证文件哈希值')
    mode_group.add_argument('-d', '--detect', action='store_true', help='检测重复文件')
    mode_group.add_argument('-p', '--process', action='store_true', help='处理重复文件')
    mode_group.add_argument('-e', '--export', action='store_true', help='导出哈希结果')
    mode_group.add_argument('-l', '--load', action='store_true', help='加载哈希结果')
    
    # 通用参数
    parser.add_argument('-i', '--input', type=str, help='输入文件或目录路径')
    parser.add_argument('-o', '--output', type=str, help='输出文件或目录路径')
    parser.add_argument('-a', '--algorithm', type=str, default='md5', 
                      help=f'哈希算法 ({" ".join(FileHashDuplicateDetector().supported_algorithms)})')
    parser.add_argument('-r', '--recursive', action='store_true', default=True, 
                      help='递归处理子目录')
    parser.add_argument('--exclude', type=str, nargs='+', help='要排除的文件模式')
    
    # 批量处理参数
    parser.add_argument('--min-size', type=int, default=0, help='最小文件大小（字节）')
    parser.add_argument('--max-size', type=int, help='最大文件大小（字节）')
    parser.add_argument('--workers', type=int, default=4, help='并行工作线程数')
    parser.add_argument('--extensions', type=str, nargs='+', help='要过滤的文件扩展名')
    
    # 重复检测参数
    parser.add_argument('--min-duplicates', type=int, default=2, help='最小重复次数')
    
    # 哈希验证参数
    parser.add_argument('--expected-hash', type=str, help='期望的哈希值（用于验证模式）')
    
    # 重复文件处理参数
    parser.add_argument('--action', type=str, default='report', 
                      choices=['report', 'delete', 'move', 'link'], help='重复文件处理动作')
    parser.add_argument('--keep-strategy', type=str, default='newest', 
                      choices=['newest', 'oldest', 'smallest', 'largest', 'first', 'last'], help='文件保留策略')
    parser.add_argument('--dry-run', action='store_true', help='仅模拟操作而不实际执行')
    
    # 导出/导入参数
    parser.add_argument('--format', type=str, default='json', 
                      choices=['json', 'csv', 'txt'], help='导出/导入格式')
    parser.add_argument('--hash-file', type=str, help='哈希结果文件路径')
    
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 初始化工具
    tool = FileHashDuplicateDetector()
    
    try:
        # 处理不同的操作模式
        if args.calculate:
            # 计算哈希值模式
            if not args.input:
                logger.error("计算模式需要指定 --input")
                return 1
            
            input_path = os.path.expanduser(args.input)
            
            if os.path.isfile(input_path):
                # 计算单个文件哈希
                file_hash = tool.calculate_file_hash(input_path, args.algorithm)
                if file_hash:
                    logger.info(f"{args.algorithm.upper()} 哈希值: {file_hash}")
                    logger.info(f"文件: {input_path}")
                    
                    # 如果指定了输出文件，导出结果
                    if args.output:
                        tool.export_hash_results({input_path: file_hash}, args.output, args.format)
                    return 0
                else:
                    return 1
            
            elif os.path.isdir(input_path):
                # 批量计算目录中文件的哈希值
                hash_dict = tool.calculate_directory_hashes(
                    input_path,
                    args.algorithm,
                    args.recursive,
                    args.exclude,
                    args.min_size,
                    args.max_size,
                    args.workers,
                    args.extensions
                )
                
                # 如果指定了输出文件，导出结果
                if args.output:
                    tool.export_hash_results(hash_dict, args.output, args.format)
                
                # 输出统计信息
                logger.info(f"哈希计算完成: 成功 {len(hash_dict)} 个文件")
                return 0 if hash_dict else 1
            
            else:
                logger.error(f"输入路径不存在: {input_path}")
                return 1
        
        elif args.verify:
            # 验证哈希值模式
            if not args.input or not args.expected_hash:
                logger.error("验证模式需要指定 --input 和 --expected-hash")
                return 1
            
            input_path = os.path.expanduser(args.input)
            success = tool.verify_file_hash(input_path, args.expected_hash, args.algorithm)
            return 0 if success else 1
        
        elif args.detect:
            # 检测重复文件模式
            if args.hash_file:
                # 从哈希文件加载
                hash_dict = tool.load_hash_results(args.hash_file)
            elif args.input:
                # 计算哈希值
                input_path = os.path.expanduser(args.input)
                if os.path.isdir(input_path):
                    hash_dict = tool.calculate_directory_hashes(
                        input_path,
                        args.algorithm,
                        args.recursive,
                        args.exclude,
                        args.min_size,
                        args.max_size,
                        args.workers,
                        args.extensions
                    )
                else:
                    logger.error(f"检测重复文件模式需要目录输入或哈希文件: {input_path}")
                    return 1
            else:
                logger.error("检测重复文件模式需要指定 --input 或 --hash-file")
                return 1
            
            # 查找重复文件
            duplicate_files = tool.find_duplicate_files(hash_dict, args.min_duplicates)
            
            # 生成报告
            if args.output:
                tool.generate_duplicate_report(duplicate_files, args.output)
            else:
                tool.generate_duplicate_report(duplicate_files)
            
            return 0
        
        elif args.process:
            # 处理重复文件模式
            if args.hash_file:
                # 从哈希文件加载
                hash_dict = tool.load_hash_results(args.hash_file)
                duplicate_files = tool.find_duplicate_files(hash_dict, args.min_duplicates)
            elif args.input:
                # 计算哈希值并检测重复文件
                input_path = os.path.expanduser(args.input)
                if os.path.isdir(input_path):
                    hash_dict = tool.calculate_directory_hashes(
                        input_path,
                        args.algorithm,
                        args.recursive,
                        args.exclude,
                        args.min_size,
                        args.max_size,
                        args.workers,
                        args.extensions
                    )
                    duplicate_files = tool.find_duplicate_files(hash_dict, args.min_duplicates)
                else:
                    logger.error(f"处理重复文件模式需要目录输入或哈希文件: {input_path}")
                    return 1
            else:
                logger.error("处理重复文件模式需要指定 --input 或 --hash-file")
                return 1
            
            # 处理重复文件
            if duplicate_files:
                # 如果是移动操作，确保输出目录存在
                if args.action == 'move' and args.output:
                    output_dir = os.path.expanduser(args.output)
                else:
                    output_dir = None
                
                # 处理重复文件
                results = tool.process_duplicate_files(
                    duplicate_files,
                    args.action,
                    args.keep_strategy,
                    output_dir,
                    args.dry_run
                )
                
                # 如果指定了输出文件，生成报告
                if args.output and args.action != 'move':
                    tool.generate_duplicate_report(duplicate_files, args.output)
                
                return 0 if results else 1
            else:
                logger.info("未找到重复文件")
                return 0
        
        elif args.export:
            # 导出哈希结果模式
            if not args.hash_file or not args.output:
                logger.error("导出模式需要指定 --hash-file 和 --output")
                return 1
            
            # 加载哈希结果
            hash_dict = tool.load_hash_results(args.hash_file)
            
            # 导出哈希结果
            success = tool.export_hash_results(hash_dict, args.output, args.format)
            return 0 if success else 1
        
        elif args.load:
            # 加载哈希结果模式
            if not args.hash_file:
                logger.error("加载模式需要指定 --hash-file")
                return 1
            
            # 加载哈希结果
            hash_dict = tool.load_hash_results(args.hash_file)
            
            # 输出统计信息
            logger.info(f"已加载 {len(hash_dict)} 个文件的哈希值")
            
            # 如果指定了检测重复文件
            duplicate_files = tool.find_duplicate_files(hash_dict, args.min_duplicates)
            
            # 生成报告
            if args.output:
                tool.generate_duplicate_report(duplicate_files, args.output)
            else:
                tool.generate_duplicate_report(duplicate_files)
            
            return 0
        
        else:
            logger.error("请指定操作模式")
            return 1
        
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        return 1
    except Exception as e:
        logger.error(f"发生未预期的错误: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
