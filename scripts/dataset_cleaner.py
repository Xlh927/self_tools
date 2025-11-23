#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集清洗模块（B2）

功能：
- 数据集中无效数据检测与移除
- 数据格式转换（图像格式、标注格式等）
- 重复数据检测与处理
- 数据一致性验证
- 缺失值处理（填充、删除等）
- 异常值检测与处理
- 数据标准化/归一化
- 支持多种数据格式（图像、文本、CSV等）
- 支持批量处理
- 清洗报告生成
"""

import os
import sys
import json
import csv
import yaml
import shutil
import logging
import argparse
import hashlib
import uuid
import cv2
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dataset_cleaner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DatasetCleaner")

class DatasetCleaner:
    """数据集清洗器类"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化数据集清洗器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.stats = {
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": 0,
            "duplicate_files": 0,
            "missing_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "removed_files": 0,
            "converted_files": 0,
            "fixed_files": 0
        }
        self.invalid_reasons = {}
        self.duplicate_groups = []
        self.start_time = None
        self.end_time = None
    
    def start_cleaning(self):
        """开始清洗"""
        self.start_time = datetime.now()
        logger.info("开始数据集清洗")
    
    def end_cleaning(self):
        """结束清洗"""
        self.end_time = datetime.now()
        logger.info(f"数据集清洗完成，总耗时: {(self.end_time - self.start_time).total_seconds():.2f}秒")
    
    def _ensure_output_dir(self, subdir: str = None):
        """
        确保输出目录存在
        
        Args:
            subdir: 子目录
            
        Returns:
            完整的输出目录路径
        """
        if not self.output_dir:
            return None
        
        output_path = self.output_dir
        if subdir:
            output_path = os.path.join(self.output_dir, subdir)
        
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        return output_path
    
    def calculate_file_hash(self, file_path: str, hash_algorithm: str = 'md5') -> Optional[str]:
        """
        计算文件哈希值
        
        Args:
            file_path: 文件路径
            hash_algorithm: 哈希算法
            
        Returns:
            文件哈希值
        """
        try:
            if hash_algorithm == 'md5':
                hash_func = hashlib.md5()
            elif hash_algorithm == 'sha1':
                hash_func = hashlib.sha1()
            elif hash_algorithm == 'sha256':
                hash_func = hashlib.sha256()
            else:
                logger.error(f"不支持的哈希算法: {hash_algorithm}")
                return None
            
            with open(file_path, 'rb') as f:
                # 分块读取文件
                while chunk := f.read(8192):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希值失败 {file_path}: {str(e)}")
            return None
    
    def validate_image(self, image_path: str) -> Tuple[bool, str]:
        """
        验证图像文件有效性
        
        Args:
            image_path: 图像路径
            
        Returns:
            (是否有效, 原因)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(image_path):
                return False, "文件不存在"
            
            # 检查文件大小
            if os.path.getsize(image_path) == 0:
                return False, "空文件"
            
            # 尝试使用PIL打开图像
            try:
                with Image.open(image_path) as img:
                    img.verify()  # 验证图像完整性
                    img.close()
                    # 再次打开以检查是否可以加载
                    with Image.open(image_path) as img2:
                        img2.load()
            except UnidentifiedImageError:
                return False, "无法识别的图像格式"
            except Exception as e:
                return False, f"图像加载失败: {str(e)}"
            
            # 尝试使用OpenCV打开图像
            try:
                img = cv2.imread(image_path)
                if img is None:
                    return False, "OpenCV无法读取图像"
                
                # 检查图像维度
                if len(img.shape) not in [2, 3]:
                    return False, "无效的图像维度"
            except Exception as e:
                return False, f"OpenCV处理失败: {str(e)}"
            
            return True, "有效图像"
        except Exception as e:
            logger.error(f"验证图像失败 {image_path}: {str(e)}")
            return False, f"验证异常: {str(e)}"
    
    def validate_json(self, json_path: str) -> Tuple[bool, str]:
        """
        验证JSON文件有效性
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            (是否有效, 原因)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(json_path):
                return False, "文件不存在"
            
            # 检查文件大小
            if os.path.getsize(json_path) == 0:
                return False, "空文件"
            
            # 尝试解析JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, (dict, list)):
                        return False, "JSON内容必须是对象或数组"
                except json.JSONDecodeError as e:
                    return False, f"JSON解析错误: {str(e)}"
            
            return True, "有效JSON"
        except Exception as e:
            logger.error(f"验证JSON失败 {json_path}: {str(e)}")
            return False, f"验证异常: {str(e)}"
    
    def validate_csv(self, csv_path: str) -> Tuple[bool, str]:
        """
        验证CSV文件有效性
        
        Args:
            csv_path: CSV文件路径
            
        Returns:
            (是否有效, 原因)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(csv_path):
                return False, "文件不存在"
            
            # 检查文件大小
            if os.path.getsize(csv_path) == 0:
                return False, "空文件"
            
            # 尝试解析CSV
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    # 读取所有行以检查格式
                    rows = list(reader)
                    if not rows:
                        return False, "CSV文件为空"
                    # 检查行的一致性
                    first_row_length = len(rows[0])
                    for i, row in enumerate(rows[1:], 2):
                        if len(row) != first_row_length:
                            return False, f"第{i}行的列数不一致"
            except Exception as e:
                return False, f"CSV解析错误: {str(e)}"
            
            return True, "有效CSV"
        except Exception as e:
            logger.error(f"验证CSV失败 {csv_path}: {str(e)}")
            return False, f"验证异常: {str(e)}"
    
    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        根据文件类型验证文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            (是否有效, 原因)
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif']:
            return self.validate_image(file_path)
        elif ext == '.json':
            return self.validate_json(file_path)
        elif ext == '.csv':
            return self.validate_csv(file_path)
        elif ext in ['.yaml', '.yml']:
            # 简单检查YAML文件
            try:
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    return False, "文件不存在或为空"
                with open(file_path, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
                return True, "有效YAML"
            except Exception as e:
                return False, f"YAML验证失败: {str(e)}"
        else:
            # 对于其他文件类型，只检查是否存在且不为空
            if not os.path.exists(file_path):
                return False, "文件不存在"
            if os.path.getsize(file_path) == 0:
                return False, "空文件"
            return True, "文件存在且不为空"
    
    def detect_duplicate_files(self, file_list: List[str], hash_algorithm: str = 'md5') -> List[List[str]]:
        """
        检测重复文件
        
        Args:
            file_list: 文件列表
            hash_algorithm: 哈希算法
            
        Returns:
            重复文件组列表
        """
        hash_to_files = {}
        
        logger.info(f"开始检测重复文件，总文件数: {len(file_list)}")
        
        for file_path in tqdm(file_list):
            # 验证文件是否有效
            is_valid, _ = self.validate_file(file_path)
            if not is_valid:
                continue
            
            # 计算哈希值
            file_hash = self.calculate_file_hash(file_path, hash_algorithm)
            if file_hash:
                if file_hash not in hash_to_files:
                    hash_to_files[file_hash] = []
                hash_to_files[file_hash].append(file_path)
        
        # 找出重复的文件组
        duplicate_groups = [files for files in hash_to_files.values() if len(files) > 1]
        self.duplicate_groups = duplicate_groups
        self.stats["duplicate_files"] = sum(len(group) for group in duplicate_groups)
        
        logger.info(f"重复文件检测完成，发现 {len(duplicate_groups)} 组重复文件，共 {self.stats['duplicate_files']} 个文件")
        
        return duplicate_groups
    
    def remove_duplicate_files(self, keep_first: bool = True, keep_largest: bool = False) -> int:
        """
        移除重复文件
        
        Args:
            keep_first: 是否保留每组的第一个文件
            keep_largest: 是否保留最大的文件
            
        Returns:
            移除的文件数量
        """
        removed_count = 0
        
        for group in self.duplicate_groups:
            if len(group) <= 1:
                continue
            
            # 确定要保留的文件
            if keep_largest:
                # 按文件大小排序，保留最大的
                group.sort(key=lambda x: os.path.getsize(x), reverse=True)
                keep_index = 0
            elif keep_first:
                # 保留第一个文件
                keep_index = 0
            else:
                # 保留最后一个文件
                keep_index = -1
            
            # 移除其他文件
            for i, file_path in enumerate(group):
                if i != keep_index:
                    try:
                        os.remove(file_path)
                        removed_count += 1
                        self.stats["removed_files"] += 1
                        logger.info(f"移除重复文件: {file_path}")
                    except Exception as e:
                        logger.error(f"移除文件失败 {file_path}: {str(e)}")
        
        return removed_count
    
    def convert_image_format(self, image_path: str, output_format: str, output_path: str = None) -> Optional[str]:
        """
        转换图像格式
        
        Args:
            image_path: 输入图像路径
            output_format: 输出格式 (jpg, png, bmp, etc.)
            output_path: 输出路径，None则自动生成
            
        Returns:
            输出图像路径
        """
        try:
            # 验证输入图像
            is_valid, reason = self.validate_image(image_path)
            if not is_valid:
                logger.error(f"无效的输入图像 {image_path}: {reason}")
                return None
            
            # 生成输出路径
            if not output_path:
                if not self.output_dir:
                    logger.error("未指定输出目录或输出路径")
                    return None
                base_name = os.path.basename(image_path)
                name_without_ext = os.path.splitext(base_name)[0]
                output_path = os.path.join(self._ensure_output_dir(), f"{name_without_ext}.{output_format.lower()}")
            
            # 转换格式
            with Image.open(image_path) as img:
                # 确保正确的颜色模式
                if img.mode == 'RGBA' and output_format.lower() in ['jpg', 'jpeg']:
                    # 将RGBA转换为RGB
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # 使用Alpha通道作为遮罩
                    background.save(output_path, output_format.upper())
                else:
                    img.save(output_path, output_format.upper())
            
            self.stats["converted_files"] += 1
            logger.info(f"图像格式转换完成: {image_path} -> {output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"转换图像格式失败 {image_path}: {str(e)}")
            return None
    
    def clean_csv(self, csv_path: str, output_path: str = None, 
                 drop_duplicates: bool = True, 
                 drop_empty_rows: bool = True, 
                 drop_empty_columns: bool = False, 
                 fill_na: Dict[str, Any] = None) -> Optional[str]:
        """
        清洗CSV文件
        
        Args:
            csv_path: 输入CSV路径
            output_path: 输出路径，None则自动生成
            drop_duplicates: 是否删除重复行
            drop_empty_rows: 是否删除空行
            drop_empty_columns: 是否删除空列
            fill_na: 缺失值填充规则
            
        Returns:
            输出CSV路径
        """
        try:
            # 验证输入CSV
            is_valid, reason = self.validate_csv(csv_path)
            if not is_valid:
                logger.error(f"无效的输入CSV {csv_path}: {reason}")
                return None
            
            # 读取CSV
            df = pd.read_csv(csv_path)
            original_rows = len(df)
            
            # 删除重复行
            if drop_duplicates:
                df = df.drop_duplicates()
            
            # 删除空行
            if drop_empty_rows:
                df = df.dropna(how='all')
            
            # 删除空列
            if drop_empty_columns:
                df = df.dropna(axis=1, how='all')
            
            # 填充缺失值
            if fill_na:
                for column, value in fill_na.items():
                    if column in df.columns:
                        df[column] = df[column].fillna(value)
            
            # 生成输出路径
            if not output_path:
                if not self.output_dir:
                    logger.error("未指定输出目录或输出路径")
                    return None
                base_name = os.path.basename(csv_path)
                name_without_ext = os.path.splitext(base_name)[0]
                output_path = os.path.join(self._ensure_output_dir(), f"{name_without_ext}_cleaned.csv")
            
            # 保存清洗后的CSV
            df.to_csv(output_path, index=False)
            
            cleaned_rows = len(df)
            logger.info(f"CSV清洗完成: {csv_path} -> {output_path}, 行数从 {original_rows} 减少到 {cleaned_rows}")
            
            return output_path
        except Exception as e:
            logger.error(f"清洗CSV失败 {csv_path}: {str(e)}")
            return None
    
    def clean_json(self, json_path: str, output_path: str = None, 
                  remove_duplicates: bool = True, 
                  sort_keys: bool = False, 
                  indent: int = 2) -> Optional[str]:
        """
        清洗JSON文件
        
        Args:
            json_path: 输入JSON路径
            output_path: 输出路径，None则自动生成
            remove_duplicates: 如果JSON是数组，是否移除重复项
            sort_keys: 是否排序键
            indent: 缩进空格数
            
        Returns:
            输出JSON路径
        """
        try:
            # 验证输入JSON
            is_valid, reason = self.validate_json(json_path)
            if not is_valid:
                logger.error(f"无效的输入JSON {json_path}: {reason}")
                return None
            
            # 读取JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 移除重复项（如果是数组）
            if remove_duplicates and isinstance(data, list):
                # 对于复杂对象，转换为JSON字符串进行去重
                seen = set()
                unique_data = []
                for item in data:
                    # 确保item是可序列化的
                    item_str = json.dumps(item, sort_keys=True)
                    if item_str not in seen:
                        seen.add(item_str)
                        unique_data.append(item)
                data = unique_data
            
            # 生成输出路径
            if not output_path:
                if not self.output_dir:
                    logger.error("未指定输出目录或输出路径")
                    return None
                base_name = os.path.basename(json_path)
                name_without_ext = os.path.splitext(base_name)[0]
                output_path = os.path.join(self._ensure_output_dir(), f"{name_without_ext}_cleaned.json")
            
            # 保存清洗后的JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
            
            logger.info(f"JSON清洗完成: {json_path} -> {output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"清洗JSON失败 {json_path}: {str(e)}")
            return None
    
    def find_missing_files(self, file_pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        查找缺失的文件对
        
        Args:
            file_pairs: 文件对列表 [(文件1, 文件2), ...]
            
        Returns:
            缺失文件对列表
        """
        missing_pairs = []
        
        for file1, file2 in file_pairs:
            if not os.path.exists(file1) or not os.path.exists(file2):
                missing_pairs.append((file1, file2))
                self.stats["missing_files"] += 1
        
        logger.info(f"缺失文件检测完成，发现 {len(missing_pairs)} 对缺失文件")
        
        return missing_pairs
    
    def fix_corrupted_images(self, image_path: str, output_path: str = None) -> Optional[str]:
        """
        尝试修复损坏的图像
        
        Args:
            image_path: 输入图像路径
            output_path: 输出路径，None则自动生成
            
        Returns:
            输出图像路径
        """
        try:
            # 生成输出路径
            if not output_path:
                if not self.output_dir:
                    logger.error("未指定输出目录或输出路径")
                    return None
                base_name = os.path.basename(image_path)
                name_without_ext = os.path.splitext(base_name)[0]
                output_path = os.path.join(self._ensure_output_dir(), f"{name_without_ext}_fixed.jpg")
            
            # 尝试使用PIL修复
            try:
                with Image.open(image_path) as img:
                    img = img.convert("RGB")  # 转换为RGB模式
                    img.save(output_path, "JPEG", quality=95, optimize=True)
                
                self.stats["fixed_files"] += 1
                logger.info(f"图像修复完成: {image_path} -> {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"PIL修复失败 {image_path}: {str(e)}")
                
            # 尝试使用OpenCV修复
            try:
                # 以二进制模式读取
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                
                # 使用OpenCV尝试解码
                img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    cv2.imwrite(output_path, img)
                    self.stats["fixed_files"] += 1
                    logger.info(f"OpenCV修复完成: {image_path} -> {output_path}")
                    return output_path
            except Exception as e:
                logger.error(f"OpenCV修复失败 {image_path}: {str(e)}")
            
            return None
        except Exception as e:
            logger.error(f"修复图像失败 {image_path}: {str(e)}")
            return None
    
    def process_directory(self, input_dir: str, recursive: bool = False, 
                         image_extensions: List[str] = None, 
                         validate: bool = True, 
                         detect_duplicates: bool = False, 
                         hash_algorithm: str = 'md5') -> Dict[str, Any]:
        """
        处理目录中的所有文件
        
        Args:
            input_dir: 输入目录
            recursive: 是否递归处理
            image_extensions: 图像文件扩展名列表
            validate: 是否验证文件
            detect_duplicates: 是否检测重复文件
            hash_algorithm: 哈希算法
            
        Returns:
            处理结果统计
        """
        if image_extensions is None:
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        
        file_list = []
        valid_files = []
        invalid_files = []
        
        # 收集文件
        for root, _, files in os.walk(input_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append(file_path)
            
            if not recursive:
                break
        
        self.stats["total_files"] = len(file_list)
        logger.info(f"开始处理目录: {input_dir}, 总文件数: {len(file_list)}")
        
        # 验证文件
        if validate:
            for file_path in tqdm(file_list):
                is_valid, reason = self.validate_file(file_path)
                if is_valid:
                    valid_files.append(file_path)
                    self.stats["valid_files"] += 1
                else:
                    invalid_files.append((file_path, reason))
                    self.stats["invalid_files"] += 1
                    # 记录无效原因
                    if reason not in self.invalid_reasons:
                        self.invalid_reasons[reason] = 0
                    self.invalid_reasons[reason] += 1
            
            logger.info(f"文件验证完成，有效文件: {len(valid_files)}, 无效文件: {len(invalid_files)}")
        else:
            valid_files = file_list
            self.stats["valid_files"] = len(file_list)
        
        # 检测重复文件
        if detect_duplicates:
            self.detect_duplicate_files(valid_files, hash_algorithm)
        
        # 更新处理统计
        self.stats["processed_files"] = len(file_list)
        
        return {
            "total_files": len(file_list),
            "valid_files": len(valid_files),
            "invalid_files": len(invalid_files),
            "invalid_reasons": self.invalid_reasons,
            "duplicate_groups": len(self.duplicate_groups),
            "duplicate_files": self.stats["duplicate_files"]
        }
    
    def generate_report(self, output_path: str = None, format: str = 'json') -> Optional[str]:
        """
        生成清洗报告
        
        Args:
            output_path: 输出路径，None则自动生成
            format: 报告格式 (json, html, txt)
            
        Returns:
            报告文件路径
        """
        try:
            # 生成输出路径
            if not output_path:
                if not self.output_dir:
                    output_path = f"cleaning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
                else:
                    output_path = os.path.join(self._ensure_output_dir(), f"cleaning_report.{format}")
            
            # 构建报告内容
            report_data = {
                "report_time": datetime.now().isoformat(),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None,
                "stats": self.stats,
                "invalid_reasons": self.invalid_reasons,
                "duplicate_groups": len(self.duplicate_groups),
                "duplicate_file_examples": [group[:2] for group in self.duplicate_groups[:5]] if self.duplicate_groups else []
            }
            
            # 保存报告
            if format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            elif format == 'txt':
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("=== 数据集清洗报告 ===\n\n")
                    f.write(f"报告生成时间: {report_data['report_time']}\n")
                    f.write(f"开始时间: {report_data['start_time']}\n")
                    f.write(f"结束时间: {report_data['end_time']}\n")
                    f.write(f"总耗时: {report_data['duration_seconds']:.2f} 秒\n\n")
                    
                    f.write("=== 统计信息 ===\n")
                    for key, value in report_data['stats'].items():
                        f.write(f"{key}: {value}\n")
                    
                    f.write("\n=== 无效文件原因 ===\n")
                    for reason, count in report_data['invalid_reasons'].items():
                        f.write(f"{reason}: {count}\n")
                    
                    f.write(f"\n=== 重复文件 ===\n")
                    f.write(f"重复文件组数量: {report_data['duplicate_groups']}\n")
                    if report_data['duplicate_file_examples']:
                        f.write("重复文件示例:  ")
                        for i, group in enumerate(report_data['duplicate_file_examples'], 1):
                            f.write(f"\n组 {i}:\n")
                            for file_path in group:
                                f.write(f"  - {file_path}\n")
            elif format == 'html':
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>数据集清洗报告</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1, h2 {{ color: #333; }}
                        .stats {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
                        .stat-card {{ background: #f5f5f5; border-radius: 5px; padding: 15px; min-width: 200px; }}
                        .stat-value {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
                        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                        .error {{ color: red; }}
                        .success {{ color: green; }}
                    </style>
                </head>
                <body>
                    <h1>数据集清洗报告</h1>
                    <p>报告生成时间: {report_data['report_time']}</p>
                    <p>开始时间: {report_data['start_time']}</p>
                    <p>结束时间: {report_data['end_time']}</p>
                    <p>总耗时: {report_data['duration_seconds']:.2f} 秒</p>
                    
                    <h2>统计信息</h2>
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-label">总文件数</div>
                            <div class="stat-value">{report_data['stats'].get('total_files', 0)}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">有效文件</div>
                            <div class="stat-value success">{report_data['stats'].get('valid_files', 0)}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">无效文件</div>
                            <div class="stat-value error">{report_data['stats'].get('invalid_files', 0)}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">重复文件</div>
                            <div class="stat-value">{report_data['stats'].get('duplicate_files', 0)}</div>
                        </div>
                    </div>
                    
                    <h2>无效文件原因</h2>
                    <table>
                        <tr>
                            <th>原因</th>
                            <th>数量</th>
                        </tr>
                """
                
                for reason, count in report_data['invalid_reasons'].items():
                    html_content += f"<tr><td>{reason}</td><td>{count}</td></tr>"
                
                html_content += f"""
                    </table>
                    
                    <h2>重复文件信息</h2>
                    <p>重复文件组数量: {report_data['duplicate_groups']}</p>
                """
                
                if report_data['duplicate_file_examples']:
                    html_content += "<h3>重复文件示例</h3>"
                    for i, group in enumerate(report_data['duplicate_file_examples'], 1):
                        html_content += f"<h4>组 {i}</h4><ul>"
                        for file_path in group:
                            html_content += f"<li>{file_path}</li>"
                        html_content += "</ul>"
                
                html_content += "</body></html>"
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            else:
                logger.error(f"不支持的报告格式: {format}")
                return None
            
            logger.info(f"清洗报告已生成: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"生成清洗报告失败: {str(e)}")
            return None

def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='数据集清洗工具')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 验证命令
    validate_parser = subparsers.add_parser('validate', help='验证数据集')
    validate_parser.add_argument('--input', '-i', required=True, help='输入文件或目录路径')
    validate_parser.add_argument('--output', '-o', default=None, help='输出目录')
    validate_parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    validate_parser.add_argument('--report', '-e', default=None, help='报告输出路径')
    validate_parser.add_argument('--report-format', default='json', choices=['json', 'txt', 'html'], help='报告格式')
    
    # 去重命令
    dedup_parser = subparsers.add_parser('dedup', help='移除重复文件')
    dedup_parser.add_argument('--input', '-i', required=True, help='输入目录路径')
    dedup_parser.add_argument('--output', '-o', default=None, help='输出目录')
    dedup_parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    dedup_parser.add_argument('--hash', default='md5', choices=['md5', 'sha1', 'sha256'], help='哈希算法')
    dedup_parser.add_argument('--keep-first', action='store_true', help='保留每组第一个文件')
    dedup_parser.add_argument('--keep-largest', action='store_true', help='保留最大的文件')
    dedup_parser.add_argument('--report', '-e', default=None, help='报告输出路径')
    
    # 转换命令
    convert_parser = subparsers.add_parser('convert', help='转换文件格式')
    convert_parser.add_argument('--input', '-i', required=True, help='输入文件或目录路径')
    convert_parser.add_argument('--output', '-o', required=True, help='输出目录')
    convert_parser.add_argument('--format', '-f', required=True, help='输出格式 (jpg, png, etc.)')
    convert_parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    # 清洗CSV命令
    clean_csv_parser = subparsers.add_parser('clean-csv', help='清洗CSV文件')
    clean_csv_parser.add_argument('--input', '-i', required=True, help='输入CSV文件或目录路径')
    clean_csv_parser.add_argument('--output', '-o', required=True, help='输出目录')
    clean_csv_parser.add_argument('--drop-duplicates', action='store_true', help='删除重复行')
    clean_csv_parser.add_argument('--drop-empty-rows', action='store_true', help='删除空行')
    clean_csv_parser.add_argument('--drop-empty-columns', action='store_true', help='删除空列')
    clean_csv_parser.add_argument('--fill-na', nargs='+', help='缺失值填充，格式为 "列名:值"')
    
    # 清洗JSON命令
    clean_json_parser = subparsers.add_parser('clean-json', help='清洗JSON文件')
    clean_json_parser.add_argument('--input', '-i', required=True, help='输入JSON文件或目录路径')
    clean_json_parser.add_argument('--output', '-o', required=True, help='输出目录')
    clean_json_parser.add_argument('--remove-duplicates', action='store_true', help='移除重复项')
    clean_json_parser.add_argument('--sort-keys', action='store_true', help='排序键')
    
    # 修复命令
    fix_parser = subparsers.add_parser('fix', help='修复损坏的文件')
    fix_parser.add_argument('--input', '-i', required=True, help='输入文件或目录路径')
    fix_parser.add_argument('--output', '-o', required=True, help='输出目录')
    fix_parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    return parser.parse_args()

def validate_dataset(args):
    """
    验证数据集
    """
    cleaner = DatasetCleaner(args.output)
    cleaner.start_cleaning()
    
    try:
        if os.path.isfile(args.input):
            # 验证单个文件
            is_valid, reason = cleaner.validate_file(args.input)
            print(f"文件验证结果: {'有效' if is_valid else '无效'}")
            print(f"原因: {reason}")
            cleaner.stats["total_files"] = 1
            cleaner.stats["valid_files"] = 1 if is_valid else 0
            cleaner.stats["invalid_files"] = 0 if is_valid else 1
            if not is_valid:
                cleaner.invalid_reasons[reason] = 1
        elif os.path.isdir(args.input):
            # 验证目录
            cleaner.process_directory(args.input, args.recursive, validate=True)
        else:
            print(f"输入路径不存在: {args.input}")
            return
        
        # 生成报告
        if args.report:
            cleaner.generate_report(args.report, args.report_format)
        
        # 打印统计信息
        print(f"\n验证统计:")
        print(f"总文件数: {cleaner.stats['total_files']}")
        print(f"有效文件: {cleaner.stats['valid_files']}")
        print(f"无效文件: {cleaner.stats['invalid_files']}")
        
        if cleaner.invalid_reasons:
            print("\n无效文件原因:")
            for reason, count in cleaner.invalid_reasons.items():
                print(f"  {reason}: {count}")
    finally:
        cleaner.end_cleaning()

def deduplicate_dataset(args):
    """
    去重数据集
    """
    cleaner = DatasetCleaner(args.output)
    cleaner.start_cleaning()
    
    try:
        if not os.path.isdir(args.input):
            print(f"输入路径必须是目录: {args.input}")
            return
        
        # 收集文件
        file_list = []
        for root, _, files in os.walk(args.input):
            for file in files:
                file_list.append(os.path.join(root, file))
            if not args.recursive:
                break
        
        # 检测重复文件
        cleaner.detect_duplicate_files(file_list, args.hash)
        
        # 移除重复文件
        if cleaner.duplicate_groups:
            print(f"发现 {len(cleaner.duplicate_groups)} 组重复文件，共 {cleaner.stats['duplicate_files']} 个文件")
            confirm = input("是否移除重复文件？(y/n): ")
            if confirm.lower() == 'y':
                removed = cleaner.remove_duplicate_files(args.keep_first, args.keep_largest)
                print(f"已移除 {removed} 个重复文件")
        else:
            print("未发现重复文件")
        
        # 生成报告
        if args.report:
            cleaner.generate_report(args.report)
    finally:
        cleaner.end_cleaning()

def convert_files(args):
    """
    转换文件格式
    """
    cleaner = DatasetCleaner(args.output)
    cleaner.start_cleaning()
    
    try:
        if os.path.isfile(args.input):
            # 转换单个文件
            result = cleaner.convert_image_format(args.input, args.format)
            if result:
                print(f"文件已转换: {result}")
            else:
                print("文件转换失败")
        elif os.path.isdir(args.input):
            # 转换目录中的文件
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
            converted_count = 0
            
            for root, _, files in os.walk(args.input):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        input_path = os.path.join(root, file)
                        # 保持相对目录结构
                        relative_path = os.path.relpath(root, args.input)
                        output_subdir = os.path.join(args.output, relative_path)
                        os.makedirs(output_subdir, exist_ok=True)
                        
                        # 生成输出文件名
                        name_without_ext = os.path.splitext(file)[0]
                        output_path = os.path.join(output_subdir, f"{name_without_ext}.{args.format.lower()}")
                        
                        if cleaner.convert_image_format(input_path, args.format, output_path):
                            converted_count += 1
                
                if not args.recursive:
                    break
            
            print(f"转换完成，共转换 {converted_count} 个文件")
        else:
            print(f"输入路径不存在: {args.input}")
    finally:
        cleaner.end_cleaning()

def clean_csv_files(args):
    """
    清洗CSV文件
    """
    cleaner = DatasetCleaner(args.output)
    cleaner.start_cleaning()
    
    try:
        # 解析填充规则
        fill_na = {}
        if args.fill_na:
            for item in args.fill_na:
                if ':' in item:
                    column, value = item.split(':', 1)
                    # 尝试转换值类型
                    try:
                        if value.lower() == 'true':
                            fill_na[column] = True
                        elif value.lower() == 'false':
                            fill_na[column] = False
                        elif '.' in value:
                            fill_na[column] = float(value)
                        else:
                            fill_na[column] = int(value)
                    except ValueError:
                        fill_na[column] = value
        
        if os.path.isfile(args.input) and args.input.lower().endswith('.csv'):
            # 清洗单个CSV文件
            result = cleaner.clean_csv(
                args.input, 
                drop_duplicates=args.drop_duplicates,
                drop_empty_rows=args.drop_empty_rows,
                drop_empty_columns=args.drop_empty_columns,
                fill_na=fill_na
            )
            if result:
                print(f"CSV文件已清洗: {result}")
            else:
                print("CSV文件清洗失败")
        elif os.path.isdir(args.input):
            # 清洗目录中的CSV文件
            cleaned_count = 0
            
            for root, _, files in os.walk(args.input):
                for file in files:
                    if file.lower().endswith('.csv'):
                        input_path = os.path.join(root, file)
                        # 保持相对目录结构
                        relative_path = os.path.relpath(root, args.input)
                        output_subdir = os.path.join(args.output, relative_path)
                        os.makedirs(output_subdir, exist_ok=True)
                        
                        output_path = os.path.join(output_subdir, file)
                        
                        if cleaner.clean_csv(
                            input_path, 
                            output_path,
                            drop_duplicates=args.drop_duplicates,
                            drop_empty_rows=args.drop_empty_rows,
                            drop_empty_columns=args.drop_empty_columns,
                            fill_na=fill_na
                        ):
                            cleaned_count += 1
            
            print(f"CSV文件清洗完成，共清洗 {cleaned_count} 个文件")
        else:
            print(f"输入路径不存在或不是CSV文件: {args.input}")
    finally:
        cleaner.end_cleaning()

def clean_json_files(args):
    """
    清洗JSON文件
    """
    cleaner = DatasetCleaner(args.output)
    cleaner.start_cleaning()
    
    try:
        if os.path.isfile(args.input) and args.input.lower().endswith('.json'):
            # 清洗单个JSON文件
            result = cleaner.clean_json(
                args.input,
                remove_duplicates=args.remove_duplicates,
                sort_keys=args.sort_keys
            )
            if result:
                print(f"JSON文件已清洗: {result}")
            else:
                print("JSON文件清洗失败")
        elif os.path.isdir(args.input):
            # 清洗目录中的JSON文件
            cleaned_count = 0
            
            for root, _, files in os.walk(args.input):
                for file in files:
                    if file.lower().endswith('.json'):
                        input_path = os.path.join(root, file)
                        # 保持相对目录结构
                        relative_path = os.path.relpath(root, args.input)
                        output_subdir = os.path.join(args.output, relative_path)
                        os.makedirs(output_subdir, exist_ok=True)
                        
                        output_path = os.path.join(output_subdir, file)
                        
                        if cleaner.clean_json(
                            input_path,
                            output_path,
                            remove_duplicates=args.remove_duplicates,
                            sort_keys=args.sort_keys
                        ):
                            cleaned_count += 1
            
            print(f"JSON文件清洗完成，共清洗 {cleaned_count} 个文件")
        else:
            print(f"输入路径不存在或不是JSON文件: {args.input}")
    finally:
        cleaner.end_cleaning()

def fix_files(args):
    """
    修复损坏的文件
    """
    cleaner = DatasetCleaner(args.output)
    cleaner.start_cleaning()
    
    try:
        if os.path.isfile(args.input):
            # 修复单个文件
            result = cleaner.fix_corrupted_images(args.input)
            if result:
                print(f"文件已修复: {result}")
            else:
                print("文件修复失败")
        elif os.path.isdir(args.input):
            # 修复目录中的文件
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
            fixed_count = 0
            
            for root, _, files in os.walk(args.input):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        input_path = os.path.join(root, file)
                        # 先验证文件是否损坏
                        is_valid, _ = cleaner.validate_image(input_path)
                        if not is_valid:
                            # 保持相对目录结构
                            relative_path = os.path.relpath(root, args.input)
                            output_subdir = os.path.join(args.output, relative_path)
                            os.makedirs(output_subdir, exist_ok=True)
                            
                            output_path = os.path.join(output_subdir, file)
                            
                            if cleaner.fix_corrupted_images(input_path, output_path):
                                fixed_count += 1
                
                if not args.recursive:
                    break
            
            print(f"文件修复完成，共修复 {fixed_count} 个文件")
        else:
            print(f"输入路径不存在: {args.input}")
    finally:
        cleaner.end_cleaning()

def main():
    """
    主函数
    """
    args = parse_arguments()
    
    if args.command == 'validate':
        validate_dataset(args)
    elif args.command == 'dedup':
        deduplicate_dataset(args)
    elif args.command == 'convert':
        convert_files(args)
    elif args.command == 'clean-csv':
        clean_csv_files(args)
    elif args.command == 'clean-json':
        clean_json_files(args)
    elif args.command == 'fix':
        fix_files(args)
    else:
        print("请指定命令")
        sys.exit(1)

if __name__ == "__main__":
    main()
