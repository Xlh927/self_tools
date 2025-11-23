#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录结构分析与可视化模块

该模块提供目录结构的全面分析与可视化功能，用于了解文件系统组织、文件分布和存储使用情况。
支持目录扫描、统计分析、树形可视化、空间占用分析和多种图表生成。

主要功能:
- 递归扫描目录结构
- 统计文件数量、目录数量、文件类型分布
- 分析存储空间占用
- 生成树形目录结构
- 创建文件类型分布饼图
- 创建目录大小柱状图
- 生成热力图展示空间分布
- 支持多种输出格式（PNG、SVG、PDF）
- 命令行接口
- 支持配置文件排除规则

作者: Self Tools
日期: 2023-11-10
"""

import os
import sys
import json
import time
import datetime
import argparse
import logging
import re
import pickle
from typing import Dict, List, Tuple, Set, Optional, Union, Any
from pathlib import Path
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试导入可视化库
try:
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    import numpy as np
    VISUALIZATION_ENABLED = True
except ImportError:
    logger.warning("无法导入matplotlib库，可视化功能将被禁用")
    VISUALIZATION_ENABLED = False

try:
    import networkx as nx
    NETWORKX_ENABLED = True
except ImportError:
    logger.warning("无法导入networkx库，网络图功能将被禁用")
    NETWORKX_ENABLED = False

try:
    import seaborn as sns
    SEABORN_ENABLED = True
except ImportError:
    logger.warning("无法导入seaborn库，增强可视化功能将被禁用")
    SEABORN_ENABLED = False


class DirectoryStructureAnalyzer:
    """
    目录结构分析器类
    """
    
    # 常见文件类型分组
    FILE_TYPE_GROUPS = {
        'text': ['.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml',
                '.py', '.java', '.c', '.cpp', '.h', '.hpp', '.js', '.ts',
                '.html', '.css', '.php', '.rb', '.go', '.rs', '.sh', '.bat',
                '.sql', '.log', '.ini', '.conf', '.cfg', '.properties'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
                '.svg', '.ico', '.jfif', '.pjpeg', '.pjp'],
        'document': ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
                    '.odt', '.ods', '.odp', '.rtf'],
        'archive': ['.zip', '.rar', '.tar', '.gz', '.7z', '.bz2', '.xz',
                    '.tar.gz', '.tar.bz2', '.tar.xz'],
        'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'],
        'executable': ['.exe', '.dll', '.so', '.dylib', '.app'],
        'database': ['.sqlite', '.db', '.mdb', '.accdb']
    }
    
    def __init__(self, root_dir: str, exclude_patterns: Optional[List[str]] = None,
                 max_depth: Optional[int] = None, follow_symlinks: bool = False):
        """
        初始化目录结构分析器
        
        Args:
            root_dir: 要分析的根目录
            exclude_patterns: 要排除的文件/目录正则表达式模式列表
            max_depth: 最大扫描深度
            follow_symlinks: 是否跟随符号链接
        """
        self.root_dir = os.path.abspath(root_dir)
        self.exclude_patterns = exclude_patterns or []
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks
        
        # 编译排除正则表达式
        self.exclude_regexes = [re.compile(pattern) for pattern in self.exclude_patterns]
        
        # 分析结果
        self.analysis_results = {
            'metadata': {
                'root_directory': self.root_dir,
                'analysis_time': datetime.datetime.now().isoformat(),
                'total_directories': 0,
                'total_files': 0,
                'total_size': 0,
                'scan_duration': 0
            },
            'directory_stats': {},  # 目录 -> {files: int, size: int, subdirs: int}
            'file_type_stats': {},  # 文件类型 -> {count: int, size: int}
            'extension_stats': {},  # 扩展名 -> {count: int, size: int}
            'largest_files': [],  # 最大文件列表
            'deepest_path': '',  # 最深路径
            'depth_count': {},  # 深度 -> 文件/目录数量
            'hourly_creation': Counter(),  # 创建时间小时分布
            'daily_modification': Counter()  # 修改时间日期分布
        }
        
        # 验证目录
        if not os.path.exists(self.root_dir) or not os.path.isdir(self.root_dir):
            raise ValueError(f"目录不存在或不是有效的目录: {self.root_dir}")
    
    def _should_exclude(self, path: str) -> bool:
        """
        检查是否应该排除指定路径
        
        Args:
            path: 要检查的路径
            
        Returns:
            是否排除
        """
        rel_path = os.path.relpath(path, self.root_dir)
        
        for regex in self.exclude_regexes:
            if regex.search(rel_path) or regex.search(os.path.basename(path)):
                return True
        
        return False
    
    def _get_file_type(self, extension: str) -> str:
        """
        根据扩展名获取文件类型
        
        Args:
            extension: 文件扩展名
            
        Returns:
            文件类型
        """
        extension = extension.lower()
        
        for file_type, extensions in self.FILE_TYPE_GROUPS.items():
            if extension in extensions:
                return file_type
        
        return 'other'
    
    def _get_path_depth(self, path: str) -> int:
        """
        获取路径深度
        
        Args:
            path: 路径
            
        Returns:
            深度
        """
        rel_path = os.path.relpath(path, self.root_dir)
        return rel_path.count(os.sep) + 1
    
    def _process_file(self, file_path: str, depth: int) -> Dict[str, Any]:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            depth: 路径深度
            
        Returns:
            文件信息字典
        """
        try:
            # 获取文件统计信息
            stat_info = os.stat(file_path)
            file_size = stat_info.st_size
            
            # 获取文件扩展名
            _, ext = os.path.splitext(file_path)
            ext = ext.lower() if ext else '(无扩展名)'
            
            # 获取文件类型
            file_type = self._get_file_type(ext)
            
            # 更新深度统计
            self.analysis_results['depth_count'][depth] = self.analysis_results['depth_count'].get(depth, 0) + 1
            
            # 更新创建时间小时统计
            creation_time = datetime.datetime.fromtimestamp(stat_info.st_ctime)
            self.analysis_results['hourly_creation'][creation_time.hour] += 1
            
            # 更新修改时间日期统计
            modification_date = datetime.datetime.fromtimestamp(stat_info.st_mtime).date()
            self.analysis_results['daily_modification'][modification_date.isoformat()] += 1
            
            return {
                'path': file_path,
                'size': file_size,
                'extension': ext,
                'type': file_type,
                'created': stat_info.st_ctime,
                'modified': stat_info.st_mtime
            }
            
        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {e}")
            return None
    
    def analyze(self, max_workers: int = 4, chunk_size: int = 1000) -> Dict[str, Any]:
        """
        分析目录结构
        
        Args:
            max_workers: 最大工作线程数
            chunk_size: 每个工作线程处理的文件块大小
            
        Returns:
            分析结果
        """
        logger.info(f"开始分析目录: {self.root_dir}")
        start_time = time.time()
        
        # 初始化目录统计
        self.analysis_results['directory_stats'][self.root_dir] = {
            'files': 0,
            'size': 0,
            'subdirs': 0
        }
        
        # 收集所有文件路径
        all_files = []
        all_dirs = [self.root_dir]
        
        # 递归遍历目录
        current_depth = 1
        deepest_path = self.root_dir
        deepest_depth = 1
        
        while all_dirs:
            next_dirs = []
            
            for dir_path in all_dirs:
                # 检查是否应该排除
                if self._should_exclude(dir_path):
                    continue
                
                # 检查深度限制
                depth = self._get_path_depth(dir_path)
                if self.max_depth is not None and depth > self.max_depth:
                    continue
                
                # 更新最深路径
                if depth > deepest_depth:
                    deepest_depth = depth
                    deepest_path = dir_path
                
                try:
                    # 遍历目录内容
                    for entry in os.listdir(dir_path):
                        entry_path = os.path.join(dir_path, entry)
                        
                        # 检查符号链接
                        if os.path.islink(entry_path):
                            if not self.follow_symlinks:
                                continue
                            # 检查是否存在循环链接
                            try:
                                real_path = os.path.realpath(entry_path)
                                if real_path.startswith(self.root_dir):
                                    logger.warning(f"检测到可能的循环链接: {entry_path}")
                                    continue
                            except:
                                continue
                        
                        # 检查是否应该排除
                        if self._should_exclude(entry_path):
                            continue
                        
                        if os.path.isdir(entry_path):
                            next_dirs.append(entry_path)
                            self.analysis_results['directory_stats'][entry_path] = {
                                'files': 0,
                                'size': 0,
                                'subdirs': 0
                            }
                        elif os.path.isfile(entry_path):
                            all_files.append((entry_path, depth + 1))
                
                except Exception as e:
                    logger.error(f"访问目录失败 {dir_path}: {e}")
            
            all_dirs = next_dirs
            current_depth += 1
        
        # 更新最深路径
        self.analysis_results['deepest_path'] = deepest_path
        
        # 并行处理文件
        total_files = len(all_files)
        logger.info(f"发现 {total_files} 个文件需要处理")
        
        processed_files = 0
        largest_files = []
        
        # 分块处理文件以避免内存问题
        for i in range(0, total_files, chunk_size):
            chunk = all_files[i:i+chunk_size]
            
            with ThreadPoolExecutor(max_workers=min(max_workers, len(chunk))) as executor:
                future_to_file = {executor.submit(self._process_file, file_path, depth): (file_path, depth)
                                 for file_path, depth in chunk}
                
                for future in as_completed(future_to_file):
                    file_path, depth = future_to_file[future]
                    try:
                        file_info = future.result()
                        if file_info:
                            # 更新统计信息
                            processed_files += 1
                            file_size = file_info['size']
                            file_ext = file_info['extension']
                            file_type = file_info['type']
                            
                            # 更新总大小
                            self.analysis_results['metadata']['total_size'] += file_size
                            
                            # 更新文件类型统计
                            self.analysis_results['file_type_stats'][file_type] = {
                                'count': self.analysis_results['file_type_stats'].get(file_type, {}).get('count', 0) + 1,
                                'size': self.analysis_results['file_type_stats'].get(file_type, {}).get('size', 0) + file_size
                            }
                            
                            # 更新扩展名统计
                            self.analysis_results['extension_stats'][file_ext] = {
                                'count': self.analysis_results['extension_stats'].get(file_ext, {}).get('count', 0) + 1,
                                'size': self.analysis_results['extension_stats'].get(file_ext, {}).get('size', 0) + file_size
                            }
                            
                            # 更新目录统计
                            dir_path = os.path.dirname(file_path)
                            while dir_path != self.root_dir and dir_path in self.analysis_results['directory_stats']:
                                self.analysis_results['directory_stats'][dir_path]['files'] += 1
                                self.analysis_results['directory_stats'][dir_path]['size'] += file_size
                                dir_path = os.path.dirname(dir_path)
                            
                            # 更新根目录统计
                            self.analysis_results['directory_stats'][self.root_dir]['files'] += 1
                            self.analysis_results['directory_stats'][self.root_dir]['size'] += file_size
                            
                            # 更新最大文件列表
                            largest_files.append((file_path, file_size))
                            if len(largest_files) > 10:
                                largest_files.sort(key=lambda x: x[1], reverse=True)
                                largest_files = largest_files[:10]
                        
                    except Exception as e:
                        logger.error(f"处理文件时发生异常 {file_path}: {e}")
                    
                    # 打印进度
                    if processed_files % 100 == 0 or processed_files == total_files:
                        logger.info(f"已处理 {processed_files}/{total_files} 文件")
        
        # 排序最大文件列表
        largest_files.sort(key=lambda x: x[1], reverse=True)
        self.analysis_results['largest_files'] = [
            {'path': path, 'size': size} for path, size in largest_files[:10]
        ]
        
        # 更新子目录统计
        for dir_path in list(self.analysis_results['directory_stats'].keys()):
            if dir_path == self.root_dir:
                continue
                
            parent_dir = os.path.dirname(dir_path)
            while parent_dir in self.analysis_results['directory_stats']:
                self.analysis_results['directory_stats'][parent_dir]['subdirs'] += 1
                parent_dir = os.path.dirname(parent_dir)
                if parent_dir == dir_path:  # 防止循环
                    break
        
        # 更新元数据
        self.analysis_results['metadata']['total_directories'] = len(self.analysis_results['directory_stats'])
        self.analysis_results['metadata']['total_files'] = processed_files
        self.analysis_results['metadata']['scan_duration'] = time.time() - start_time
        
        logger.info(f"目录分析完成，共处理 {processed_files} 个文件，耗时: {self.analysis_results['metadata']['scan_duration']:.2f}s")
        return self.analysis_results
    
    def save_results(self, output_file: str) -> bool:
        """
        保存分析结果到文件
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            
            # 根据文件扩展名确定格式
            _, ext = os.path.splitext(output_file.lower())
            
            if ext == '.json':
                # 保存为JSON格式
                with open(output_file, 'w', encoding='utf-8') as f:
                    # 转换Counter对象为字典
                    results_copy = self.analysis_results.copy()
                    results_copy['hourly_creation'] = dict(results_copy['hourly_creation'])
                    results_copy['daily_modification'] = dict(results_copy['daily_modification'])
                    json.dump(results_copy, f, ensure_ascii=False, indent=2)
            
            elif ext == '.pkl':
                # 保存为pickle格式
                with open(output_file, 'wb') as f:
                    pickle.dump(self.analysis_results, f)
            
            else:
                # 默认保存为JSON格式
                with open(output_file + '.json', 'w', encoding='utf-8') as f:
                    results_copy = self.analysis_results.copy()
                    results_copy['hourly_creation'] = dict(results_copy['hourly_creation'])
                    results_copy['daily_modification'] = dict(results_copy['daily_modification'])
                    json.dump(results_copy, f, ensure_ascii=False, indent=2)
                output_file += '.json'
            
            logger.info(f"分析结果已保存到 {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return False
    
    def generate_tree_structure(self, output_file: Optional[str] = None, 
                              max_depth: Optional[int] = 3) -> str:
        """
        生成树形目录结构
        
        Args:
            output_file: 输出文件路径（可选）
            max_depth: 最大显示深度
            
        Returns:
            树形结构字符串
        """
        tree_lines = []
        root_name = os.path.basename(self.root_dir)
        tree_lines.append(root_name + '/')
        
        def add_directory(path: str, prefix: str, current_depth: int):
            """递归添加目录内容"""
            if current_depth >= max_depth:
                return
                
            try:
                items = os.listdir(path)
                items.sort()  # 按名称排序
                
                # 过滤掉排除的项目
                filtered_items = []
                for item in items:
                    item_path = os.path.join(path, item)
                    if not self._should_exclude(item_path):
                        filtered_items.append(item)
                
                for i, item in enumerate(filtered_items):
                    item_path = os.path.join(path, item)
                    
                    # 确定连接线
                    if i == len(filtered_items) - 1:
                        # 最后一项
                        connector = '└── '
                        next_prefix = prefix + '    '
                    else:
                        connector = '├── '
                        next_prefix = prefix + '│   '
                    
                    tree_lines.append(prefix + connector + item)
                    
                    # 递归处理子目录
                    if os.path.isdir(item_path) and not os.path.islink(item_path):
                        tree_lines[-1] += '/'
                        add_directory(item_path, next_prefix, current_depth + 1)
            
            except Exception as e:
                logger.error(f"生成树形结构时访问目录失败 {path}: {e}")
        
        # 生成树形结构
        add_directory(self.root_dir, '', 0)
        tree_str = '\n'.join(tree_lines)
        
        # 保存到文件
        if output_file:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(tree_str)
                logger.info(f"树形目录结构已保存到 {output_file}")
            except Exception as e:
                logger.error(f"保存树形目录结构失败: {e}")
        
        return tree_str
    
    def generate_visualizations(self, output_dir: str, format: str = 'png',
                              dpi: int = 300) -> List[str]:
        """
        生成可视化图表
        
        Args:
            output_dir: 输出目录
            format: 图表格式 (png, svg, pdf)
            dpi: 图表分辨率
            
        Returns:
            生成的文件路径列表
        """
        if not VISUALIZATION_ENABLED:
            logger.warning("可视化功能不可用，matplotlib库未安装")
            return []
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        generated_files = []
        
        try:
            # 设置中文字体支持
            plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
            plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
            
            # 1. 文件类型分布饼图
            file = self._plot_file_type_pie(os.path.join(output_dir, f'file_type_distribution.{format}'), dpi)
            if file:
                generated_files.append(file)
            
            # 2. 目录大小柱状图
            file = self._plot_directory_sizes(os.path.join(output_dir, f'directory_sizes.{format}'), dpi)
            if file:
                generated_files.append(file)
            
            # 3. 扩展名统计柱状图
            file = self._plot_extension_stats(os.path.join(output_dir, f'extension_stats.{format}'), dpi)
            if file:
                generated_files.append(file)
            
            # 4. 深度分布条形图
            file = self._plot_depth_distribution(os.path.join(output_dir, f'depth_distribution.{format}'), dpi)
            if file:
                generated_files.append(file)
            
            # 5. 时间线热力图
            file = self._plot_time_heatmap(os.path.join(output_dir, f'time_heatmap.{format}'), dpi)
            if file:
                generated_files.append(file)
            
            # 6. 存储使用情况堆叠图
            file = self._plot_storage_usage(os.path.join(output_dir, f'storage_usage.{format}'), dpi)
            if file:
                generated_files.append(file)
                
        except Exception as e:
            logger.error(f"生成可视化图表失败: {e}")
        
        return generated_files
    
    def _plot_file_type_pie(self, output_file: str, dpi: int) -> Optional[str]:
        """
        绘制文件类型分布饼图
        """
        try:
            # 准备数据
            labels = []
            sizes = []
            explode = []
            max_size = 0
            max_idx = 0
            
            for i, (file_type, stats) in enumerate(self.analysis_results['file_type_stats'].items()):
                labels.append(file_type)
                sizes.append(stats['size'])
                explode.append(0.05)
                
                if stats['size'] > max_size:
                    max_size = stats['size']
                    max_idx = i
            
            # 突出最大的部分
            explode[max_idx] = 0.15
            
            # 创建饼图
            plt.figure(figsize=(10, 8))
            
            # 计算百分比
            total_size = sum(sizes)
            autopct = lambda p: f'{p:.1f}%\n{self._format_size(p*total_size/100)}'
            
            wedges, texts, autotexts = plt.pie(
                sizes, explode=explode, labels=labels, autopct=autopct,
                shadow=True, startangle=90, 
                wedgeprops={'edgecolor': 'w', 'linewidth': 1}
            )
            
            # 设置文本样式
            plt.setp(autotexts, size=10, weight="bold")
            plt.setp(texts, size=12)
            
            plt.axis('equal')  # 确保饼图是圆形
            plt.title('文件类型存储空间分布', fontsize=15, pad=20)
            
            # 添加图例
            plt.legend(wedges, labels, title="文件类型", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
            plt.close()
            
            logger.info(f"文件类型分布饼图已保存到 {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"绘制文件类型饼图失败: {e}")
            return None
    
    def _plot_directory_sizes(self, output_file: str, dpi: int) -> Optional[str]:
        """
        绘制目录大小柱状图
        """
        try:
            # 准备数据 - 只显示前20个最大的目录
            dir_stats = [(path, stats['size']) 
                        for path, stats in self.analysis_results['directory_stats'].items()]
            dir_stats.sort(key=lambda x: x[1], reverse=True)
            dir_stats = dir_stats[:20]  # 只取前20个
            
            # 转换为相对路径并格式化大小
            labels = [os.path.relpath(path, self.root_dir) or '.' for path, _ in dir_stats]
            sizes = [size for _, size in dir_stats]
            formatted_sizes = [self._format_size(size) for size in sizes]
            
            # 创建柱状图
            plt.figure(figsize=(12, max(6, len(labels) * 0.3)))
            
            # 使用颜色渐变
            colors = plt.cm.YlOrRd(np.linspace(0.2, 0.8, len(labels)))
            
            bars = plt.barh(labels, sizes, color=colors)
            
            # 添加数值标签
            for i, bar in enumerate(bars):
                plt.text(bar.get_width() + max(sizes) * 0.01, bar.get_y() + bar.get_height()/2,
                        formatted_sizes[i], va='center', fontsize=10)
            
            plt.xlabel('大小', fontsize=12)
            plt.title('目录大小分布（前20名）', fontsize=15, pad=20)
            plt.xscale('log')  # 使用对数刻度以便更好地显示差异
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
            plt.close()
            
            logger.info(f"目录大小柱状图已保存到 {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"绘制目录大小柱状图失败: {e}")
            return None
    
    def _plot_extension_stats(self, output_file: str, dpi: int) -> Optional[str]:
        """
        绘制扩展名统计柱状图
        """
        try:
            # 准备数据 - 只显示前15个最常见的扩展名
            ext_stats = [(ext, stats['count']) 
                        for ext, stats in self.analysis_results['extension_stats'].items()]
            ext_stats.sort(key=lambda x: x[1], reverse=True)
            ext_stats = ext_stats[:15]  # 只取前15个
            
            labels = [ext for ext, _ in ext_stats]
            counts = [count for _, count in ext_stats]
            
            # 创建柱状图
            plt.figure(figsize=(12, 8))
            
            # 使用颜色渐变
            colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(labels)))
            
            bars = plt.bar(labels, counts, color=colors)
            
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + max(counts) * 0.01,
                        f'{height}', ha='center', va='bottom', fontsize=9)
            
            plt.xlabel('文件扩展名', fontsize=12)
            plt.ylabel('文件数量', fontsize=12)
            plt.title('文件扩展名分布（前15名）', fontsize=15, pad=20)
            plt.xticks(rotation=45, ha='right')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
            plt.close()
            
            logger.info(f"扩展名统计柱状图已保存到 {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"绘制扩展名统计柱状图失败: {e}")
            return None
    
    def _plot_depth_distribution(self, output_file: str, dpi: int) -> Optional[str]:
        """
        绘制深度分布条形图
        """
        try:
            # 准备数据
            depth_data = sorted(self.analysis_results['depth_count'].items())
            depths = [f'深度 {depth}' for depth, _ in depth_data]
            counts = [count for _, count in depth_data]
            
            # 创建条形图
            plt.figure(figsize=(10, 6))
            
            # 使用颜色渐变
            colors = plt.cm.Greens(np.linspace(0.4, 0.8, len(depths)))
            
            bars = plt.bar(depths, counts, color=colors)
            
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + max(counts) * 0.01,
                        f'{height}', ha='center', va='bottom', fontsize=9)
            
            plt.xlabel('目录深度', fontsize=12)
            plt.ylabel('文件数量', fontsize=12)
            plt.title('目录深度分布', fontsize=15, pad=20)
            plt.xticks(rotation=45, ha='right')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
            plt.close()
            
            logger.info(f"深度分布条形图已保存到 {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"绘制深度分布条形图失败: {e}")
            return None
    
    def _plot_time_heatmap(self, output_file: str, dpi: int) -> Optional[str]:
        """
        绘制时间线热力图
        """
        try:
            # 如果没有seaborn，使用基本的matplotlib热力图
            if not SEABORN_ENABLED:
                logger.warning("seaborn未安装，跳过热力图生成")
                return None
                
            # 准备小时数据（24小时）
            hourly_data = np.zeros((1, 24))
            for hour, count in self.analysis_results['hourly_creation'].items():
                if 0 <= hour < 24:
                    hourly_data[0, hour] = count
            
            # 创建热力图
            plt.figure(figsize=(12, 3))
            
            if SEABORN_ENABLED:
                sns.heatmap(hourly_data, cmap='YlOrRd', cbar_kws={'label': '文件数量'})
            else:
                plt.imshow(hourly_data, cmap='YlOrRd', aspect='auto')
                plt.colorbar(label='文件数量')
            
            plt.xticks(range(24), [f'{h}h' for h in range(24)], fontsize=8, rotation=45)
            plt.yticks([])  # 隐藏y轴刻度
            plt.xlabel('小时', fontsize=12)
            plt.title('文件创建时间分布（小时）', fontsize=15, pad=20)
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
            plt.close()
            
            logger.info(f"时间线热力图已保存到 {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"绘制时间线热力图失败: {e}")
            return None
    
    def _plot_storage_usage(self, output_file: str, dpi: int) -> Optional[str]:
        """
        绘制存储使用情况堆叠图
        """
        try:
            # 准备数据
            file_types = list(self.analysis_results['file_type_stats'].keys())
            sizes = [stats['size'] for stats in self.analysis_results['file_type_stats'].values()]
            
            # 按大小排序
            sorted_data = sorted(zip(file_types, sizes), key=lambda x: x[1], reverse=True)
            file_types, sizes = zip(*sorted_data)
            
            # 创建堆叠图
            plt.figure(figsize=(10, 6))
            
            # 使用彩色调色板
            colors = plt.cm.tab20(np.linspace(0, 1, len(file_types)))
            
            plt.pie(sizes, labels=file_types, autopct='%1.1f%%', startangle=90,
                   colors=colors, wedgeprops={'edgecolor': 'w', 'linewidth': 1})
            
            plt.axis('equal')  # 确保饼图是圆形
            plt.title('存储空间使用分布', fontsize=15, pad=20)
            
            # 添加图例
            plt.legend(title="文件类型", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
            plt.close()
            
            logger.info(f"存储使用情况图已保存到 {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"绘制存储使用情况图失败: {e}")
            return None
    
    def _format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 字节大小
            
        Returns:
            格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def generate_report(self, output_file: str, format: str = 'txt') -> bool:
        """
        生成分析报告
        
        Args:
            output_file: 输出文件路径
            format: 报告格式 (txt, md)
            
        Returns:
            是否成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            
            # 准备报告内容
            report_lines = []
            
            if format == 'md':
                report_lines.append("# 目录结构分析报告")
                report_lines.append(f"## 分析时间: {self.analysis_results['metadata']['analysis_time']}")
                report_lines.append(f"## 分析目录: {self.analysis_results['metadata']['root_directory']}")
                report_lines.append("")
                
                report_lines.append("## 基本统计")
                report_lines.append(f"- 总目录数: **{self.analysis_results['metadata']['total_directories']}**")
                report_lines.append(f"- 总文件数: **{self.analysis_results['metadata']['total_files']}**")
                report_lines.append(f"- 总大小: **{self._format_size(self.analysis_results['metadata']['total_size'])}**")
                report_lines.append(f"- 分析耗时: **{self.analysis_results['metadata']['scan_duration']:.2f} 秒**")
                report_lines.append(f"- 最深路径: **{self.analysis_results['deepest_path']}**")
                report_lines.append("")
                
                report_lines.append("## 文件类型统计")
                report_lines.append("| 文件类型 | 文件数量 | 占用空间 |")
                report_lines.append("|---------|---------|----------|")
                
                # 按大小排序文件类型
                sorted_file_types = sorted(
                    self.analysis_results['file_type_stats'].items(),
                    key=lambda x: x[1]['size'],
                    reverse=True
                )
                
                for file_type, stats in sorted_file_types:
                    percentage = (stats['size'] / self.analysis_results['metadata']['total_size'] * 100) if self.analysis_results['metadata']['total_size'] > 0 else 0
                    report_lines.append(f"| {file_type} | {stats['count']} | {self._format_size(stats['size'])} ({percentage:.1f}%) |")
                
                report_lines.append("")
                
                report_lines.append("## 最大文件")
                report_lines.append("| 排名 | 文件路径 | 大小 |")
                report_lines.append("|-----|---------|------|")
                
                for i, file_info in enumerate(self.analysis_results['largest_files'], 1):
                    report_lines.append(f"| {i} | {file_info['path']} | {self._format_size(file_info['size'])} |")
                
            else:  # txt format
                report_lines.append("=" * 80)
                report_lines.append("目录结构分析报告")
                report_lines.append("=" * 80)
                report_lines.append(f"分析时间: {self.analysis_results['metadata']['analysis_time']}")
                report_lines.append(f"分析目录: {self.analysis_results['metadata']['root_directory']}")
                report_lines.append("" * 2)
                
                report_lines.append("基本统计:")
                report_lines.append("-" * 40)
                report_lines.append(f"总目录数: {self.analysis_results['metadata']['total_directories']}")
                report_lines.append(f"总文件数: {self.analysis_results['metadata']['total_files']}")
                report_lines.append(f"总大小: {self._format_size(self.analysis_results['metadata']['total_size'])}")
                report_lines.append(f"分析耗时: {self.analysis_results['metadata']['scan_duration']:.2f} 秒")
                report_lines.append(f"最深路径: {self.analysis_results['deepest_path']}")
                report_lines.append("" * 2)
                
                report_lines.append("文件类型统计:")
                report_lines.append("-" * 40)
                
                # 按大小排序文件类型
                sorted_file_types = sorted(
                    self.analysis_results['file_type_stats'].items(),
                    key=lambda x: x[1]['size'],
                    reverse=True
                )
                
                for file_type, stats in sorted_file_types:
                    percentage = (stats['size'] / self.analysis_results['metadata']['total_size'] * 100) if self.analysis_results['metadata']['total_size'] > 0 else 0
                    report_lines.append(f"{file_type}: {stats['count']} 个文件, {self._format_size(stats['size'])} ({percentage:.1f}%)")
                
                report_lines.append("" * 2)
                
                report_lines.append("最大文件:")
                report_lines.append("-" * 40)
                
                for i, file_info in enumerate(self.analysis_results['largest_files'], 1):
                    report_lines.append(f"{i}. {file_info['path']} ({self._format_size(file_info['size'])})")
            
            # 保存报告
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            logger.info(f"分析报告已保存到 {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"生成分析报告失败: {e}")
            return False


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description='目录结构分析与可视化工具')
    
    # 基本参数
    parser.add_argument('directory', help='要分析的目录路径')
    parser.add_argument('-o', '--output-dir', default='./analysis_results', 
                       help='分析结果输出目录')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='递归分析子目录（默认启用）')
    parser.add_argument('--no-recursive', action='store_true',
                       help='禁用递归分析')
    
    # 过滤参数
    parser.add_argument('-e', '--exclude', action='append', default=[],
                       help='排除的文件/目录正则表达式模式')
    parser.add_argument('-d', '--max-depth', type=int, default=None,
                       help='最大分析深度')
    parser.add_argument('--follow-symlinks', action='store_true',
                       help='跟随符号链接')
    
    # 输出选项
    parser.add_argument('--json', action='store_true',
                       help='保存JSON格式的分析结果')
    parser.add_argument('--pickle', action='store_true',
                       help='保存pickle格式的分析结果')
    parser.add_argument('--tree', action='store_true',
                       help='生成树形目录结构')
    parser.add_argument('--tree-depth', type=int, default=3,
                       help='树形结构最大显示深度')
    parser.add_argument('--visualize', action='store_true',
                       help='生成可视化图表')
    parser.add_argument('--report', action='store_true',
                       help='生成分析报告')
    parser.add_argument('--report-format', default='txt', choices=['txt', 'md'],
                       help='报告格式')
    parser.add_argument('--viz-format', default='png', choices=['png', 'svg', 'pdf'],
                       help='可视化图表格式')
    parser.add_argument('--dpi', type=int, default=300,
                       help='图表分辨率')
    
    # 性能参数
    parser.add_argument('-w', '--workers', type=int, default=4,
                       help='并行工作线程数')
    
    # 日志级别
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='显示详细日志')
    
    return parser.parse_args()


def main():
    """
    主函数
    """
    args = parse_arguments()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # 确定是否递归
    recursive = args.recursive or not args.no_recursive
    max_depth = args.max_depth if not recursive else args.max_depth
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # 创建分析器实例
        analyzer = DirectoryStructureAnalyzer(
            args.directory,
            exclude_patterns=args.exclude,
            max_depth=max_depth,
            follow_symlinks=args.follow_symlinks
        )
        
        # 执行分析
        results = analyzer.analyze(max_workers=args.workers)
        
        # 输出基本统计信息
        print("\n目录分析完成！")
        print(f"总目录数: {results['metadata']['total_directories']}")
        print(f"总文件数: {results['metadata']['total_files']}")
        print(f"总大小: {analyzer._format_size(results['metadata']['total_size'])}")
        print(f"分析耗时: {results['metadata']['scan_duration']:.2f} 秒")
        
        # 保存JSON结果
        if args.json or not (args.pickle or args.tree or args.visualize or args.report):
            json_file = os.path.join(args.output_dir, 'analysis_results.json')
            analyzer.save_results(json_file)
        
        # 保存pickle结果
        if args.pickle:
            pickle_file = os.path.join(args.output_dir, 'analysis_results.pkl')
            analyzer.save_results(pickle_file)
        
        # 生成树形结构
        if args.tree:
            tree_file = os.path.join(args.output_dir, 'directory_tree.txt')
            tree_str = analyzer.generate_tree_structure(tree_file, max_depth=args.tree_depth)
            print(f"\n树形目录结构已保存到 {tree_file}")
        
        # 生成可视化图表
        if args.visualize:
            viz_dir = os.path.join(args.output_dir, 'visualizations')
            generated_files = analyzer.generate_visualizations(viz_dir, format=args.viz_format, dpi=args.dpi)
            print(f"\n已生成 {len(generated_files)} 个可视化图表，保存到 {viz_dir}")
        
        # 生成分析报告
        if args.report:
            report_ext = 'md' if args.report_format == 'md' else 'txt'
            report_file = os.path.join(args.output_dir, f'analysis_report.{report_ext}')
            analyzer.generate_report(report_file, format=args.report_format)
            print(f"\n分析报告已保存到 {report_file}")
        
        print(f"\n所有结果已保存到目录: {args.output_dir}")
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
