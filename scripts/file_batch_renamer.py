#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件批量重命名工具模块（C1）

功能：
- 支持批量重命名文件
- 支持正则表达式匹配和替换
- 支持序号命名（自定义起始值和步长）
- 支持插入日期时间戳
- 支持文件类型过滤
- 支持大小写转换
- 支持添加前缀/后缀
- 支持文件名长度限制
- 支持重命名预览和确认
- 支持递归处理子文件夹
- 支持重命名日志记录
- 支持撤销重命名操作

支持单文件和批量文件夹处理
"""

import os
import re
import argparse
import shutil
import datetime
import json
import logging
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FileBatchRenamer:
    """文件批量重命名器"""
    
    def __init__(self):
        self.rename_history = []  # 用于撤销操作
        self.dry_run = False  # 预览模式
    
    def setup_logging(self, log_file=None):
        """设置日志记录"""
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
    
    def load_history(self, history_file='rename_history.json'):
        """加载重命名历史"""
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.rename_history = json.load(f)
                logger.info(f"已加载 {len(self.rename_history)} 条重命名历史记录")
            except Exception as e:
                logger.error(f"加载重命名历史失败: {e}")
    
    def save_history(self, history_file='rename_history.json'):
        """保存重命名历史"""
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.rename_history, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存重命名历史到 {history_file}")
        except Exception as e:
            logger.error(f"保存重命名历史失败: {e}")
    
    def get_files(self, directory, recursive=False, file_pattern=None, ignore_pattern=None):
        """获取符合条件的文件列表"""
        files = []
        
        if recursive:
            # 递归遍历子文件夹
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    # 应用文件过滤器
                    if self._match_file(full_path, filename, file_pattern, ignore_pattern):
                        files.append(full_path)
        else:
            # 只处理当前文件夹
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                if os.path.isfile(full_path):
                    # 应用文件过滤器
                    if self._match_file(full_path, filename, file_pattern, ignore_pattern):
                        files.append(full_path)
        
        # 按文件名排序
        files.sort()
        return files
    
    def _match_file(self, full_path, filename, file_pattern=None, ignore_pattern=None):
        """匹配文件是否符合条件"""
        # 忽略隐藏文件
        if filename.startswith('.'):
            return False
        
        # 应用忽略模式
        if ignore_pattern:
            if re.search(ignore_pattern, filename):
                return False
        
        # 应用文件模式
        if file_pattern:
            if not re.search(file_pattern, filename):
                return False
        
        return True
    
    def validate_new_name(self, new_name, max_length=255):
        """验证新文件名是否合法"""
        # 检查文件名长度
        if len(new_name) > max_length:
            logger.warning(f"文件名 '{new_name}' 超过最大长度限制 {max_length}，将被截断")
            name, ext = os.path.splitext(new_name)
            new_name = name[:max_length - len(ext)] + ext
        
        # 检查文件名是否包含非法字符
        illegal_chars = '<>"|?*:/'
        for char in illegal_chars:
            if char in new_name:
                new_name = new_name.replace(char, '_')
                logger.warning(f"文件名包含非法字符 '{char}'，已替换为 '_'")
        
        # 检查文件名是否为空
        if not new_name or new_name == '.':
            return False
        
        return new_name
    
    def apply_regex_rename(self, file_list, pattern, replacement, case_sensitive=True):
        """应用正则表达式重命名"""
        rename_pairs = []
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for file_path in file_list:
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            # 应用正则表达式替换
            new_filename = re.sub(pattern, replacement, filename, flags=flags)
            
            if new_filename != filename:
                new_filename = self.validate_new_name(new_filename)
                if new_filename:
                    new_path = os.path.join(directory, new_filename)
                    rename_pairs.append((file_path, new_path))
        
        return rename_pairs
    
    def apply_sequence_rename(self, file_list, prefix='', suffix='', start=1, step=1, padding=0, keep_extension=True):
        """应用序号重命名"""
        rename_pairs = []
        current = start
        
        for file_path in file_list:
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            # 获取文件扩展名
            if keep_extension:
                name, ext = os.path.splitext(filename)
            else:
                ext = ''
            
            # 格式化序号
            sequence_str = str(current).zfill(padding)
            
            # 构建新文件名
            new_filename = f"{prefix}{sequence_str}{suffix}{ext}"
            new_filename = self.validate_new_name(new_filename)
            
            if new_filename:
                new_path = os.path.join(directory, new_filename)
                rename_pairs.append((file_path, new_path))
            
            current += step
        
        return rename_pairs
    
    def apply_case_rename(self, file_list, case_type='lower'):
        """应用大小写转换重命名"""
        rename_pairs = []
        
        for file_path in file_list:
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            # 应用大小写转换
            if case_type == 'lower':
                new_filename = filename.lower()
            elif case_type == 'upper':
                new_filename = filename.upper()
            elif case_type == 'title':
                new_filename = filename.title()
            else:
                new_filename = filename
            
            if new_filename != filename:
                new_filename = self.validate_new_name(new_filename)
                if new_filename:
                    new_path = os.path.join(directory, new_filename)
                    rename_pairs.append((file_path, new_path))
        
        return rename_pairs
    
    def apply_date_rename(self, file_list, date_format='%Y%m%d', position='prefix', separator='_'):
        """应用日期时间重命名"""
        rename_pairs = []
        current_date = datetime.datetime.now().strftime(date_format)
        
        for file_path in file_list:
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            
            # 根据位置添加日期
            if position == 'prefix':
                new_filename = f"{current_date}{separator}{name}{ext}"
            elif position == 'suffix':
                new_filename = f"{name}{separator}{current_date}{ext}"
            elif position == 'replace':
                new_filename = f"{current_date}{ext}"
            else:
                new_filename = filename
            
            if new_filename != filename:
                new_filename = self.validate_new_name(new_filename)
                if new_filename:
                    new_path = os.path.join(directory, new_filename)
                    rename_pairs.append((file_path, new_path))
        
        return rename_pairs
    
    def apply_metadata_rename(self, file_list, metadata_type='mtime', date_format='%Y%m%d_%H%M%S', position='prefix', separator='_'):
        """应用文件元数据（修改时间/创建时间）重命名"""
        rename_pairs = []
        
        for file_path in file_list:
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            
            try:
                # 获取文件时间戳
                if metadata_type == 'mtime':
                    timestamp = os.path.getmtime(file_path)
                elif metadata_type == 'ctime':
                    timestamp = os.path.getctime(file_path)
                elif metadata_type == 'atime':
                    timestamp = os.path.getatime(file_path)
                else:
                    timestamp = os.path.getmtime(file_path)
                
                # 格式化时间
                time_str = datetime.datetime.fromtimestamp(timestamp).strftime(date_format)
                
                # 根据位置添加时间
                if position == 'prefix':
                    new_filename = f"{time_str}{separator}{name}{ext}"
                elif position == 'suffix':
                    new_filename = f"{name}{separator}{time_str}{ext}"
                elif position == 'replace':
                    new_filename = f"{time_str}{ext}"
                else:
                    new_filename = filename
                
                if new_filename != filename:
                    new_filename = self.validate_new_name(new_filename)
                    if new_filename:
                        new_path = os.path.join(directory, new_filename)
                        rename_pairs.append((file_path, new_path))
            except Exception as e:
                logger.error(f"获取文件 {file_path} 元数据失败: {e}")
        
        return rename_pairs
    
    def apply_prefix_suffix(self, file_list, prefix='', suffix=''):
        """添加前缀和后缀"""
        rename_pairs = []
        
        for file_path in file_list:
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            
            new_filename = f"{prefix}{name}{suffix}{ext}"
            
            if new_filename != filename:
                new_filename = self.validate_new_name(new_filename)
                if new_filename:
                    new_path = os.path.join(directory, new_filename)
                    rename_pairs.append((file_path, new_path))
        
        return rename_pairs
    
    def apply_extension_rename(self, file_list, new_extension, keep_original=False):
        """修改文件扩展名"""
        rename_pairs = []
        
        # 确保扩展名格式正确
        if not new_extension.startswith('.'):
            new_extension = '.' + new_extension
        
        for file_path in file_list:
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            name, _ = os.path.splitext(filename)
            
            if keep_original:
                new_filename = f"{name}{new_extension}"
            else:
                new_filename = f"{name}{new_extension}"
            
            if new_filename != filename:
                new_filename = self.validate_new_name(new_filename)
                if new_filename:
                    new_path = os.path.join(directory, new_filename)
                    rename_pairs.append((file_path, new_path))
        
        return rename_pairs
    
    def check_conflicts(self, rename_pairs):
        """检查重命名冲突"""
        new_paths = [new for _, new in rename_pairs]
        duplicates = set()
        
        # 检查新文件名是否重复
        path_counts = defaultdict(int)
        for new_path in new_paths:
            path_counts[new_path] += 1
            if path_counts[new_path] > 1:
                duplicates.add(new_path)
        
        # 检查新文件名是否已存在
        existing_files = set()
        for _, new_path in rename_pairs:
            if os.path.exists(new_path):
                existing_files.add(new_path)
        
        conflicts = {
            'duplicates': list(duplicates),
            'existing': list(existing_files)
        }
        
        return conflicts
    
    def execute_rename(self, rename_pairs, backup=False, backup_dir=None):
        """执行重命名操作"""
        if not rename_pairs:
            logger.info("没有需要重命名的文件")
            return True
        
        # 检查冲突
        conflicts = self.check_conflicts(rename_pairs)
        if conflicts['duplicates']:
            logger.error(f"发现 {len(conflicts['duplicates'])} 个重命名冲突（重复的新文件名）")
            for path in conflicts['duplicates']:
                logger.error(f"  - {path}")
            return False
        
        if conflicts['existing']:
            logger.warning(f"发现 {len(conflicts['existing'])} 个文件已存在")
            for path in conflicts['existing']:
                logger.warning(f"  - {path}")
            
            # 在预览模式下，仍然继续处理，但在实际执行时需要用户确认
            if not self.dry_run:
                response = input("是否覆盖已存在的文件？(y/n): ")
                if response.lower() != 'y':
                    return False
        
        # 准备备份目录
        if backup and not self.dry_run:
            if backup_dir is None:
                backup_dir = os.path.join(os.getcwd(), 'backup_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
            
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            logger.info(f"将创建备份到: {backup_dir}")
        
        # 记录本次重命名操作
        operation_id = datetime.datetime.now().isoformat()
        operation_record = {
            'id': operation_id,
            'timestamp': operation_id,
            'rename_pairs': rename_pairs
        }
        
        # 执行重命名
        success_count = 0
        error_count = 0
        
        for old_path, new_path in tqdm(rename_pairs, desc="重命名进度"):
            if self.dry_run:
                logger.info(f"预览: '{old_path}' -> '{new_path}'")
                success_count += 1
            else:
                try:
                    # 创建备份
                    if backup:
                        # 计算相对路径以保持目录结构
                        rel_path = os.path.relpath(os.path.dirname(old_path), os.getcwd())
                        backup_path = os.path.join(backup_dir, rel_path)
                        if not os.path.exists(backup_path):
                            os.makedirs(backup_path)
                        
                        backup_file = os.path.join(backup_path, os.path.basename(old_path))
                        shutil.copy2(old_path, backup_file)
                    
                    # 执行重命名
                    os.rename(old_path, new_path)
                    logger.info(f"已重命名: '{old_path}' -> '{new_path}'")
                    success_count += 1
                except Exception as e:
                    logger.error(f"重命名失败 '{old_path}': {e}")
                    error_count += 1
        
        # 保存历史记录
        if not self.dry_run and success_count > 0:
            self.rename_history.append(operation_record)
            # 只保留最近100条历史记录
            if len(self.rename_history) > 100:
                self.rename_history = self.rename_history[-100:]
            self.save_history()
        
        logger.info(f"重命名完成: 成功 {success_count}, 失败 {error_count}")
        return error_count == 0
    
    def undo_rename(self, operation_id=None):
        """撤销重命名操作"""
        if not self.rename_history:
            logger.error("没有可撤销的重命名操作")
            return False
        
        # 查找要撤销的操作
        if operation_id:
            operation = next((op for op in self.rename_history if op['id'] == operation_id), None)
        else:
            # 默认撤销最后一次操作
            operation = self.rename_history[-1]
        
        if not operation:
            logger.error(f"找不到操作 ID: {operation_id}")
            return False
        
        # 反转重命名对
        reverse_pairs = [(new, old) for old, new in operation['rename_pairs']]
        
        logger.info(f"撤销操作 ID: {operation['id']}")
        logger.info(f"将恢复 {len(reverse_pairs)} 个文件")
        
        # 执行反向重命名
        result = self.execute_rename(reverse_pairs)
        
        if result:
            # 从历史记录中移除已撤销的操作
            self.rename_history.remove(operation)
            self.save_history()
            logger.info("撤销操作成功完成")
        
        return result
    
    def list_rename_history(self):
        """列出重命名历史"""
        if not self.rename_history:
            logger.info("没有重命名历史记录")
            return
        
        logger.info(f"共有 {len(self.rename_history)} 条重命名历史记录:")
        for i, operation in enumerate(reversed(self.rename_history), 1):
            timestamp = operation['timestamp']
            count = len(operation['rename_pairs'])
            logger.info(f"{i}. ID: {operation['id']} | 时间: {timestamp} | 文件数: {count}")
    
    def preview_rename(self, rename_pairs, max_preview=10):
        """预览重命名结果"""
        if not rename_pairs:
            logger.info("没有需要重命名的文件")
            return
        
        logger.info(f"将重命名 {len(rename_pairs)} 个文件:")
        
        # 显示前N个文件预览
        preview_count = min(max_preview, len(rename_pairs))
        for old_path, new_path in rename_pairs[:preview_count]:
            logger.info(f"  '{old_path}' -> '{new_path}'")
        
        if len(rename_pairs) > preview_count:
            logger.info(f"  ... 还有 {len(rename_pairs) - preview_count} 个文件")

# 命令行接口函数
def batch_rename(args):
    """批量重命名命令"""
    renamer = FileBatchRenamer()
    renamer.dry_run = args.dry_run
    
    # 设置日志
    if args.log_file:
        renamer.setup_logging(args.log_file)
    
    # 加载历史记录
    renamer.load_history()
    
    # 获取文件列表
    logger.info(f"正在扫描目录: {args.directory}")
    file_list = renamer.get_files(
        args.directory,
        recursive=args.recursive,
        file_pattern=args.file_pattern,
        ignore_pattern=args.ignore_pattern
    )
    
    logger.info(f"找到 {len(file_list)} 个符合条件的文件")
    
    if not file_list:
        logger.info("没有找到符合条件的文件，退出")
        return
    
    # 应用重命名规则
    rename_pairs = []
    
    if args.regex_pattern and args.regex_replacement:
        # 正则表达式重命名
        logger.info(f"应用正则表达式重命名: '{args.regex_pattern}' -> '{args.regex_replacement}'")
        rename_pairs = renamer.apply_regex_rename(
            file_list,
            args.regex_pattern,
            args.regex_replacement,
            case_sensitive=not args.ignore_case
        )
    
    elif args.sequence:
        # 序号重命名
        logger.info(f"应用序号重命名: 前缀='{args.prefix}', 后缀='{args.suffix}', 起始={args.start}, 步长={args.step}, 填充={args.padding}")
        rename_pairs = renamer.apply_sequence_rename(
            file_list,
            prefix=args.prefix,
            suffix=args.suffix,
            start=args.start,
            step=args.step,
            padding=args.padding,
            keep_extension=not args.remove_extension
        )
    
    elif args.case:
        # 大小写转换
        logger.info(f"应用大小写转换: {args.case}")
        rename_pairs = renamer.apply_case_rename(file_list, args.case)
    
    elif args.add_date:
        # 添加日期
        logger.info(f"添加日期: 格式='{args.date_format}', 位置='{args.date_position}', 分隔符='{args.separator}'")
        rename_pairs = renamer.apply_date_rename(
            file_list,
            date_format=args.date_format,
            position=args.date_position,
            separator=args.separator
        )
    
    elif args.use_metadata:
        # 使用文件元数据
        logger.info(f"使用文件元数据: 类型='{args.metadata_type}', 格式='{args.date_format}', 位置='{args.date_position}'")
        rename_pairs = renamer.apply_metadata_rename(
            file_list,
            metadata_type=args.metadata_type,
            date_format=args.date_format,
            position=args.date_position,
            separator=args.separator
        )
    
    elif args.prefix or args.suffix:
        # 添加前缀或后缀
        logger.info(f"添加前缀='{args.prefix}' 和/或 后缀='{args.suffix}'")
        rename_pairs = renamer.apply_prefix_suffix(file_list, args.prefix, args.suffix)
    
    elif args.new_extension:
        # 修改扩展名
        logger.info(f"修改扩展名为: {args.new_extension}")
        rename_pairs = renamer.apply_extension_rename(file_list, args.new_extension)
    
    else:
        logger.error("请指定重命名规则")
        return
    
    # 预览重命名结果
    renamer.preview_rename(rename_pairs)
    
    # 如果不是预览模式，确认执行
    if not args.dry_run:
        response = input("确认执行重命名操作？(y/n): ")
        if response.lower() != 'y':
            logger.info("已取消重命名操作")
            return
    
    # 执行重命名
    renamer.execute_rename(
        rename_pairs,
        backup=args.backup,
        backup_dir=args.backup_dir
    )

def undo_rename_command(args):
    """撤销重命名命令"""
    renamer = FileBatchRenamer()
    renamer.load_history()
    renamer.undo_rename(args.operation_id)

def list_history_command(args):
    """列出历史命令"""
    renamer = FileBatchRenamer()
    renamer.load_history()
    renamer.list_rename_history()

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='文件批量重命名工具')
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 重命名命令
    rename_parser = subparsers.add_parser('rename', help='批量重命名文件')
    rename_parser.add_argument('--directory', '-d', required=True, help='要处理的目录')
    rename_parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子文件夹')
    rename_parser.add_argument('--file-pattern', '-f', help='文件匹配正则表达式')
    rename_parser.add_argument('--ignore-pattern', '-i', help='忽略文件的正则表达式')
    rename_parser.add_argument('--dry-run', '-n', action='store_true', help='预览模式，不实际执行重命名')
    rename_parser.add_argument('--backup', '-b', action='store_true', help='创建文件备份')
    rename_parser.add_argument('--backup-dir', help='备份目录路径')
    rename_parser.add_argument('--log-file', help='日志文件路径')
    
    # 重命名规则组
    rule_group = rename_parser.add_mutually_exclusive_group(required=True)
    
    # 正则表达式重命名
    rule_group.add_argument('--regex-pattern', help='正则表达式匹配模式')
    rename_parser.add_argument('--regex-replacement', help='正则表达式替换内容')
    rename_parser.add_argument('--ignore-case', action='store_true', help='正则表达式忽略大小写')
    
    # 序号重命名
    rule_group.add_argument('--sequence', action='store_true', help='使用序号重命名')
    rename_parser.add_argument('--prefix', default='', help='序号前的前缀')
    rename_parser.add_argument('--suffix', default='', help='序号后的后缀')
    rename_parser.add_argument('--start', type=int, default=1, help='起始序号')
    rename_parser.add_argument('--step', type=int, default=1, help='序号步长')
    rename_parser.add_argument('--padding', type=int, default=0, help='序号填充位数')
    rename_parser.add_argument('--remove-extension', action='store_true', help='移除原始扩展名')
    
    # 大小写转换
    rule_group.add_argument('--case', choices=['lower', 'upper', 'title'], help='大小写转换（lower/upper/title）')
    
    # 添加日期
    rule_group.add_argument('--add-date', action='store_true', help='添加当前日期到文件名')
    rename_parser.add_argument('--date-format', default='%Y%m%d', help='日期格式（默认: %%Y%%m%%d）')
    rename_parser.add_argument('--date-position', choices=['prefix', 'suffix', 'replace'], default='prefix', help='日期位置')
    rename_parser.add_argument('--separator', default='_', help='分隔符')
    
    # 使用文件元数据
    rule_group.add_argument('--use-metadata', action='store_true', help='使用文件元数据重命名')
    rename_parser.add_argument('--metadata-type', choices=['mtime', 'ctime', 'atime'], default='mtime', help='元数据类型')
    
    # 添加前缀/后缀
    rule_group.add_argument('--add-prefix-suffix', action='store_true', help='添加前缀和/或后缀')
    
    # 修改扩展名
    rule_group.add_argument('--new-extension', help='新的文件扩展名')
    
    # 撤销命令
    undo_parser = subparsers.add_parser('undo', help='撤销最近的重命名操作')
    undo_parser.add_argument('--operation-id', help='要撤销的操作ID，不指定则撤销最后一次操作')
    
    # 历史命令
    history_parser = subparsers.add_parser('history', help='列出重命名历史记录')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    if args.command == 'rename':
        # 检查正则表达式参数是否匹配
        if args.regex_pattern and not args.regex_replacement:
            print("错误: 使用 --regex-pattern 时必须指定 --regex-replacement")
            return
        elif args.regex_replacement and not args.regex_pattern:
            print("错误: 使用 --regex-replacement 时必须指定 --regex-pattern")
            return
        
        # 执行重命名
        batch_rename(args)
    
    elif args.command == 'undo':
        # 执行撤销
        undo_rename_command(args)
    
    elif args.command == 'history':
        # 列出历史
        list_history_command(args)
    
    else:
        # 显示帮助信息
        print("请指定命令")
        print("可用命令: rename, undo, history")
        print("使用 -h 参数查看各命令的详细用法")

if __name__ == "__main__":
    main()