#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件搜索与索引模块

该模块提供高效的文件搜索与索引功能，用于快速定位和检索文件系统中的文件。
支持创建文件索引、全文搜索、元数据搜索、增量更新和索引优化等功能。

主要功能:
- 创建文件索引（扫描目录并建立文件元数据索引）
- 文件内容搜索（支持正则表达式）
- 文件属性搜索（按名称、大小、修改时间、权限等）
- 索引增量更新
- 索引优化
- 搜索结果过滤与排序
- 支持多种文件类型
- 命令行接口

作者: Self Tools
日期: 2023-11-10
"""

import os
import re
import json
import time
import datetime
import hashlib
import shutil
import pickle
import logging
from typing import Dict, List, Tuple, Set, Optional, Union, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileIndexer:
    """
    文件索引器类，负责创建和维护文件索引
    """
    
    # 支持的文件扩展名
    TEXT_EXTENSIONS = {
        '.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml',
        '.py', '.java', '.c', '.cpp', '.h', '.hpp', '.js', '.ts',
        '.html', '.css', '.php', '.rb', '.go', '.rs', '.sh', '.bat',
        '.sql', '.log', '.ini', '.conf', '.cfg', '.properties'
    }
    
    # 图像文件扩展名
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
        '.svg', '.ico', '.jfif', '.pjpeg', '.pjp'
    }
    
    # 文档文件扩展名
    DOCUMENT_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
        '.odt', '.ods', '.odp', '.rtf'
    }
    
    # 归档文件扩展名
    ARCHIVE_EXTENSIONS = {
        '.zip', '.rar', '.tar', '.gz', '.7z', '.bz2', '.xz',
        '.tar.gz', '.tar.bz2', '.tar.xz'
    }
    
    def __init__(self, index_file: str = 'file_index.json'):
        """
        初始化文件索引器
        
        Args:
            index_file: 索引文件保存路径
        """
        self.index_file = index_file
        self.index = {
            'metadata': {
                'created_at': datetime.datetime.now().isoformat(),
                'last_updated': datetime.datetime.now().isoformat(),
                'version': '1.0',
                'total_files': 0,
                'indexed_directories': []
            },
            'files': {},  # 文件路径 -> 文件元数据
            'content_index': {},  # 关键词 -> 文件路径列表
            'file_types': {},  # 文件类型 -> 文件路径列表
            'directories': {}  # 目录 -> 文件路径列表
        }
        self._load_index()
    
    def _load_index(self):
        """
        从文件加载索引
        """
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.index = json.load(f)
                logger.info(f"索引已加载，包含 {self.index['metadata']['total_files']} 个文件")
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
    
    def _save_index(self):
        """
        保存索引到文件
        """
        try:
            self.index['metadata']['last_updated'] = datetime.datetime.now().isoformat()
            self.index['metadata']['total_files'] = len(self.index['files'])
            
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.index_file)), exist_ok=True)
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
            logger.info(f"索引已保存到 {self.index_file}")
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """
        计算文件哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件哈希值
        """
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return ''
    
    def _is_text_file(self, file_path: str) -> bool:
        """
        检查文件是否为文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为文本文件
        """
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.TEXT_EXTENSIONS
    
    def _get_file_type(self, file_path: str) -> str:
        """
        获取文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件类型
        """
        _, ext = os.path.splitext(file_path.lower())
        
        if ext in self.TEXT_EXTENSIONS:
            return 'text'
        elif ext in self.IMAGE_EXTENSIONS:
            return 'image'
        elif ext in self.DOCUMENT_EXTENSIONS:
            return 'document'
        elif ext in self.ARCHIVE_EXTENSIONS:
            return 'archive'
        else:
            return 'other'
    
    def _index_file_content(self, file_path: str) -> Set[str]:
        """
        索引文件内容，提取关键词
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的关键词集合
        """
        keywords = set()
        
        if not self._is_text_file(file_path):
            return keywords
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                
                # 提取单词（简单实现）
                words = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', content)
                keywords.update(words)
                
                # 提取数字
                numbers = re.findall(r'\b\d+\b', content)
                keywords.update(numbers)
                
        except Exception as e:
            logger.error(f"索引文件内容失败 {file_path}: {e}")
        
        return keywords
    
    def _process_file(self, file_path: str, include_content: bool = False) -> Dict[str, Any]:
        """
        处理单个文件，提取元数据
        
        Args:
            file_path: 文件路径
            include_content: 是否包含内容索引
            
        Returns:
            文件元数据
        """
        try:
            file_stats = os.stat(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            file_type = self._get_file_type(file_path)
            
            metadata = {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': file_stats.st_size,
                'created': datetime.datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                'modified': datetime.datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                'accessed': datetime.datetime.fromtimestamp(file_stats.st_atime).isoformat(),
                'mode': file_stats.st_mode,
                'extension': file_ext,
                'type': file_type,
                'hash': self._get_file_hash(file_path),
                'content_indexed': include_content
            }
            
            if include_content:
                keywords = self._index_file_content(file_path)
                metadata['keywords'] = list(keywords)
                
                # 更新内容索引
                for keyword in keywords:
                    if keyword not in self.index['content_index']:
                        self.index['content_index'][keyword] = []
                    if file_path not in self.index['content_index'][keyword]:
                        self.index['content_index'][keyword].append(file_path)
            
            return metadata
            
        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {e}")
            return None
    
    def create_index(self, root_dir: str, recursive: bool = True, 
                    include_content: bool = False, max_workers: int = 4) -> int:
        """
        创建文件索引
        
        Args:
            root_dir: 根目录路径
            recursive: 是否递归处理子目录
            include_content: 是否包含内容索引
            max_workers: 最大工作线程数
            
        Returns:
            索引的文件数量
        """
        if not os.path.exists(root_dir) or not os.path.isdir(root_dir):
            logger.error(f"目录不存在或不是有效的目录: {root_dir}")
            return 0
        
        logger.info(f"开始创建索引，根目录: {root_dir}, 递归: {recursive}, 内容索引: {include_content}")
        
        # 重置索引（保留索引配置）
        self.index['files'] = {}
        self.index['content_index'] = {}
        self.index['file_types'] = {}
        self.index['directories'] = {}
        self.index['metadata']['indexed_directories'] = [root_dir]
        
        # 获取所有文件路径
        all_files = []
        if recursive:
            for dirpath, _, filenames in os.walk(root_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    all_files.append(file_path)
        else:
            for filename in os.listdir(root_dir):
                file_path = os.path.join(root_dir, filename)
                if os.path.isfile(file_path):
                    all_files.append(file_path)
        
        total_files = len(all_files)
        logger.info(f"发现 {total_files} 个文件需要索引")
        
        # 使用线程池并行处理文件
        indexed_count = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(self._process_file, file_path, include_content): file_path 
                             for file_path in all_files}
            
            for i, future in enumerate(as_completed(future_to_file)):
                file_path = future_to_file[future]
                try:
                    metadata = future.result()
                    if metadata:
                        # 更新文件索引
                        self.index['files'][file_path] = metadata
                        
                        # 更新文件类型索引
                        file_type = metadata['type']
                        if file_type not in self.index['file_types']:
                            self.index['file_types'][file_type] = []
                        self.index['file_types'][file_type].append(file_path)
                        
                        # 更新目录索引
                        dir_path = os.path.dirname(file_path)
                        if dir_path not in self.index['directories']:
                            self.index['directories'][dir_path] = []
                        self.index['directories'][dir_path].append(file_path)
                        
                        indexed_count += 1
                except Exception as e:
                    logger.error(f"处理文件时发生异常 {file_path}: {e}")
                
                # 打印进度
                if (i + 1) % 100 == 0 or (i + 1) == total_files:
                    elapsed = time.time() - start_time
                    logger.info(f"已索引 {i + 1}/{total_files} 文件 ({indexed_count} 个成功)，耗时: {elapsed:.2f}s")
        
        # 保存索引
        self._save_index()
        
        logger.info(f"索引创建完成，成功索引 {indexed_count} 个文件")
        return indexed_count
    
    def update_index(self, root_dir: str, recursive: bool = True, 
                    include_content: bool = False, max_workers: int = 4) -> Dict[str, int]:
        """
        更新文件索引
        
        Args:
            root_dir: 根目录路径
            recursive: 是否递归处理子目录
            include_content: 是否包含内容索引
            max_workers: 最大工作线程数
            
        Returns:
            更新统计信息
        """
        if not os.path.exists(root_dir) or not os.path.isdir(root_dir):
            logger.error(f"目录不存在或不是有效的目录: {root_dir}")
            return {'added': 0, 'updated': 0, 'removed': 0}
        
        logger.info(f"开始更新索引，根目录: {root_dir}")
        
        # 获取当前所有文件路径
        current_files = set()
        if recursive:
            for dirpath, _, filenames in os.walk(root_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    current_files.add(file_path)
        else:
            for filename in os.listdir(root_dir):
                file_path = os.path.join(root_dir, filename)
                if os.path.isfile(file_path):
                    current_files.add(file_path)
        
        # 获取之前索引的文件路径
        indexed_files = set(self.index['files'].keys())
        
        # 找出新增、更新和删除的文件
        new_files = current_files - indexed_files
        common_files = current_files & indexed_files
        deleted_files = indexed_files - current_files
        
        # 统计信息
        stats = {'added': 0, 'updated': 0, 'removed': 0}
        
        # 处理删除的文件
        for file_path in deleted_files:
            # 从内容索引中移除
            if 'keywords' in self.index['files'][file_path]:
                for keyword in self.index['files'][file_path]['keywords']:
                    if keyword in self.index['content_index']:
                        self.index['content_index'][keyword].remove(file_path)
                        if not self.index['content_index'][keyword]:
                            del self.index['content_index'][keyword]
            
            # 从文件类型索引中移除
            file_type = self.index['files'][file_path]['type']
            if file_type in self.index['file_types']:
                self.index['file_types'][file_type].remove(file_path)
                if not self.index['file_types'][file_type]:
                    del self.index['file_types'][file_type]
            
            # 从目录索引中移除
            dir_path = os.path.dirname(file_path)
            if dir_path in self.index['directories']:
                self.index['directories'][dir_path].remove(file_path)
                if not self.index['directories'][dir_path]:
                    del self.index['directories'][dir_path]
            
            # 从文件索引中移除
            del self.index['files'][file_path]
            stats['removed'] += 1
        
        logger.info(f"发现 {len(deleted_files)} 个已删除文件")
        
        # 处理新增的文件
        if new_files:
            logger.info(f"发现 {len(new_files)} 个新增文件")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {executor.submit(self._process_file, file_path, include_content): file_path 
                                 for file_path in new_files}
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        metadata = future.result()
                        if metadata:
                            # 更新文件索引
                            self.index['files'][file_path] = metadata
                            
                            # 更新文件类型索引
                            file_type = metadata['type']
                            if file_type not in self.index['file_types']:
                                self.index['file_types'][file_type] = []
                            self.index['file_types'][file_type].append(file_path)
                            
                            # 更新目录索引
                            dir_path = os.path.dirname(file_path)
                            if dir_path not in self.index['directories']:
                                self.index['directories'][dir_path] = []
                            self.index['directories'][dir_path].append(file_path)
                            
                            stats['added'] += 1
                    except Exception as e:
                        logger.error(f"处理新增文件时发生异常 {file_path}: {e}")
        
        # 处理需要更新的文件
        updated_files = []
        for file_path in common_files:
            current_mtime = os.path.getmtime(file_path)
            indexed_mtime = datetime.datetime.fromisoformat(
                self.index['files'][file_path]['modified']).timestamp()
            
            # 如果文件被修改或内容索引状态不一致，则更新
            if abs(current_mtime - indexed_mtime) > 1 or \
               self.index['files'][file_path]['content_indexed'] != include_content:
                updated_files.append(file_path)
        
        if updated_files:
            logger.info(f"发现 {len(updated_files)} 个需要更新的文件")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {executor.submit(self._process_file, file_path, include_content): file_path 
                                 for file_path in updated_files}
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        metadata = future.result()
                        if metadata:
                            # 更新文件索引
                            self.index['files'][file_path] = metadata
                            stats['updated'] += 1
                    except Exception as e:
                        logger.error(f"处理更新文件时发生异常 {file_path}: {e}")
        
        # 保存索引
        self._save_index()
        
        logger.info(f"索引更新完成，新增: {stats['added']}, 更新: {stats['updated']}, 删除: {stats['removed']}")
        return stats
    
    def optimize_index(self):
        """
        优化索引，删除冗余数据并压缩
        """
        logger.info("开始优化索引")
        
        # 优化内容索引（移除重复和排序）
        for keyword, file_paths in self.index['content_index'].items():
            unique_paths = list(set(file_paths))
            unique_paths.sort()
            self.index['content_index'][keyword] = unique_paths
        
        # 优化文件类型索引
        for file_type, file_paths in self.index['file_types'].items():
            unique_paths = list(set(file_paths))
            unique_paths.sort()
            self.index['file_types'][file_type] = unique_paths
        
        # 优化目录索引
        for dir_path, file_paths in self.index['directories'].items():
            unique_paths = list(set(file_paths))
            unique_paths.sort()
            self.index['directories'][dir_path] = unique_paths
        
        # 保存优化后的索引
        self._save_index()
        
        logger.info("索引优化完成")
    
    def get_index_info(self) -> Dict[str, Any]:
        """
        获取索引信息
        
        Returns:
            索引信息字典
        """
        info = self.index['metadata'].copy()
        info['file_types'] = {file_type: len(file_paths) 
                            for file_type, file_paths in self.index['file_types'].items()}
        info['keyword_count'] = len(self.index['content_index'])
        info['directory_count'] = len(self.index['directories'])
        return info


class FileSearcher:
    """
    文件搜索器类，负责搜索文件
    """
    
    def __init__(self, indexer: FileIndexer):
        """
        初始化文件搜索器
        
        Args:
            indexer: 文件索引器实例
        """
        self.indexer = indexer
    
    def search_by_name(self, pattern: str, regex: bool = False, 
                      case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        按文件名搜索
        
        Args:
            pattern: 搜索模式
            regex: 是否为正则表达式
            case_sensitive: 是否区分大小写
            
        Returns:
            搜索结果列表
        """
        results = []
        
        for file_path, metadata in self.indexer.index['files'].items():
            filename = metadata['name']
            
            if not case_sensitive:
                filename = filename.lower()
                search_pattern = pattern.lower()
            else:
                search_pattern = pattern
            
            if regex:
                try:
                    if re.search(search_pattern, filename):
                        results.append(metadata.copy())
                except re.error as e:
                    logger.error(f"正则表达式错误: {e}")
                    return []
            else:
                if search_pattern in filename:
                    results.append(metadata.copy())
        
        return results
    
    def search_by_content(self, keyword: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        按文件内容搜索
        
        Args:
            keyword: 搜索关键词
            case_sensitive: 是否区分大小写
            
        Returns:
            搜索结果列表
        """
        results = []
        
        if not case_sensitive:
            search_keyword = keyword.lower()
        else:
            search_keyword = keyword
        
        # 检查内容索引
        if search_keyword in self.indexer.index['content_index']:
            for file_path in self.indexer.index['content_index'][search_keyword]:
                if file_path in self.indexer.index['files']:
                    results.append(self.indexer.index['files'][file_path].copy())
        
        return results
    
    def search_by_type(self, file_type: str) -> List[Dict[str, Any]]:
        """
        按文件类型搜索
        
        Args:
            file_type: 文件类型
            
        Returns:
            搜索结果列表
        """
        results = []
        
        if file_type in self.indexer.index['file_types']:
            for file_path in self.indexer.index['file_types'][file_type]:
                if file_path in self.indexer.index['files']:
                    results.append(self.indexer.index['files'][file_path].copy())
        
        return results
    
    def search_by_size(self, min_size: Optional[int] = None, 
                      max_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        按文件大小搜索
        
        Args:
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            
        Returns:
            搜索结果列表
        """
        results = []
        
        for file_path, metadata in self.indexer.index['files'].items():
            file_size = metadata['size']
            
            if min_size is not None and file_size < min_size:
                continue
            if max_size is not None and file_size > max_size:
                continue
            
            results.append(metadata.copy())
        
        return results
    
    def search_by_modified_time(self, start_time: Optional[datetime.datetime] = None, 
                               end_time: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
        """
        按修改时间搜索
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            搜索结果列表
        """
        results = []
        
        for file_path, metadata in self.indexer.index['files'].items():
            modified_time = datetime.datetime.fromisoformat(metadata['modified'])
            
            if start_time is not None and modified_time < start_time:
                continue
            if end_time is not None and modified_time > end_time:
                continue
            
            results.append(metadata.copy())
        
        return results
    
    def search_by_directory(self, directory: str) -> List[Dict[str, Any]]:
        """
        按目录搜索
        
        Args:
            directory: 目录路径
            
        Returns:
            搜索结果列表
        """
        results = []
        
        # 精确匹配目录
        if directory in self.indexer.index['directories']:
            for file_path in self.indexer.index['directories'][directory]:
                if file_path in self.indexer.index['files']:
                    results.append(self.indexer.index['files'][file_path].copy())
        else:
            # 模糊匹配子目录
            for dir_path, file_paths in self.indexer.index['directories'].items():
                if dir_path.startswith(directory):
                    for file_path in file_paths:
                        if file_path in self.indexer.index['files']:
                            results.append(self.indexer.index['files'][file_path].copy())
        
        return results
    
    def filter_results(self, results: List[Dict[str, Any]], 
                      filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        过滤搜索结果
        
        Args:
            results: 搜索结果列表
            filters: 过滤条件
            
        Returns:
            过滤后的结果列表
        """
        filtered_results = []
        
        for result in results:
            match = True
            
            # 按扩展名过滤
            if 'extension' in filters:
                if result['extension'].lower() != filters['extension'].lower():
                    match = False
            
            # 按最小大小过滤
            if 'min_size' in filters:
                if result['size'] < filters['min_size']:
                    match = False
            
            # 按最大大小过滤
            if 'max_size' in filters:
                if result['size'] > filters['max_size']:
                    match = False
            
            # 按修改时间过滤
            if 'min_modified' in filters:
                modified_time = datetime.datetime.fromisoformat(result['modified'])
                if modified_time < filters['min_modified']:
                    match = False
            
            # 按修改时间过滤
            if 'max_modified' in filters:
                modified_time = datetime.datetime.fromisoformat(result['modified'])
                if modified_time > filters['max_modified']:
                    match = False
            
            if match:
                filtered_results.append(result)
        
        return filtered_results
    
    def sort_results(self, results: List[Dict[str, Any]], 
                    sort_by: str = 'name', reverse: bool = False) -> List[Dict[str, Any]]:
        """
        排序搜索结果
        
        Args:
            results: 搜索结果列表
            sort_by: 排序字段（name, size, modified, created, accessed）
            reverse: 是否降序
            
        Returns:
            排序后的结果列表
        """
        if sort_by not in ['name', 'size', 'modified', 'created', 'accessed']:
            logger.warning(f"无效的排序字段: {sort_by}，使用默认字段 'name'")
            sort_by = 'name'
        
        # 对于时间字段，需要转换为datetime对象
        if sort_by in ['modified', 'created', 'accessed']:
            sorted_results = sorted(
                results, 
                key=lambda x: datetime.datetime.fromisoformat(x[sort_by]),
                reverse=reverse
            )
        else:
            sorted_results = sorted(results, key=lambda x: x[sort_by], reverse=reverse)
        
        return sorted_results
    
    def format_results(self, results: List[Dict[str, Any]], 
                      format_type: str = 'text') -> Union[str, List[Dict[str, Any]], str]:
        """
        格式化搜索结果
        
        Args:
            results: 搜索结果列表
            format_type: 格式化类型（text, json, csv）
            
        Returns:
            格式化后的结果
        """
        if format_type == 'json':
            return json.dumps(results, ensure_ascii=False, indent=2)
        
        elif format_type == 'csv':
            if not results:
                return ''
            
            # CSV 表头
            headers = ['path', 'name', 'size', 'modified', 'type', 'extension']
            csv_lines = [','.join(headers)]
            
            # CSV 数据行
            for result in results:
                row = [
                    f'"{result.get("path", "")}"',
                    f'"{result.get("name", "")}"',
                    str(result.get("size", 0)),
                    f'"{result.get("modified", "")}"',
                    f'"{result.get("type", "")}"',
                    f'"{result.get("extension", "")}"'
                ]
                csv_lines.append(','.join(row))
            
            return '\n'.join(csv_lines)
        
        else:  # text format
            text_lines = []
            text_lines.append(f"搜索结果 ({len(results)} 个文件):\n")
            
            for i, result in enumerate(results, 1):
                text_lines.append(f"{i}. {result.get('name', 'Unknown')}")
                text_lines.append(f"   路径: {result.get('path', 'Unknown')}")
                text_lines.append(f"   大小: {result.get('size', 0)} 字节")
                text_lines.append(f"   修改时间: {result.get('modified', 'Unknown')}")
                text_lines.append(f"   类型: {result.get('type', 'Unknown')} ({result.get('extension', '')})")
                text_lines.append("")
            
            return '\n'.join(text_lines)


def parse_size(size_str: str) -> int:
    """
    解析大小字符串为字节数
    
    Args:
        size_str: 大小字符串，如 "100MB", "2GB"
        
    Returns:
        字节数
    """
    size_units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024
    }
    
    size_str = size_str.strip().upper()
    
    # 匹配数字和单位
    match = re.match(r'^(\d+(?:\.\d+)?)([KMGT]?B)?$', size_str)
    if not match:
        raise ValueError(f"无效的大小格式: {size_str}")
    
    size, unit = match.groups()
    size = float(size)
    
    if unit is None:
        unit = 'B'
    
    return int(size * size_units[unit])


def parse_datetime(date_str: str) -> datetime.datetime:
    """
    解析日期时间字符串
    
    Args:
        date_str: 日期时间字符串
        
    Returns:
        datetime对象
    """
    # 尝试多种格式
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"无法解析日期时间: {date_str}")


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='文件搜索与索引工具')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # create 命令
    create_parser = subparsers.add_parser('create', help='创建文件索引')
    create_parser.add_argument('directory', help='要索引的目录')
    create_parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    create_parser.add_argument('-c', '--content', action='store_true', help='包含文件内容索引')
    create_parser.add_argument('-o', '--output', default='file_index.json', help='索引文件保存路径')
    create_parser.add_argument('-w', '--workers', type=int, default=4, help='工作线程数')
    
    # update 命令
    update_parser = subparsers.add_parser('update', help='更新文件索引')
    update_parser.add_argument('directory', help='要更新索引的目录')
    update_parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    update_parser.add_argument('-c', '--content', action='store_true', help='包含文件内容索引')
    update_parser.add_argument('-i', '--index', default='file_index.json', help='索引文件路径')
    update_parser.add_argument('-w', '--workers', type=int, default=4, help='工作线程数')
    
    # optimize 命令
    optimize_parser = subparsers.add_parser('optimize', help='优化文件索引')
    optimize_parser.add_argument('-i', '--index', default='file_index.json', help='索引文件路径')
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='显示索引信息')
    info_parser.add_argument('-i', '--index', default='file_index.json', help='索引文件路径')
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索文件')
    search_parser.add_argument('-i', '--index', default='file_index.json', help='索引文件路径')
    search_parser.add_argument('-n', '--name', help='按文件名搜索')
    search_parser.add_argument('-c', '--content', help='按文件内容搜索')
    search_parser.add_argument('-t', '--type', help='按文件类型搜索')
    search_parser.add_argument('-d', '--directory', help='按目录搜索')
    search_parser.add_argument('-r', '--regex', action='store_true', help='将名称搜索模式视为正则表达式')
    search_parser.add_argument('-s', '--case-sensitive', action='store_true', help='区分大小写')
    search_parser.add_argument('--min-size', help='最小文件大小 (如 100MB)')
    search_parser.add_argument('--max-size', help='最大文件大小 (如 1GB)')
    search_parser.add_argument('--min-modified', help='最小修改时间 (YYYY-MM-DD)')
    search_parser.add_argument('--max-modified', help='最大修改时间 (YYYY-MM-DD)')
    search_parser.add_argument('--sort-by', default='name', 
                            choices=['name', 'size', 'modified', 'created', 'accessed'],
                            help='排序字段')
    search_parser.add_argument('--reverse', action='store_true', help='降序排序')
    search_parser.add_argument('--format', default='text', choices=['text', 'json', 'csv'],
                            help='输出格式')
    search_parser.add_argument('--output', help='输出文件路径')
    
    # 日志级别
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志')
    
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
    
    if args.command == 'create':
        # 创建索引
        indexer = FileIndexer(args.output)
        indexed_count = indexer.create_index(
            args.directory, 
            recursive=args.recursive, 
            include_content=args.content,
            max_workers=args.workers
        )
        print(f"索引创建完成，成功索引 {indexed_count} 个文件")
    
    elif args.command == 'update':
        # 更新索引
        indexer = FileIndexer(args.index)
        stats = indexer.update_index(
            args.directory,
            recursive=args.recursive,
            include_content=args.content,
            max_workers=args.workers
        )
        print(f"索引更新完成: 新增 {stats['added']}, 更新 {stats['updated']}, 删除 {stats['removed']}")
    
    elif args.command == 'optimize':
        # 优化索引
        indexer = FileIndexer(args.index)
        indexer.optimize_index()
        print("索引优化完成")
    
    elif args.command == 'info':
        # 显示索引信息
        indexer = FileIndexer(args.index)
        info = indexer.get_index_info()
        print("索引信息:")
        print(f"  创建时间: {info['created_at']}")
        print(f"  最后更新: {info['last_updated']}")
        print(f"  版本: {info['version']}")
        print(f"  总文件数: {info['total_files']}")
        print(f"  关键词数: {info['keyword_count']}")
        print(f"  目录数: {info['directory_count']}")
        print("  文件类型统计:")
        for file_type, count in info['file_types'].items():
            print(f"    - {file_type}: {count}")
        print("  索引目录:")
        for directory in info['indexed_directories']:
            print(f"    - {directory}")
    
    elif args.command == 'search':
        # 搜索文件
        indexer = FileIndexer(args.index)
        searcher = FileSearcher(indexer)
        
        # 执行搜索
        results = []
        
        if args.name:
            results = searcher.search_by_name(
                args.name, 
                regex=args.regex, 
                case_sensitive=args.case_sensitive
            )
        elif args.content:
            results = searcher.search_by_content(
                args.content, 
                case_sensitive=args.case_sensitive
            )
        elif args.type:
            results = searcher.search_by_type(args.type)
        elif args.directory:
            results = searcher.search_by_directory(args.directory)
        else:
            print("错误: 必须指定至少一个搜索条件 (-n, -c, -t 或 -d)")
            return
        
        # 应用过滤条件
        filters = {}
        
        if args.min_size:
            try:
                filters['min_size'] = parse_size(args.min_size)
            except ValueError as e:
                print(f"错误: {e}")
                return
        
        if args.max_size:
            try:
                filters['max_size'] = parse_size(args.max_size)
            except ValueError as e:
                print(f"错误: {e}")
                return
        
        if args.min_modified:
            try:
                filters['min_modified'] = parse_datetime(args.min_modified)
            except ValueError as e:
                print(f"错误: {e}")
                return
        
        if args.max_modified:
            try:
                filters['max_modified'] = parse_datetime(args.max_modified)
            except ValueError as e:
                print(f"错误: {e}")
                return
        
        if filters:
            results = searcher.filter_results(results, filters)
        
        # 排序结果
        results = searcher.sort_results(results, sort_by=args.sort_by, reverse=args.reverse)
        
        # 格式化结果
        formatted_results = searcher.format_results(results, format_type=args.format)
        
        # 输出结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(formatted_results)
            print(f"搜索结果已保存到 {args.output}")
        else:
            print(formatted_results)
    
    else:
        print("错误: 必须指定命令。使用 -h 查看帮助")


if __name__ == '__main__':
    main()
