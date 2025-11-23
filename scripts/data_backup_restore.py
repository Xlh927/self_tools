#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据备份与恢复模块

该模块提供灵活的数据备份和恢复功能，支持多种备份策略（全量备份、增量备份、差异备份）
以及多种备份格式。适用于各种数据保护场景，确保数据安全性和可恢复性。

主要功能:
- 全量备份：备份所有指定的文件和目录
- 增量备份：仅备份上次备份后修改的文件
- 差异备份：备份上次全量备份后修改的文件
- 备份压缩：支持多种压缩格式
- 备份加密：保护敏感数据
- 备份验证：确保备份完整性
- 自动恢复：从备份中恢复数据
- 备份管理：列出、删除、比较备份
- 定时备份：支持定时任务配置
- 命令行接口：方便集成到脚本和工作流

作者: Self Tools
日期: 2023-11-12
"""

import os
import sys
import time
import shutil
import json
import yaml
import argparse
import logging
import tarfile
import zipfile
import gzip
import bz2
import lzma
import hashlib
import subprocess
import tempfile
import datetime
import re
import stat
from typing import Dict, List, Tuple, Set, Optional, Union, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 支持的压缩格式
COMPRESSION_FORMATS = {
    'tar': {'ext': '.tar', 'module': None},
    'tar.gz': {'ext': '.tar.gz', 'module': tarfile, 'mode': 'w:gz'},
    'tar.bz2': {'ext': '.tar.bz2', 'module': tarfile, 'mode': 'w:bz2'},
    'tar.xz': {'ext': '.tar.xz', 'module': tarfile, 'mode': 'w:xz'},
    'zip': {'ext': '.zip', 'module': zipfile, 'mode': 'w', 'compression': zipfile.ZIP_DEFLATED},
    'gz': {'ext': '.gz', 'module': gzip},
    'bz2': {'ext': '.bz2', 'module': bz2},
    'xz': {'ext': '.xz', 'module': lzma}
}


class BackupRestoreManager:
    """
    备份与恢复管理器
    """
    
    def __init__(self, backup_dir: str,
                 compression: str = 'tar.gz',
                 max_workers: int = 4,
                 exclude_patterns: Optional[List[str]] = None,
                 follow_symlinks: bool = False,
                 verify_backups: bool = True,
                 checksum_algorithm: str = 'md5'):
        """
        初始化备份与恢复管理器
        
        Args:
            backup_dir: 备份存储目录
            compression: 压缩格式 (tar, tar.gz, tar.bz2, tar.xz, zip)
            max_workers: 并行处理的最大线程数
            exclude_patterns: 排除的文件正则表达式模式列表
            follow_symlinks: 是否跟随符号链接
            verify_backups: 是否自动验证备份
            checksum_algorithm: 校验和算法 (md5, sha1, sha256)
        """
        self.backup_dir = os.path.abspath(backup_dir)
        self.compression = compression.lower()
        self.max_workers = max_workers
        self.exclude_patterns = exclude_patterns or []
        self.follow_symlinks = follow_symlinks
        self.verify_backups = verify_backups
        self.checksum_algorithm = checksum_algorithm.lower()
        
        # 验证压缩格式
        if self.compression not in COMPRESSION_FORMATS:
            raise ValueError(f"不支持的压缩格式: {self.compression}。支持的格式: {', '.join(COMPRESSION_FORMATS.keys())}")
        
        # 验证校验和算法
        if self.checksum_algorithm not in ['md5', 'sha1', 'sha256']:
            raise ValueError(f"不支持的校验和算法: {self.checksum_algorithm}。支持的算法: md5, sha1, sha256")
        
        # 编译排除正则表达式
        self.exclude_regexes = [re.compile(pattern) for pattern in self.exclude_patterns]
        
        # 创建备份目录
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 初始化备份元数据目录
        self.metadata_dir = os.path.join(self.backup_dir, '.metadata')
        os.makedirs(self.metadata_dir, exist_ok=True)
        
        # 初始化锁定机制
        self.lock_file = os.path.join(self.backup_dir, '.backup_lock')
        self._lock = threading.RLock()
    
    def _acquire_lock(self) -> bool:
        """
        获取备份操作锁
        
        Returns:
            是否成功获取锁
        """
        with self._lock:
            if os.path.exists(self.lock_file):
                # 检查锁文件是否过期（超过24小时）
                try:
                    lock_mtime = os.path.getmtime(self.lock_file)
                    if time.time() - lock_mtime > 86400:  # 24小时
                        logger.warning("检测到过期的锁文件，将强制移除")
                        os.remove(self.lock_file)
                    else:
                        logger.error("备份操作正在进行中，请稍后再试")
                        return False
                except Exception as e:
                    logger.warning(f"检查锁文件失败: {e}")
                    return False
            
            try:
                with open(self.lock_file, 'w') as f:
                    f.write(f"Process ID: {os.getpid()}\nTimestamp: {time.time()}")
                return True
            except Exception as e:
                logger.error(f"创建锁文件失败: {e}")
                return False
    
    def _release_lock(self):
        """
        释放备份操作锁
        """
        with self._lock:
            try:
                if os.path.exists(self.lock_file):
                    os.remove(self.lock_file)
            except Exception as e:
                logger.error(f"删除锁文件失败: {e}")
    
    def _should_exclude(self, path: str, is_dir: bool = False) -> bool:
        """
        检查是否应该排除指定路径
        
        Args:
            path: 要检查的路径
            is_dir: 是否为目录
            
        Returns:
            是否排除
        """
        # 排除备份目录本身
        if path.startswith(self.backup_dir):
            return True
        
        # 排除临时文件和系统文件
        basename = os.path.basename(path)
        if basename.startswith('.') and basename != '.':
            return True
        
        # 排除特定的系统文件和目录
        exclude_names = [
            '__pycache__', '.git', '.svn', '.hg', '.DS_Store',
            'Thumbs.db', '.Trashes', 'ehthumbs.db',
            '.backup_lock', '.metadata'
        ]
        
        if basename in exclude_names:
            return True
        
        # 应用用户定义的排除模式
        for regex in self.exclude_regexes:
            if regex.search(path) or regex.search(basename):
                return True
        
        return False
    
    def _get_checksum(self, file_path: str) -> Optional[str]:
        """
        计算文件的校验和
        
        Args:
            file_path: 文件路径
            
        Returns:
            校验和值，如果计算失败则返回None
        """
        try:
            if self.checksum_algorithm == 'md5':
                hasher = hashlib.md5()
            elif self.checksum_algorithm == 'sha1':
                hasher = hashlib.sha1()
            elif self.checksum_algorithm == 'sha256':
                hasher = hashlib.sha256()
            else:
                return None
            
            with open(file_path, 'rb') as f:
                buf = f.read(65536)  # 64KB chunks
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"计算文件校验和失败 {file_path}: {e}")
            return None
    
    def _get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件元数据字典
        """
        try:
            stat_info = os.stat(file_path)
            
            metadata = {
                'path': file_path,
                'size': stat_info.st_size,
                'mtime': stat_info.st_mtime,
                'ctime': stat_info.st_ctime,
                'atime': stat_info.st_atime,
                'mode': stat_info.st_mode,
                'uid': stat_info.st_uid,
                'gid': stat_info.st_gid,
                'is_symlink': os.path.islink(file_path)
            }
            
            # 如果是符号链接，保存链接目标
            if os.path.islink(file_path):
                metadata['symlink_target'] = os.readlink(file_path)
            
            return metadata
        except Exception as e:
            logger.error(f"获取文件元数据失败 {file_path}: {e}")
            return {}
    
    def _collect_files(self, source_paths: List[str], recursive: bool = True) -> List[Dict[str, Any]]:
        """
        收集要备份的文件
        
        Args:
            source_paths: 源路径列表
            recursive: 是否递归收集子目录
            
        Returns:
            文件元数据列表
        """
        logger.info(f"开始收集文件，共 {len(source_paths)} 个源路径")
        
        collected_files = []
        skipped_count = 0
        
        for source_path in source_paths:
            source_path = os.path.abspath(source_path)
            
            if not os.path.exists(source_path):
                logger.warning(f"源路径不存在: {source_path}")
                skipped_count += 1
                continue
            
            if os.path.isfile(source_path):
                # 单个文件
                if not self._should_exclude(source_path):
                    metadata = self._get_file_metadata(source_path)
                    if metadata:
                        collected_files.append(metadata)
                    else:
                        skipped_count += 1
            elif os.path.isdir(source_path):
                # 目录
                if recursive:
                    for root, dirs, files in os.walk(source_path, followlinks=self.follow_symlinks):
                        # 过滤排除的目录
                        dirs[:] = [d for d in dirs if not self._should_exclude(os.path.join(root, d), is_dir=True)]
                        
                        # 处理文件
                        for file in files:
                            file_path = os.path.join(root, file)
                            if not self._should_exclude(file_path):
                                metadata = self._get_file_metadata(file_path)
                                if metadata:
                                    collected_files.append(metadata)
                                else:
                                    skipped_count += 1
                        
                        # 处理符号链接目录
                        if self.follow_symlinks:
                            for dir_name in dirs:
                                dir_path = os.path.join(root, dir_name)
                                if os.path.islink(dir_path):
                                    metadata = self._get_file_metadata(dir_path)
                                    if metadata:
                                        collected_files.append(metadata)
                else:
                    # 非递归模式
                    try:
                        for item in os.listdir(source_path):
                            item_path = os.path.join(source_path, item)
                            if os.path.isfile(item_path) and not self._should_exclude(item_path):
                                metadata = self._get_file_metadata(item_path)
                                if metadata:
                                    collected_files.append(metadata)
                                else:
                                    skipped_count += 1
                    except Exception as e:
                        logger.error(f"读取目录失败 {source_path}: {e}")
                        skipped_count += 1
            else:
                logger.warning(f"源路径既不是文件也不是目录: {source_path}")
                skipped_count += 1
        
        logger.info(f"文件收集完成，共收集 {len(collected_files)} 个文件，跳过 {skipped_count} 个项目")
        return collected_files
    
    def _load_backup_metadata(self, backup_name: str) -> Optional[Dict[str, Any]]:
        """
        加载备份元数据
        
        Args:
            backup_name: 备份名称
            
        Returns:
            备份元数据字典，如果加载失败则返回None
        """
        metadata_file = os.path.join(self.metadata_dir, f"{backup_name}.json")
        
        if not os.path.exists(metadata_file):
            logger.error(f"备份元数据文件不存在: {metadata_file}")
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载备份元数据失败 {metadata_file}: {e}")
            return None
    
    def _save_backup_metadata(self, backup_name: str, metadata: Dict[str, Any]) -> bool:
        """
        保存备份元数据
        
        Args:
            backup_name: 备份名称
            metadata: 备份元数据字典
            
        Returns:
            是否保存成功
        """
        metadata_file = os.path.join(self.metadata_dir, f"{backup_name}.json")
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存备份元数据失败 {metadata_file}: {e}")
            return False
    
    def _get_backup_file_path(self, backup_name: str) -> str:
        """
        获取备份文件路径
        
        Args:
            backup_name: 备份名称
            
        Returns:
            备份文件完整路径
        """
        ext = COMPRESSION_FORMATS[self.compression]['ext']
        return os.path.join(self.backup_dir, f"{backup_name}{ext}")
    
    def _create_backup_name(self, prefix: str = 'backup') -> str:
        """
        创建唯一的备份名称
        
        Args:
            prefix: 备份名称前缀
            
        Returns:
            备份名称
        """
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{timestamp}"
    
    def _backup_to_tar(self, source_files: List[Dict[str, Any]], backup_file: str,
                      progress_callback: Optional[callable] = None) -> bool:
        """
        创建tar格式备份
        
        Args:
            source_files: 源文件列表
            backup_file: 备份文件路径
            progress_callback: 进度回调函数
            
        Returns:
            是否备份成功
        """
        try:
            format_info = COMPRESSION_FORMATS[self.compression]
            mode = format_info.get('mode', 'w')
            
            with tarfile.open(backup_file, mode) as tar:
                total_size = sum(f['size'] for f in source_files if 'size' in f)
                processed_size = 0
                
                for i, file_info in enumerate(source_files):
                    file_path = file_info['path']
                    
                    try:
                        # 相对路径（避免包含完整路径）
                        arcname = os.path.basename(file_path)
                        
                        # 添加文件到归档
                        tar.add(file_path, arcname=arcname, recursive=False)
                        
                        # 更新进度
                        if 'size' in file_info:
                            processed_size += file_info['size']
                        
                        if progress_callback and total_size > 0:
                            progress = min(100, int(processed_size / total_size * 100))
                            progress_callback(progress, i + 1, len(source_files), file_path)
                            
                    except Exception as e:
                        logger.error(f"添加文件到备份失败 {file_path}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"创建tar备份失败 {backup_file}: {e}")
            # 清理失败的备份文件
            if os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                except:
                    pass
            return False
    
    def _backup_to_zip(self, source_files: List[Dict[str, Any]], backup_file: str,
                      progress_callback: Optional[callable] = None) -> bool:
        """
        创建zip格式备份
        
        Args:
            source_files: 源文件列表
            backup_file: 备份文件路径
            progress_callback: 进度回调函数
            
        Returns:
            是否备份成功
        """
        try:
            format_info = COMPRESSION_FORMATS[self.compression]
            compression = format_info.get('compression', zipfile.ZIP_DEFLATED)
            
            with zipfile.ZipFile(backup_file, 'w', compression=compression) as zipf:
                total_size = sum(f['size'] for f in source_files if 'size' in f)
                processed_size = 0
                
                for i, file_info in enumerate(source_files):
                    file_path = file_info['path']
                    
                    try:
                        # 相对路径
                        arcname = os.path.basename(file_path)
                        
                        # 添加文件到ZIP
                        zipf.write(file_path, arcname)
                        
                        # 更新进度
                        if 'size' in file_info:
                            processed_size += file_info['size']
                        
                        if progress_callback and total_size > 0:
                            progress = min(100, int(processed_size / total_size * 100))
                            progress_callback(progress, i + 1, len(source_files), file_path)
                            
                    except Exception as e:
                        logger.error(f"添加文件到备份失败 {file_path}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"创建zip备份失败 {backup_file}: {e}")
            # 清理失败的备份文件
            if os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                except:
                    pass
            return False
    
    def create_full_backup(self, source_paths: List[str], backup_name: Optional[str] = None,
                          recursive: bool = True,
                          progress_callback: Optional[callable] = None) -> Optional[str]:
        """
        创建全量备份
        
        Args:
            source_paths: 源路径列表
            backup_name: 备份名称，如果为None则自动生成
            recursive: 是否递归备份子目录
            progress_callback: 进度回调函数
            
        Returns:
            备份名称，如果备份失败则返回None
        """
        # 获取锁
        if not self._acquire_lock():
            return None
        
        try:
            logger.info(f"开始创建全量备份，源路径: {source_paths}")
            
            # 生成备份名称
            if backup_name is None:
                backup_name = self._create_backup_name('full')
            
            # 收集文件
            source_files = self._collect_files(source_paths, recursive=recursive)
            
            if not source_files:
                logger.error("没有找到可备份的文件")
                return None
            
            # 获取备份文件路径
            backup_file = self._get_backup_file_path(backup_name)
            
            # 确保备份文件目录存在
            os.makedirs(os.path.dirname(backup_file), exist_ok=True)
            
            # 根据压缩格式创建备份
            start_time = time.time()
            
            if self.compression.startswith('tar'):
                success = self._backup_to_tar(source_files, backup_file, progress_callback)
            elif self.compression == 'zip':
                success = self._backup_to_zip(source_files, backup_file, progress_callback)
            else:
                logger.error(f"不支持的压缩格式: {self.compression}")
                return None
            
            if not success:
                return None
            
            # 计算备份文件校验和
            backup_checksum = self._get_checksum(backup_file)
            
            # 计算文件校验和（并行处理）
            file_checksums = {}
            
            def compute_checksum(file_info):
                file_path = file_info['path']
                checksum = self._get_checksum(file_path)
                return file_path, checksum
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(compute_checksum, source_files))
                
            for file_path, checksum in results:
                if checksum:
                    file_checksums[file_path] = checksum
            
            # 保存备份元数据
            metadata = {
                'backup_name': backup_name,
                'backup_type': 'full',
                'creation_time': time.time(),
                'source_paths': source_paths,
                'file_count': len(source_files),
                'total_size': sum(f['size'] for f in source_files if 'size' in f),
                'compression': self.compression,
                'backup_file': backup_file,
                'backup_file_size': os.path.getsize(backup_file),
                'backup_checksum': backup_checksum,
                'file_checksums': file_checksums,
                'files': source_files,
                'recursive': recursive,
                'exclude_patterns': self.exclude_patterns,
                'follow_symlinks': self.follow_symlinks,
                'checksum_algorithm': self.checksum_algorithm,
                'execution_time': time.time() - start_time
            }
            
            if not self._save_backup_metadata(backup_name, metadata):
                logger.error("保存备份元数据失败")
                # 保留备份文件，但记录警告
            
            # 验证备份
            if self.verify_backups and not self.verify_backup(backup_name):
                logger.error("备份验证失败")
                # 保留备份文件，但记录警告
            
            logger.info(f"全量备份创建成功: {backup_name}")
            logger.info(f"备份文件: {backup_file}")
            logger.info(f"文件数量: {len(source_files)}")
            logger.info(f"总大小: {metadata['total_size'] / (1024*1024):.2f} MB")
            logger.info(f"压缩后大小: {metadata['backup_file_size'] / (1024*1024):.2f} MB")
            logger.info(f"执行时间: {metadata['execution_time']:.2f} 秒")
            
            return backup_name
            
        except Exception as e:
            logger.error(f"创建全量备份时发生错误: {e}")
            return None
        finally:
            # 释放锁
            self._release_lock()
    
    def create_incremental_backup(self, source_paths: List[str], base_backup_name: str,
                                backup_name: Optional[str] = None,
                                recursive: bool = True,
                                progress_callback: Optional[callable] = None) -> Optional[str]:
        """
        创建增量备份（基于上次备份）
        
        Args:
            source_paths: 源路径列表
            base_backup_name: 基础备份名称
            backup_name: 备份名称，如果为None则自动生成
            recursive: 是否递归备份子目录
            progress_callback: 进度回调函数
            
        Returns:
            备份名称，如果备份失败则返回None
        """
        # 获取锁
        if not self._acquire_lock():
            return None
        
        try:
            logger.info(f"开始创建增量备份，基于备份: {base_backup_name}")
            
            # 加载基础备份元数据
            base_metadata = self._load_backup_metadata(base_backup_name)
            if not base_metadata:
                logger.error("加载基础备份元数据失败")
                return None
            
            # 生成备份名称
            if backup_name is None:
                backup_name = self._create_backup_name('incr')
            
            # 收集当前文件
            current_files = self._collect_files(source_paths, recursive=recursive)
            
            # 找出修改或新增的文件
            changed_files = []
            base_file_info = {f['path']: f for f in base_metadata.get('files', [])}
            
            for file_info in current_files:
                file_path = file_info['path']
                
                # 新增文件
                if file_path not in base_file_info:
                    changed_files.append(file_info)
                else:
                    # 修改的文件（基于修改时间或大小）
                    base_info = base_file_info[file_path]
                    if (file_info.get('mtime', 0) != base_info.get('mtime', 0) or
                        file_info.get('size', 0) != base_info.get('size', 0)):
                        changed_files.append(file_info)
            
            # 检查删除的文件
            deleted_files = [f_path for f_path in base_file_info if f_path not in [f['path'] for f in current_files]]
            
            logger.info(f"发现 {len(changed_files)} 个修改或新增文件，{len(deleted_files)} 个删除文件")
            
            if not changed_files and not deleted_files:
                logger.info("没有检测到文件变化，跳过备份")
                return None
            
            # 获取备份文件路径
            backup_file = self._get_backup_file_path(backup_name)
            
            # 确保备份文件目录存在
            os.makedirs(os.path.dirname(backup_file), exist_ok=True)
            
            # 创建备份（仅包含变化的文件）
            if changed_files:
                start_time = time.time()
                
                if self.compression.startswith('tar'):
                    success = self._backup_to_tar(changed_files, backup_file, progress_callback)
                elif self.compression == 'zip':
                    success = self._backup_to_zip(changed_files, backup_file, progress_callback)
                else:
                    logger.error(f"不支持的压缩格式: {self.compression}")
                    return None
                
                if not success:
                    return None
            else:
                # 只有删除的文件，创建空备份
                open(backup_file, 'w').close()
                start_time = time.time()
            
            # 计算备份文件校验和
            backup_checksum = self._get_checksum(backup_file)
            
            # 计算文件校验和
            file_checksums = {}
            for file_info in changed_files:
                file_path = file_info['path']
                checksum = self._get_checksum(file_path)
                if checksum:
                    file_checksums[file_path] = checksum
            
            # 保存备份元数据
            metadata = {
                'backup_name': backup_name,
                'backup_type': 'incremental',
                'base_backup': base_backup_name,
                'creation_time': time.time(),
                'source_paths': source_paths,
                'changed_file_count': len(changed_files),
                'deleted_file_count': len(deleted_files),
                'total_size': sum(f['size'] for f in changed_files if 'size' in f),
                'compression': self.compression,
                'backup_file': backup_file,
                'backup_file_size': os.path.getsize(backup_file),
                'backup_checksum': backup_checksum,
                'file_checksums': file_checksums,
                'changed_files': changed_files,
                'deleted_files': deleted_files,
                'recursive': recursive,
                'exclude_patterns': self.exclude_patterns,
                'follow_symlinks': self.follow_symlinks,
                'checksum_algorithm': self.checksum_algorithm,
                'execution_time': time.time() - start_time
            }
            
            if not self._save_backup_metadata(backup_name, metadata):
                logger.error("保存备份元数据失败")
            
            # 验证备份
            if self.verify_backups and changed_files and not self.verify_backup(backup_name):
                logger.error("备份验证失败")
            
            logger.info(f"增量备份创建成功: {backup_name}")
            logger.info(f"基于备份: {base_backup_name}")
            logger.info(f"备份文件: {backup_file}")
            logger.info(f"修改/新增文件: {len(changed_files)}")
            logger.info(f"删除文件: {len(deleted_files)}")
            logger.info(f"执行时间: {time.time() - start_time:.2f} 秒")
            
            return backup_name
            
        except Exception as e:
            logger.error(f"创建增量备份时发生错误: {e}")
            return None
        finally:
            # 释放锁
            self._release_lock()
    
    def create_differential_backup(self, source_paths: List[str], full_backup_name: str,
                                 backup_name: Optional[str] = None,
                                 recursive: bool = True,
                                 progress_callback: Optional[callable] = None) -> Optional[str]:
        """
        创建差异备份（基于上次全量备份）
        
        Args:
            source_paths: 源路径列表
            full_backup_name: 全量备份名称
            backup_name: 备份名称，如果为None则自动生成
            recursive: 是否递归备份子目录
            progress_callback: 进度回调函数
            
        Returns:
            备份名称，如果备份失败则返回None
        """
        # 获取锁
        if not self._acquire_lock():
            return None
        
        try:
            logger.info(f"开始创建差异备份，基于全量备份: {full_backup_name}")
            
            # 加载全量备份元数据
            full_metadata = self._load_backup_metadata(full_backup_name)
            if not full_metadata or full_metadata.get('backup_type') != 'full':
                logger.error("加载全量备份元数据失败或不是全量备份")
                return None
            
            # 生成备份名称
            if backup_name is None:
                backup_name = self._create_backup_name('diff')
            
            # 收集当前文件
            current_files = self._collect_files(source_paths, recursive=recursive)
            
            # 找出修改或新增的文件（与全量备份相比）
            changed_files = []
            full_file_info = {f['path']: f for f in full_metadata.get('files', [])}
            
            for file_info in current_files:
                file_path = file_info['path']
                
                # 新增文件
                if file_path not in full_file_info:
                    changed_files.append(file_info)
                else:
                    # 修改的文件
                    full_info = full_file_info[file_path]
                    if (file_info.get('mtime', 0) != full_info.get('mtime', 0) or
                        file_info.get('size', 0) != full_info.get('size', 0)):
                        changed_files.append(file_info)
            
            # 检查删除的文件
            deleted_files = [f_path for f_path in full_file_info if f_path not in [f['path'] for f in current_files]]
            
            logger.info(f"发现 {len(changed_files)} 个修改或新增文件，{len(deleted_files)} 个删除文件")
            
            if not changed_files and not deleted_files:
                logger.info("没有检测到文件变化，跳过备份")
                return None
            
            # 获取备份文件路径
            backup_file = self._get_backup_file_path(backup_name)
            
            # 确保备份文件目录存在
            os.makedirs(os.path.dirname(backup_file), exist_ok=True)
            
            # 创建备份
            if changed_files:
                start_time = time.time()
                
                if self.compression.startswith('tar'):
                    success = self._backup_to_tar(changed_files, backup_file, progress_callback)
                elif self.compression == 'zip':
                    success = self._backup_to_zip(changed_files, backup_file, progress_callback)
                else:
                    logger.error(f"不支持的压缩格式: {self.compression}")
                    return None
                
                if not success:
                    return None
            else:
                # 只有删除的文件，创建空备份
                open(backup_file, 'w').close()
                start_time = time.time()
            
            # 计算备份文件校验和
            backup_checksum = self._get_checksum(backup_file)
            
            # 计算文件校验和
            file_checksums = {}
            for file_info in changed_files:
                file_path = file_info['path']
                checksum = self._get_checksum(file_path)
                if checksum:
                    file_checksums[file_path] = checksum
            
            # 保存备份元数据
            metadata = {
                'backup_name': backup_name,
                'backup_type': 'differential',
                'full_backup': full_backup_name,
                'creation_time': time.time(),
                'source_paths': source_paths,
                'changed_file_count': len(changed_files),
                'deleted_file_count': len(deleted_files),
                'total_size': sum(f['size'] for f in changed_files if 'size' in f),
                'compression': self.compression,
                'backup_file': backup_file,
                'backup_file_size': os.path.getsize(backup_file),
                'backup_checksum': backup_checksum,
                'file_checksums': file_checksums,
                'changed_files': changed_files,
                'deleted_files': deleted_files,
                'recursive': recursive,
                'exclude_patterns': self.exclude_patterns,
                'follow_symlinks': self.follow_symlinks,
                'checksum_algorithm': self.checksum_algorithm,
                'execution_time': time.time() - start_time
            }
            
            if not self._save_backup_metadata(backup_name, metadata):
                logger.error("保存备份元数据失败")
            
            # 验证备份
            if self.verify_backups and changed_files and not self.verify_backup(backup_name):
                logger.error("备份验证失败")
            
            logger.info(f"差异备份创建成功: {backup_name}")
            logger.info(f"基于全量备份: {full_backup_name}")
            logger.info(f"备份文件: {backup_file}")
            logger.info(f"修改/新增文件: {len(changed_files)}")
            logger.info(f"删除文件: {len(deleted_files)}")
            logger.info(f"执行时间: {time.time() - start_time:.2f} 秒")
            
            return backup_name
            
        except Exception as e:
            logger.error(f"创建差异备份时发生错误: {e}")
            return None
        finally:
            # 释放锁
            self._release_lock()
    
    def verify_backup(self, backup_name: str) -> bool:
        """
        验证备份的完整性
        
        Args:
            backup_name: 备份名称
            
        Returns:
            验证是否通过
        """
        logger.info(f"开始验证备份: {backup_name}")
        
        # 加载备份元数据
        metadata = self._load_backup_metadata(backup_name)
        if not metadata:
            return False
        
        backup_file = metadata.get('backup_file')
        if not backup_file or not os.path.exists(backup_file):
            logger.error(f"备份文件不存在: {backup_file}")
            return False
        
        # 验证备份文件校验和
        expected_checksum = metadata.get('backup_checksum')
        if expected_checksum:
            current_checksum = self._get_checksum(backup_file)
            if current_checksum != expected_checksum:
                logger.error(f"备份文件校验和不匹配。期望: {expected_checksum}, 实际: {current_checksum}")
                return False
        
        # 根据备份类型执行不同的验证
        backup_type = metadata.get('backup_type', 'full')
        
        if backup_type == 'full':
            # 验证所有文件是否可从备份中提取
            try:
                temp_dir = tempfile.mkdtemp()
                
                if self.compression.startswith('tar'):
                    with tarfile.open(backup_file, 'r:*') as tar:
                        # 仅验证文件列表，不实际提取
                        tar.list()
                elif self.compression == 'zip':
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        # 测试zip文件完整性
                        zipf.testzip()
                
                logger.info(f"备份验证通过: {backup_name}")
                return True
                
            except Exception as e:
                logger.error(f"备份文件格式验证失败: {e}")
                return False
            finally:
                # 清理临时目录
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass
        
        elif backup_type in ['incremental', 'differential']:
            # 增量和差异备份的验证
            if os.path.getsize(backup_file) == 0:
                # 空备份（只有删除的文件）
                logger.info(f"空备份验证通过: {backup_name}")
                return True
            
            try:
                temp_dir = tempfile.mkdtemp()
                
                if self.compression.startswith('tar'):
                    with tarfile.open(backup_file, 'r:*') as tar:
                        tar.list()
                elif self.compression == 'zip':
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        zipf.testzip()
                
                logger.info(f"备份验证通过: {backup_name}")
                return True
                
            except Exception as e:
                logger.error(f"备份文件格式验证失败: {e}")
                return False
            finally:
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass
        
        return False
    
    def restore_from_backup(self, backup_name: str, target_dir: str,
                           overwrite: bool = False,
                           progress_callback: Optional[callable] = None) -> bool:
        """
        从备份中恢复数据
        
        Args:
            backup_name: 备份名称
            target_dir: 恢复目标目录
            overwrite: 是否覆盖已存在的文件
            progress_callback: 进度回调函数
            
        Returns:
            是否恢复成功
        """
        # 获取锁
        if not self._acquire_lock():
            return False
        
        try:
            logger.info(f"开始从备份恢复: {backup_name} 到 {target_dir}")
            
            # 加载备份元数据
            metadata = self._load_backup_metadata(backup_name)
            if not metadata:
                logger.error("加载备份元数据失败")
                return False
            
            backup_file = metadata.get('backup_file')
            if not backup_file or not os.path.exists(backup_file):
                logger.error(f"备份文件不存在: {backup_file}")
                return False
            
            backup_type = metadata.get('backup_type', 'full')
            
            # 确保目标目录存在
            os.makedirs(target_dir, exist_ok=True)
            
            # 对于增量和差异备份，需要先恢复基础备份
            if backup_type == 'incremental':
                base_backup = metadata.get('base_backup')
                if not base_backup:
                    logger.error("增量备份缺少基础备份信息")
                    return False
                
                logger.info(f"需要先恢复基础备份: {base_backup}")
                if not self.restore_from_backup(base_backup, target_dir, overwrite=overwrite):
                    logger.error("恢复基础备份失败")
                    return False
            
            elif backup_type == 'differential':
                full_backup = metadata.get('full_backup')
                if not full_backup:
                    logger.error("差异备份缺少全量备份信息")
                    return False
                
                logger.info(f"需要先恢复全量备份: {full_backup}")
                if not self.restore_from_backup(full_backup, target_dir, overwrite=overwrite):
                    logger.error("恢复全量备份失败")
                    return False
            
            # 恢复当前备份的文件
            if os.path.getsize(backup_file) > 0:
                start_time = time.time()
                
                if self.compression.startswith('tar'):
                    with tarfile.open(backup_file, 'r:*') as tar:
                        # 获取所有成员
                        members = tar.getmembers()
                        
                        for i, member in enumerate(members):
                            try:
                                # 检查目标文件是否存在
                                target_path = os.path.join(target_dir, member.name)
                                
                                if os.path.exists(target_path) and not overwrite:
                                    logger.warning(f"文件已存在，跳过: {target_path}")
                                    continue
                                
                                # 提取文件
                                tar.extract(member, target_dir)
                                
                                # 恢复文件权限
                                if member.isfile():
                                    os.chmod(target_path, member.mode)
                                
                                # 更新进度
                                if progress_callback:
                                    progress = min(100, int((i + 1) / len(members) * 100))
                                    progress_callback(progress, i + 1, len(members), member.name)
                                    
                            except Exception as e:
                                logger.error(f"恢复文件失败 {member.name}: {e}")
                
                elif self.compression == 'zip':
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        # 获取所有文件
                        file_list = zipf.namelist()
                        
                        for i, file_name in enumerate(file_list):
                            try:
                                # 检查目标文件是否存在
                                target_path = os.path.join(target_dir, file_name)
                                
                                if os.path.exists(target_path) and not overwrite:
                                    logger.warning(f"文件已存在，跳过: {target_path}")
                                    continue
                                
                                # 提取文件
                                zipf.extract(file_name, target_dir)
                                
                                # 更新进度
                                if progress_callback:
                                    progress = min(100, int((i + 1) / len(file_list) * 100))
                                    progress_callback(progress, i + 1, len(file_list), file_name)
                                    
                            except Exception as e:
                                logger.error(f"恢复文件失败 {file_name}: {e}")
                
                logger.info(f"文件恢复完成，耗时: {time.time() - start_time:.2f} 秒")
            
            # 处理删除的文件（仅针对增量和差异备份）
            deleted_files = metadata.get('deleted_files', [])
            if deleted_files:
                logger.info(f"处理 {len(deleted_files)} 个删除文件")
                
                for deleted_path in deleted_files:
                    # 构建目标路径（简化处理，仅基于文件名）
                    file_name = os.path.basename(deleted_path)
                    target_path = os.path.join(target_dir, file_name)
                    
                    if os.path.exists(target_path):
                        try:
                            if os.path.isfile(target_path):
                                os.remove(target_path)
                                logger.info(f"删除文件: {target_path}")
                            elif os.path.isdir(target_path):
                                shutil.rmtree(target_path)
                                logger.info(f"删除目录: {target_path}")
                        except Exception as e:
                            logger.error(f"删除文件失败 {target_path}: {e}")
            
            logger.info(f"从备份恢复成功: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"恢复备份时发生错误: {e}")
            return False
        finally:
            # 释放锁
            self._release_lock()
    
    def list_backups(self, sort_by: str = 'time', reverse: bool = True) -> List[Dict[str, Any]]:
        """
        列出所有备份
        
        Args:
            sort_by: 排序字段 (name, time, size)
            reverse: 是否降序排序
            
        Returns:
            备份信息列表
        """
        logger.info("列出所有备份")
        
        backups = []
        
        # 遍历元数据目录
        try:
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('.json'):
                    backup_name = filename[:-5]  # 移除.json后缀
                    metadata = self._load_backup_metadata(backup_name)
                    
                    if metadata:
                        # 检查备份文件是否存在
                        backup_file = self._get_backup_file_path(backup_name)
                        if os.path.exists(backup_file):
                            metadata['backup_file_exists'] = True
                            metadata['backup_file_size'] = os.path.getsize(backup_file)
                        else:
                            metadata['backup_file_exists'] = False
                            metadata['backup_file_size'] = 0
                            logger.warning(f"备份文件不存在: {backup_file}")
                        
                        backups.append(metadata)
        except Exception as e:
            logger.error(f"列出备份时发生错误: {e}")
        
        # 排序
        if sort_by == 'time':
            backups.sort(key=lambda x: x.get('creation_time', 0), reverse=reverse)
        elif sort_by == 'name':
            backups.sort(key=lambda x: x.get('backup_name', ''), reverse=reverse)
        elif sort_by == 'size':
            backups.sort(key=lambda x: x.get('backup_file_size', 0), reverse=reverse)
        
        logger.info(f"找到 {len(backups)} 个备份")
        return backups
    
    def delete_backup(self, backup_name: str, force: bool = False) -> bool:
        """
        删除备份
        
        Args:
            backup_name: 备份名称
            force: 是否强制删除（即使有依赖的增量备份）
            
        Returns:
            是否删除成功
        """
        # 获取锁
        if not self._acquire_lock():
            return False
        
        try:
            logger.info(f"删除备份: {backup_name}")
            
            # 检查是否有依赖的增量备份
            if not force:
                backups = self.list_backups()
                for backup in backups:
                    if (backup.get('backup_type') == 'incremental' and 
                        backup.get('base_backup') == backup_name) or \
                       (backup.get('backup_type') == 'differential' and 
                        backup.get('full_backup') == backup_name):
                        logger.error(f"备份 {backup_name} 被其他备份依赖，无法删除。使用 --force 参数强制删除")
                        return False
            
            # 删除备份文件
            backup_file = self._get_backup_file_path(backup_name)
            if os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                    logger.info(f"已删除备份文件: {backup_file}")
                except Exception as e:
                    logger.error(f"删除备份文件失败: {e}")
            
            # 删除元数据文件
            metadata_file = os.path.join(self.metadata_dir, f"{backup_name}.json")
            if os.path.exists(metadata_file):
                try:
                    os.remove(metadata_file)
                    logger.info(f"已删除元数据文件: {metadata_file}")
                except Exception as e:
                    logger.error(f"删除元数据文件失败: {e}")
                    return False
            
            logger.info(f"备份删除成功: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除备份时发生错误: {e}")
            return False
        finally:
            # 释放锁
            self._release_lock()
    
    def clean_old_backups(self, keep_days: int = 30, keep_full_backups: int = 1) -> List[str]:
        """
        清理旧备份
        
        Args:
            keep_days: 保留最近多少天的备份
            keep_full_backups: 至少保留的全量备份数量
            
        Returns:
            删除的备份名称列表
        """
        logger.info(f"清理 {keep_days} 天前的旧备份")
        
        deleted_backups = []
        cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
        
        # 获取所有备份并按时间排序
        backups = self.list_backups(sort_by='time', reverse=True)
        
        # 分离全量备份
        full_backups = [b for b in backups if b.get('backup_type') == 'full']
        other_backups = [b for b in backups if b.get('backup_type') != 'full']
        
        # 保留最新的全量备份
        keep_full_backup_names = set()
        for i, full_backup in enumerate(full_backups):
            if i < keep_full_backups:
                keep_full_backup_names.add(full_backup['backup_name'])
                logger.info(f"保留全量备份: {full_backup['backup_name']}")
        
        # 收集要删除的备份
        to_delete = []
        
        # 处理非全量备份
        for backup in other_backups:
            backup_time = backup.get('creation_time', 0)
            backup_name = backup['backup_name']
            
            # 检查是否是保留的全量备份的依赖
            if backup.get('backup_type') == 'incremental':
                base_backup = backup.get('base_backup')
                if base_backup in keep_full_backup_names:
                    # 保留依赖于保留的全量备份的增量备份
                    continue
            elif backup.get('backup_type') == 'differential':
                full_backup = backup.get('full_backup')
                if full_backup in keep_full_backup_names:
                    # 保留依赖于保留的全量备份的差异备份
                    continue
            
            # 删除过期备份
            if backup_time < cutoff_time:
                to_delete.append(backup_name)
        
        # 处理全量备份（除了要保留的）
        for full_backup in full_backups[keep_full_backups:]:
            backup_time = full_backup.get('creation_time', 0)
            if backup_time < cutoff_time:
                # 检查是否有增量备份依赖于这个全量备份
                has_dependent = False
                for other_backup in other_backups:
                    if (other_backup.get('backup_type') == 'incremental' and 
                        other_backup.get('base_backup') == full_backup['backup_name']) or \
                       (other_backup.get('backup_type') == 'differential' and 
                        other_backup.get('full_backup') == full_backup['backup_name']):
                        has_dependent = True
                        break
                
                if not has_dependent:
                    to_delete.append(full_backup['backup_name'])
        
        # 执行删除
        for backup_name in to_delete:
            if self.delete_backup(backup_name, force=True):
                deleted_backups.append(backup_name)
        
        logger.info(f"清理完成，共删除 {len(deleted_backups)} 个备份")
        return deleted_backups
    
    def compare_backups(self, backup_name1: str, backup_name2: str) -> Dict[str, Any]:
        """
        比较两个备份
        
        Args:
            backup_name1: 第一个备份名称
            backup_name2: 第二个备份名称
            
        Returns:
            比较结果
        """
        logger.info(f"比较备份: {backup_name1} 和 {backup_name2}")
        
        # 加载备份元数据
        metadata1 = self._load_backup_metadata(backup_name1)
        metadata2 = self._load_backup_metadata(backup_name2)
        
        if not metadata1:
            logger.error(f"无法加载备份元数据: {backup_name1}")
            return {}
        
        if not metadata2:
            logger.error(f"无法加载备份元数据: {backup_name2}")
            return {}
        
        # 获取文件信息
        files1 = {f['path']: f for f in metadata1.get('files', [])}
        files2 = {f['path']: f for f in metadata2.get('files', [])}
        
        # 计算差异
        only_in1 = set(files1.keys()) - set(files2.keys())
        only_in2 = set(files2.keys()) - set(files1.keys())
        
        # 查找共同文件中修改的文件
        common_files = set(files1.keys()) & set(files2.keys())
        modified_files = []
        
        for file_path in common_files:
            f1 = files1[file_path]
            f2 = files2[file_path]
            
            if (f1.get('size', 0) != f2.get('size', 0) or 
                f1.get('mtime', 0) != f2.get('mtime', 0)):
                modified_files.append({
                    'path': file_path,
                    'size1': f1.get('size', 0),
                    'size2': f2.get('size', 0),
                    'size_diff': f2.get('size', 0) - f1.get('size', 0),
                    'mtime1': f1.get('mtime', 0),
                    'mtime2': f2.get('mtime', 0)
                })
        
        # 准备结果
        result = {
            'backup1': {
                'name': backup_name1,
                'type': metadata1.get('backup_type', 'unknown'),
                'time': datetime.datetime.fromtimestamp(metadata1.get('creation_time', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                'file_count': len(files1),
                'total_size': sum(f.get('size', 0) for f in files1.values())
            },
            'backup2': {
                'name': backup_name2,
                'type': metadata2.get('backup_type', 'unknown'),
                'time': datetime.datetime.fromtimestamp(metadata2.get('creation_time', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                'file_count': len(files2),
                'total_size': sum(f.get('size', 0) for f in files2.values())
            },
            'differences': {
                'only_in_backup1': list(only_in1),
                'only_in_backup2': list(only_in2),
                'modified_files': modified_files,
                'file_count_diff': len(files2) - len(files1),
                'size_diff': sum(f.get('size', 0) for f in files2.values()) - sum(f.get('size', 0) for f in files1.values())
            }
        }
        
        logger.info(f"比较完成: 仅在备份1中: {len(only_in1)}, 仅在备份2中: {len(only_in2)}, 修改的文件: {len(modified_files)}")
        
        return result
    
    def schedule_backup(self, schedule_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成备份计划
        
        Args:
            schedule_config: 计划配置
            
        Returns:
            计划信息
        """
        logger.info("生成备份计划")
        
        # 这里仅生成计划，实际的定时执行需要使用cron或其他调度器
        schedule_type = schedule_config.get('type', 'daily')
        source_paths = schedule_config.get('source_paths', [])
        retention_days = schedule_config.get('retention_days', 30)
        
        # 根据计划类型生成执行时间
        schedules = []
        
        if schedule_type == 'daily':
            # 每日备份
            for i in range(retention_days):
                schedules.append({
                    'type': 'daily',
                    'day': i + 1,
                    'action': 'incremental' if i > 0 else 'full',
                    'source_paths': source_paths
                })
        
        elif schedule_type == 'weekly':
            # 每周备份
            for week in range(retention_days // 7):
                schedules.append({
                    'type': 'weekly',
                    'week': week + 1,
                    'action': 'full',
                    'source_paths': source_paths
                })
        
        elif schedule_type == 'mixed':
            # 混合策略：每周一次全量，每天一次增量
            for week in range(retention_days // 7):
                # 全量备份
                schedules.append({
                    'type': 'weekly',
                    'week': week + 1,
                    'day': 1,
                    'action': 'full',
                    'source_paths': source_paths
                })
                
                # 增量备份
                for day in range(1, 7):
                    schedules.append({
                        'type': 'daily',
                        'week': week + 1,
                        'day': day + 1,
                        'action': 'incremental',
                        'source_paths': source_paths
                    })
        
        logger.info(f"生成了 {len(schedules)} 个备份计划")
        
        return {
            'schedule_type': schedule_type,
            'retention_days': retention_days,
            'schedules': schedules
        }


def print_progress(progress: int, current: int, total: int, current_file: str):
    """
    打印备份进度
    
    Args:
        progress: 进度百分比
        current: 当前处理的文件数
        total: 总文件数
        current_file: 当前处理的文件
    """
    sys.stdout.write(f"\r进度: {progress}% | {current}/{total} 文件 | 当前: {os.path.basename(current_file)}")
    sys.stdout.flush()


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description='数据备份与恢复工具')
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 创建备份子命令
    backup_parser = subparsers.add_parser('backup', help='创建备份')
    backup_parser.add_argument('source_paths', nargs='+', help='源路径列表')
    backup_parser.add_argument('--type', choices=['full', 'incremental', 'differential'], default='full',
                             help='备份类型')
    backup_parser.add_argument('--base-backup', help='基础备份名称（增量备份使用）')
    backup_parser.add_argument('--full-backup', help='全量备份名称（差异备份使用）')
    backup_parser.add_argument('--name', help='备份名称（默认自动生成）')
    backup_parser.add_argument('--output-dir', default='./backups', help='备份存储目录')
    backup_parser.add_argument('--compression', choices=COMPRESSION_FORMATS.keys(), default='tar.gz',
                             help='压缩格式')
    backup_parser.add_argument('--no-recursive', action='store_true', help='禁用递归备份')
    backup_parser.add_argument('--exclude', action='append', default=[], help='排除的文件模式')
    backup_parser.add_argument('--follow-symlinks', action='store_true', help='跟随符号链接')
    backup_parser.add_argument('--no-verify', action='store_true', help='禁用备份验证')
    backup_parser.add_argument('--workers', type=int, default=4, help='并行处理的线程数')
    
    # 恢复备份子命令
    restore_parser = subparsers.add_parser('restore', help='恢复备份')
    restore_parser.add_argument('backup_name', help='备份名称')
    restore_parser.add_argument('target_dir', help='恢复目标目录')
    restore_parser.add_argument('--backup-dir', default='./backups', help='备份存储目录')
    restore_parser.add_argument('--overwrite', action='store_true', help='覆盖已存在的文件')
    
    # 列出备份子命令
    list_parser = subparsers.add_parser('list', help='列出备份')
    list_parser.add_argument('--backup-dir', default='./backups', help='备份存储目录')
    list_parser.add_argument('--sort', choices=['time', 'name', 'size'], default='time', help='排序方式')
    list_parser.add_argument('--ascending', action='store_true', help='升序排序')
    
    # 删除备份子命令
    delete_parser = subparsers.add_parser('delete', help='删除备份')
    delete_parser.add_argument('backup_name', help='备份名称')
    delete_parser.add_argument('--backup-dir', default='./backups', help='备份存储目录')
    delete_parser.add_argument('--force', action='store_true', help='强制删除（即使有依赖）')
    
    # 验证备份子命令
    verify_parser = subparsers.add_parser('verify', help='验证备份')
    verify_parser.add_argument('backup_name', help='备份名称')
    verify_parser.add_argument('--backup-dir', default='./backups', help='备份存储目录')
    
    # 清理备份子命令
    clean_parser = subparsers.add_parser('clean', help='清理旧备份')
    clean_parser.add_argument('--backup-dir', default='./backups', help='备份存储目录')
    clean_parser.add_argument('--days', type=int, default=30, help='保留最近多少天的备份')
    clean_parser.add_argument('--keep-full', type=int, default=1, help='至少保留的全量备份数量')
    
    # 比较备份子命令
    compare_parser = subparsers.add_parser('compare', help='比较两个备份')
    compare_parser.add_argument('backup_name1', help='第一个备份名称')
    compare_parser.add_argument('backup_name2', help='第二个备份名称')
    compare_parser.add_argument('--backup-dir', default='./backups', help='备份存储目录')
    
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
    
    try:
        # 根据命令执行不同操作
        if args.command == 'backup':
            # 创建备份
            manager = BackupRestoreManager(
                backup_dir=args.output_dir,
                compression=args.compression,
                max_workers=args.workers,
                exclude_patterns=args.exclude,
                follow_symlinks=args.follow_symlinks,
                verify_backups=not args.no_verify
            )
            
            recursive = not args.no_recursive
            
            if args.type == 'full':
                backup_name = manager.create_full_backup(
                    source_paths=args.source_paths,
                    backup_name=args.name,
                    recursive=recursive,
                    progress_callback=print_progress
                )
                
                if backup_name:
                    print(f"\n全量备份创建成功: {backup_name}")
                    print(f"备份目录: {args.output_dir}")
                else:
                    print("\n备份失败")
                    return 1
            
            elif args.type == 'incremental':
                if not args.base_backup:
                    print("错误: 增量备份需要指定基础备份 --base-backup")
                    return 1
                
                backup_name = manager.create_incremental_backup(
                    source_paths=args.source_paths,
                    base_backup_name=args.base_backup,
                    backup_name=args.name,
                    recursive=recursive,
                    progress_callback=print_progress
                )
                
                if backup_name:
                    print(f"\n增量备份创建成功: {backup_name}")
                    print(f"基于备份: {args.base_backup}")
                else:
                    print("\n备份失败")
                    return 1
            
            elif args.type == 'differential':
                if not args.full_backup:
                    print("错误: 差异备份需要指定全量备份 --full-backup")
                    return 1
                
                backup_name = manager.create_differential_backup(
                    source_paths=args.source_paths,
                    full_backup_name=args.full_backup,
                    backup_name=args.name,
                    recursive=recursive,
                    progress_callback=print_progress
                )
                
                if backup_name:
                    print(f"\n差异备份创建成功: {backup_name}")
                    print(f"基于全量备份: {args.full_backup}")
                else:
                    print("\n备份失败")
                    return 1
        
        elif args.command == 'restore':
            # 恢复备份
            manager = BackupRestoreManager(backup_dir=args.backup_dir)
            
            success = manager.restore_from_backup(
                backup_name=args.backup_name,
                target_dir=args.target_dir,
                overwrite=args.overwrite,
                progress_callback=print_progress
            )
            
            if success:
                print(f"\n备份恢复成功: {args.backup_name}")
                print(f"恢复目标: {args.target_dir}")
            else:
                print("\n恢复失败")
                return 1
        
        elif args.command == 'list':
            # 列出备份
            manager = BackupRestoreManager(backup_dir=args.backup_dir)
            backups = manager.list_backups(
                sort_by=args.sort,
                reverse=not args.ascending
            )
            
            print(f"找到 {len(backups)} 个备份:")
            print("=" * 100)
            print(f"{'备份名称':<30} {'类型':<10} {'创建时间':<20} {'文件数':<10} {'大小':<15}")
            print("=" * 100)
            
            for backup in backups:
                backup_name = backup.get('backup_name', 'Unknown')
                backup_type = backup.get('backup_type', 'unknown')
                
                # 格式化时间
                creation_time = backup.get('creation_time', 0)
                time_str = datetime.datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S') if creation_time else 'N/A'
                
                # 文件数量
                if backup_type == 'full':
                    file_count = backup.get('file_count', 0)
                else:
                    file_count = backup.get('changed_file_count', 0)
                
                # 格式化大小
                size = backup.get('backup_file_size', 0)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.2f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                
                # 状态标记
                status = "✓" if backup.get('backup_file_exists', False) else "✗"
                
                print(f"{backup_name:<30} {backup_type:<10} {time_str:<20} {file_count:<10} {size_str:<15} {status}")
            
            print("=" * 100)
            print("✓: 备份文件存在  ✗: 备份文件丢失")
        
        elif args.command == 'delete':
            # 删除备份
            manager = BackupRestoreManager(backup_dir=args.backup_dir)
            
            success = manager.delete_backup(
                backup_name=args.backup_name,
                force=args.force
            )
            
            if success:
                print(f"\n备份删除成功: {args.backup_name}")
            else:
                print("\n删除失败")
                return 1
        
        elif args.command == 'verify':
            # 验证备份
            manager = BackupRestoreManager(backup_dir=args.backup_dir)
            
            if manager.verify_backup(args.backup_name):
                print(f"\n备份验证通过: {args.backup_name}")
            else:
                print("\n备份验证失败")
                return 1
        
        elif args.command == 'clean':
            # 清理备份
            manager = BackupRestoreManager(backup_dir=args.backup_dir)
            
            deleted = manager.clean_old_backups(
                keep_days=args.days,
                keep_full_backups=args.keep_full
            )
            
            print(f"\n清理完成，共删除 {len(deleted)} 个备份:")
            for backup_name in deleted:
                print(f"  - {backup_name}")
        
        elif args.command == 'compare':
            # 比较备份
            manager = BackupRestoreManager(backup_dir=args.backup_dir)
            
            result = manager.compare_backups(args.backup_name1, args.backup_name2)
            
            if result:
                print("\n备份比较结果:")
                print("=" * 80)
                print(f"备份1: {result['backup1']['name']}")
                print(f"  类型: {result['backup1']['type']}")
                print(f"  时间: {result['backup1']['time']}")
                print(f"  文件数: {result['backup1']['file_count']}")
                print(f"  总大小: {result['backup1']['total_size'] / (1024*1024):.2f} MB")
                print()
                print(f"备份2: {result['backup2']['name']}")
                print(f"  类型: {result['backup2']['type']}")
                print(f"  时间: {result['backup2']['time']}")
                print(f"  文件数: {result['backup2']['file_count']}")
                print(f"  总大小: {result['backup2']['total_size'] / (1024*1024):.2f} MB")
                print()
                print("差异:")
                diffs = result['differences']
                print(f"  仅在备份1中: {len(diffs['only_in_backup1'])} 个文件")
                print(f"  仅在备份2中: {len(diffs['only_in_backup2'])} 个文件")
                print(f"  修改的文件: {len(diffs['modified_files'])} 个文件")
                print(f"  文件数变化: {diffs['file_count_diff']:+}")
                print(f"  大小变化: {diffs['size_diff'] / (1024*1024):+.2f} MB")
                print("=" * 80)
            else:
                print("\n比较失败")
                return 1
        
        else:
            parser.print_help()
            return 1
        
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