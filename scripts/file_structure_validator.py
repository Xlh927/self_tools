#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件结构校验模块（C2）

功能：
- 检查目录结构是否符合预期（支持配置模板）
- 检测缺失的必要文件
- 检测多余的文件
- 文件类型/扩展名验证
- 文件数量统计与验证
- 嵌套目录深度检查
- 配置规则文件支持（JSON格式）
- 生成详细的校验报告（HTML/JSON/TXT）
- 支持批量目录检查

支持单文件和批量文件夹处理
"""

import os
import json
import argparse
import glob
from datetime import datetime
from tqdm import tqdm
import re
import xml.etree.ElementTree as ET
from pathlib import Path

def ensure_directory(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_rule_config(config_path):
    """加载规则配置文件"""
    if not os.path.exists(config_path):
        print(f"警告：配置文件不存在 {config_path}")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置文件失败 {config_path}: {e}")
        return {}

class FileStructureValidator:
    def __init__(self, config=None):
        """初始化文件结构验证器"""
        self.config = config or {}
        self.results = {
            'total_directories': 0,
            'total_files': 0,
            'missing_files': [],
            'extra_files': [],
            'invalid_files': [],
            'structure_errors': [],
            'validation_time': None
        }
    
    def validate_directory_structure(self, target_dir, template=None):
        """验证目录结构是否符合模板"""
        if template is None:
            template = self.config.get('directory_structure', {})
        
        # 获取实际目录结构
        actual_structure = self._get_directory_structure(target_dir)
        
        # 验证根目录结构
        root_template = template.get('root', {})
        required_dirs = root_template.get('directories', [])
        optional_dirs = root_template.get('optional_directories', [])
        required_files = root_template.get('files', [])
        
        # 检查必要目录是否存在
        for dir_name in required_dirs:
            dir_path = os.path.join(target_dir, dir_name)
            if not os.path.isdir(dir_path):
                self.results['structure_errors'].append({
                    'type': 'missing_directory',
                    'path': dir_path,
                    'message': f'必要目录不存在: {dir_path}'
                })
            else:
                # 递归验证子目录
                if dir_name in template:
                    self.validate_directory_structure(dir_path, template[dir_name])
        
        # 检查必要文件是否存在
        for file_pattern in required_files:
            expected_files = self._glob_pattern(os.path.join(target_dir, file_pattern))
            if not expected_files:
                self.results['missing_files'].append({
                    'path': os.path.join(target_dir, file_pattern),
                    'type': 'required',
                    'message': f'必要文件不存在: {file_pattern}'
                })
    
    def _get_directory_structure(self, root_dir):
        """获取目录结构"""
        structure = {}
        
        try:
            for item in os.listdir(root_dir):
                item_path = os.path.join(root_dir, item)
                if os.path.isdir(item_path):
                    structure[item] = {
                        'type': 'directory',
                        'children': self._get_directory_structure(item_path)
                    }
                else:
                    structure[item] = {
                        'type': 'file',
                        'size': os.path.getsize(item_path),
                        'mtime': os.path.getmtime(item_path)
                    }
        except Exception as e:
            print(f"获取目录结构失败 {root_dir}: {e}")
        
        return structure
    
    def _glob_pattern(self, pattern):
        """使用glob查找匹配的文件"""
        try:
            return glob.glob(pattern)
        except Exception as e:
            print(f"查找文件失败 {pattern}: {e}")
            return []
    
    def check_file_extensions(self, target_dir, allowed_extensions=None):
        """检查文件扩展名是否符合要求"""
        if allowed_extensions is None:
            allowed_extensions = self.config.get('allowed_extensions', [])
        
        if not allowed_extensions:
            return
        
        # 转换为小写以支持大小写不敏感的检查
        allowed_extensions = [ext.lower() for ext in allowed_extensions]
        
        # 遍历目录中的所有文件
        for root, dirs, files in os.walk(target_dir):
            # 跳过被排除的目录
            excluded_dirs = self.config.get('excluded_directories', [])
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            for file_name in files:
                # 获取文件扩展名
                _, ext = os.path.splitext(file_name)
                ext = ext.lower()  # 转换为小写
                
                # 检查扩展名是否在允许列表中
                if ext and ext[1:] not in allowed_extensions:  # ext[1:] 去掉点号
                    file_path = os.path.join(root, file_name)
                    self.results['invalid_files'].append({
                        'path': file_path,
                        'issue': 'invalid_extension',
                        'message': f'无效的文件扩展名: {ext}, 允许的扩展名: {" ".join(allowed_extensions)}'
                    })
    
    def check_file_naming_conventions(self, target_dir, patterns=None):
        """检查文件命名是否符合规范"""
        if patterns is None:
            patterns = self.config.get('naming_patterns', [])
        
        if not patterns:
            return
        
        # 遍历目录中的所有文件
        for root, dirs, files in os.walk(target_dir):
            # 跳过被排除的目录
            excluded_dirs = self.config.get('excluded_directories', [])
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            for file_name in files:
                # 检查文件名是否匹配任一模式
                matched = False
                for pattern in patterns:
                    try:
                        if re.match(pattern, file_name):
                            matched = True
                            break
                    except Exception as e:
                        print(f"正则表达式错误 {pattern}: {e}")
                
                if not matched:
                    file_path = os.path.join(root, file_name)
                    self.results['invalid_files'].append({
                        'path': file_path,
                        'issue': 'naming_convention',
                        'message': f'文件名不符合规范: {file_name}, 要求的模式: {" ".join(patterns)}'
                    })
    
    def check_file_count(self, target_dir, file_rules=None):
        """检查文件数量是否符合要求"""
        if file_rules is None:
            file_rules = self.config.get('file_count_rules', [])
        
        for rule in file_rules:
            path_pattern = rule.get('path', '')
            min_count = rule.get('min_count', 0)
            max_count = rule.get('max_count', float('inf'))
            description = rule.get('description', '')
            
            # 使用glob查找匹配的文件
            full_pattern = os.path.join(target_dir, path_pattern)
            matching_files = self._glob_pattern(full_pattern)
            count = len(matching_files)
            
            # 检查数量是否在范围内
            if count < min_count:
                self.results['structure_errors'].append({
                    'type': 'file_count_too_low',
                    'pattern': path_pattern,
                    'message': f'{description} 文件数量不足: 找到 {count} 个, 需要至少 {min_count} 个'
                })
            elif count > max_count:
                self.results['structure_errors'].append({
                    'type': 'file_count_too_high',
                    'pattern': path_pattern,
                    'message': f'{description} 文件数量过多: 找到 {count} 个, 最多允许 {max_count} 个'
                })
    
    def check_directory_depth(self, target_dir, max_depth=None):
        """检查目录深度是否符合要求"""
        if max_depth is None:
            max_depth = self.config.get('max_directory_depth', 10)
        
        # 获取目标目录的绝对路径
        abs_target_dir = os.path.abspath(target_dir)
        
        # 遍历目录树，检查深度
        for root, dirs, files in os.walk(abs_target_dir):
            # 计算当前目录的深度
            current_depth = root[len(abs_target_dir):].count(os.sep)
            
            if current_depth > max_depth:
                self.results['structure_errors'].append({
                    'type': 'directory_depth_exceeded',
                    'path': root,
                    'message': f'目录深度超过限制: 当前深度 {current_depth}, 最大允许深度 {max_depth}'
                })
                # 停止深入这个目录
                dirs[:] = []
    
    def check_missing_paired_files(self, target_dir, pairs=None):
        """检查成对文件是否都存在（如图像和标注文件）"""
        if pairs is None:
            pairs = self.config.get('file_pairs', [])
        
        for pair in pairs:
            primary_ext = pair.get('primary', '')
            secondary_ext = pair.get('secondary', '')
            description = pair.get('description', '成对文件')
            
            # 查找所有主文件
            primary_files = self._glob_pattern(os.path.join(target_dir, f'**/*{primary_ext}'), recursive=True)
            
            for primary_file in primary_files:
                # 构建对应的次文件路径
                base_name = os.path.splitext(primary_file)[0]
                secondary_file = f'{base_name}{secondary_ext}'
                
                if not os.path.exists(secondary_file):
                    self.results['missing_files'].append({
                        'path': secondary_file,
                        'type': 'paired_file',
                        'message': f'{description}缺失: 主文件 {primary_file} 对应的次文件不存在'
                    })
    
    def _glob_pattern(self, pattern, recursive=True):
        """增强的glob查找"""
        try:
            return glob.glob(pattern, recursive=recursive)
        except Exception as e:
            print(f"查找文件失败 {pattern}: {e}")
            return []
    
    def count_total_files_and_dirs(self, target_dir):
        """统计总文件数和目录数"""
        dir_count = 0
        file_count = 0
        
        for root, dirs, files in os.walk(target_dir):
            dir_count += len(dirs)
            file_count += len(files)
        
        self.results['total_directories'] = dir_count
        self.results['total_files'] = file_count
    
    def run_full_validation(self, target_dir):
        """运行完整的验证流程"""
        start_time = datetime.now()
        
        print(f"开始验证目录结构: {target_dir}")
        
        # 统计基本信息
        self.count_total_files_and_dirs(target_dir)
        
        # 验证目录结构
        self.validate_directory_structure(target_dir)
        
        # 检查文件扩展名
        self.check_file_extensions(target_dir)
        
        # 检查文件命名规范
        self.check_file_naming_conventions(target_dir)
        
        # 检查文件数量
        self.check_file_count(target_dir)
        
        # 检查目录深度
        self.check_directory_depth(target_dir)
        
        # 检查成对文件
        self.check_missing_paired_files(target_dir)
        
        # 记录验证时间
        self.results['validation_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.results['duration_seconds'] = (datetime.now() - start_time).total_seconds()
        
        return self.results
    
    def generate_txt_report(self, output_path):
        """生成文本格式的报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("文件结构验证报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"验证时间: {self.results.get('validation_time', 'N/A')}\n")
            f.write(f"验证耗时: {self.results.get('duration_seconds', 'N/A'):.2f} 秒\n")
            f.write(f"总目录数: {self.results.get('total_directories', 0)}\n")
            f.write(f"总文件数: {self.results.get('total_files', 0)}\n")
            f.write("=" * 80 + "\n\n")
            
            # 缺失文件
            f.write("[缺失文件]\n")
            f.write("-" * 80 + "\n")
            missing_files = self.results.get('missing_files', [])
            if missing_files:
                for i, item in enumerate(missing_files, 1):
                    f.write(f"{i}. {item.get('path', '')}\n")
                    f.write(f"   类型: {item.get('type', '')}\n")
                    f.write(f"   消息: {item.get('message', '')}\n\n")
            else:
                f.write("无缺失文件\n\n")
            
            # 结构错误
            f.write("[结构错误]\n")
            f.write("-" * 80 + "\n")
            structure_errors = self.results.get('structure_errors', [])
            if structure_errors:
                for i, item in enumerate(structure_errors, 1):
                    f.write(f"{i}. 类型: {item.get('type', '')}\n")
                    if 'path' in item:
                        f.write(f"   路径: {item['path']}\n")
                    elif 'pattern' in item:
                        f.write(f"   模式: {item['pattern']}\n")
                    f.write(f"   消息: {item.get('message', '')}\n\n")
            else:
                f.write("无结构错误\n\n")
            
            # 无效文件
            f.write("[无效文件]\n")
            f.write("-" * 80 + "\n")
            invalid_files = self.results.get('invalid_files', [])
            if invalid_files:
                for i, item in enumerate(invalid_files, 1):
                    f.write(f"{i}. {item.get('path', '')}\n")
                    f.write(f"   问题: {item.get('issue', '')}\n")
                    f.write(f"   消息: {item.get('message', '')}\n\n")
            else:
                f.write("无无效文件\n\n")
            
            # 总结
            f.write("=" * 80 + "\n")
            total_issues = len(missing_files) + len(structure_errors) + len(invalid_files)
            f.write(f"总计问题数: {total_issues}\n")
            f.write(f"缺失文件数: {len(missing_files)}\n")
            f.write(f"结构错误数: {len(structure_errors)}\n")
            f.write(f"无效文件数: {len(invalid_files)}\n")
            f.write("=" * 80 + "\n")
            
            if total_issues == 0:
                f.write("验证结果: 通过 ✓\n")
            else:
                f.write("验证结果: 失败 ✗\n")
    
    def generate_json_report(self, output_path):
        """生成JSON格式的报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            # 添加总结信息
            report_data = self.results.copy()
            report_data['summary'] = {
                'total_issues': len(report_data.get('missing_files', [])) + 
                               len(report_data.get('structure_errors', [])) + 
                               len(report_data.get('invalid_files', [])),
                'missing_files_count': len(report_data.get('missing_files', [])),
                'structure_errors_count': len(report_data.get('structure_errors', [])),
                'invalid_files_count': len(report_data.get('invalid_files', [])),
                'passed': len(report_data.get('missing_files', [])) == 0 and 
                         len(report_data.get('structure_errors', [])) == 0 and 
                         len(report_data.get('invalid_files', [])) == 0
            }
            
            json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    def generate_html_report(self, output_path):
        """生成HTML格式的报告"""
        total_issues = len(self.results.get('missing_files', [])) + 
                      len(self.results.get('structure_errors', [])) + 
                      len(self.results.get('invalid_files', []))
        passed = total_issues == 0
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文件结构验证报告</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            color: #333;
            line-height: 1.6;
        }
        h1, h2 {
            color: #2c3e50;
        }
        .summary {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .summary-item {
            display: inline-block;
            margin-right: 30px;
            margin-bottom: 10px;
        }
        .summary-label {
            font-weight: bold;
            color: #495057;
        }
        .status {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }
        .status.passed {
            background-color: #d4edda;
            color: #155724;
        }
        .status.failed {
            background-color: #f8d7da;
            color: #721c24;
        }
        .section {
            margin-bottom: 30px;
        }
        .section-header {
            background-color: #e9ecef;
            padding: 10px 15px;
            border-radius: 5px 5px 0 0;
            margin: 0;
        }
        .section-content {
            border: 1px solid #dee2e6;
            border-top: none;
            border-radius: 0 0 5px 5px;
            padding: 15px;
        }
        .issue-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .issue-item {
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 10px;
            background-color: #f8f9fa;
        }
        .issue-type {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .issue-message {
            color: #6c757d;
        }
        .empty-message {
            color: #28a745;
            font-style: italic;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            border: 1px solid #dee2e6;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
    </style>
</head>
<body>
    <h1>文件结构验证报告</h1>
    
    <div class="summary">
        <div class="summary-item">
            <span class="summary-label">验证时间:</span> ''' + 
            self.results.get('validation_time', 'N/A') + 
            '''</div>
        <div class="summary-item">
            <span class="summary-label">验证耗时:</span> ''' + 
            f"{self.results.get('duration_seconds', 0):.2f} 秒" + 
            '''</div>
        <div class="summary-item">
            <span class="summary-label">总目录数:</span> ''' + 
            str(self.results.get('total_directories', 0)) + 
            '''</div>
        <div class="summary-item">
            <span class="summary-label">总文件数:</span> ''' + 
            str(self.results.get('total_files', 0)) + 
            '''</div>
        <div class="summary-item">
            <span class="summary-label">总计问题数:</span> ''' + 
            str(total_issues) + 
            '''</div>
        <div class="summary-item">
            <span class="status ''' + ('passed' if passed else 'failed') + '''">
                ''' + ('通过 ✓' if passed else '失败 ✗') + '''
            </span>
        </div>
    </div>
''')
            
            # 缺失文件部分
            missing_files = self.results.get('missing_files', [])
            f.write('''
    <div class="section">
        <h2 class="section-header">缺失文件</h2>
        <div class="section-content">
''')
            
            if missing_files:
                f.write('            <table>\n')
                f.write('                <tr>\n')
                f.write('                    <th>#</th>\n')
                f.write('                    <th>文件路径</th>\n')
                f.write('                    <th>类型</th>\n')
                f.write('                    <th>说明</th>\n')
                f.write('                </tr>\n')
                
                for i, item in enumerate(missing_files, 1):
                    f.write('                <tr>\n')
                    f.write(f'                    <td>{i}</td>\n')
                    f.write(f'                    <td>{item.get("path", "")}</td>\n')
                    f.write(f'                    <td>{item.get("type", "")}</td>\n')
                    f.write(f'                    <td>{item.get("message", "")}</td>\n')
                    f.write('                </tr>\n')
                
                f.write('            </table>\n')
            else:
                f.write('            <div class="empty-message">无缺失文件</div>\n')
            
            f.write('''        </div>
    </div>
''')
            
            # 结构错误部分
            structure_errors = self.results.get('structure_errors', [])
            f.write('''
    <div class="section">
        <h2 class="section-header">结构错误</h2>
        <div class="section-content">
''')
            
            if structure_errors:
                f.write('            <table>\n')
                f.write('                <tr>\n')
                f.write('                    <th>#</th>\n')
                f.write('                    <th>类型</th>\n')
                f.write('                    <th>路径/模式</th>\n')
                f.write('                    <th>说明</th>\n')
                f.write('                </tr>\n')
                
                for i, item in enumerate(structure_errors, 1):
                    f.write('                <tr>\n')
                    f.write(f'                    <td>{i}</td>\n')
                    f.write(f'                    <td>{item.get("type", "")}</td>\n')
                    path_or_pattern = item.get('path', '') or item.get('pattern', '')
                    f.write(f'                    <td>{path_or_pattern}</td>\n')
                    f.write(f'                    <td>{item.get("message", "")}</td>\n')
                    f.write('                </tr>\n')
                
                f.write('            </table>\n')
            else:
                f.write('            <div class="empty-message">无结构错误</div>\n')
            
            f.write('''        </div>
    </div>
''')
            
            # 无效文件部分
            invalid_files = self.results.get('invalid_files', [])
            f.write('''
    <div class="section">
        <h2 class="section-header">无效文件</h2>
        <div class="section-content">
''')
            
            if invalid_files:
                f.write('            <table>\n')
                f.write('                <tr>\n')
                f.write('                    <th>#</th>\n')
                f.write('                    <th>文件路径</th>\n')
                f.write('                    <th>问题类型</th>\n')
                f.write('                    <th>说明</th>\n')
                f.write('                </tr>\n')
                
                for i, item in enumerate(invalid_files, 1):
                    f.write('                <tr>\n')
                    f.write(f'                    <td>{i}</td>\n')
                    f.write(f'                    <td>{item.get("path", "")}</td>\n')
                    f.write(f'                    <td>{item.get("issue", "")}</td>\n')
                    f.write(f'                    <td>{item.get("message", "")}</td>\n')
                    f.write('                </tr>\n')
                
                f.write('            </table>\n')
            else:
                f.write('            <div class="empty-message">无无效文件</div>\n')
            
            f.write('''        </div>
    </div>
</body>
</html>
''')
    
    def save_report(self, output_path, report_format='txt'):
        """保存验证报告"""
        ensure_directory(os.path.dirname(output_path))
        
        if report_format == 'txt':
            self.generate_txt_report(output_path)
        elif report_format == 'json':
            self.generate_json_report(output_path)
        elif report_format == 'html':
            self.generate_html_report(output_path)
        else:
            print(f"不支持的报告格式: {report_format}")
            return False
        
        print(f"报告已保存到: {output_path}")
        return True

def validate_single_directory(directory_path, config, output_report=None, report_format='txt'):
    """验证单个目录"""
    validator = FileStructureValidator(config)
    results = validator.run_full_validation(directory_path)
    
    # 打印摘要
    print("\n验证摘要:")
    print(f"总目录数: {results.get('total_directories', 0)}")
    print(f"总文件数: {results.get('total_files', 0)}")
    print(f"缺失文件数: {len(results.get('missing_files', []))}")
    print(f"结构错误数: {len(results.get('structure_errors', []))}")
    print(f"无效文件数: {len(results.get('invalid_files', []))}")
    
    # 保存报告
    if output_report:
        validator.save_report(output_report, report_format)
    
    # 返回是否通过
    return len(results.get('missing_files', [])) == 0 and \
           len(results.get('structure_errors', [])) == 0 and \
           len(results.get('invalid_files', [])) == 0

def batch_validate_directories(directories, config, output_dir, report_format='txt'):
    """批量验证多个目录"""
    ensure_directory(output_dir)
    
    # 结果汇总
    summary = {
        'total_directories': len(directories),
        'passed_directories': 0,
        'failed_directories': 0,
        'details': []
    }
    
    for i, directory in enumerate(tqdm(directories, desc="批量验证进度")):
        print(f"\n正在验证目录 {i+1}/{len(directories)}: {directory}")
        
        # 生成报告文件名
        dir_name = os.path.basename(directory)
        report_filename = f"report_{dir_name}_{i+1}.{report_format}"
        report_path = os.path.join(output_dir, report_filename)
        
        # 验证目录
        validator = FileStructureValidator(config)
        results = validator.run_full_validation(directory)
        
        # 保存报告
        validator.save_report(report_path, report_format)
        
        # 统计结果
        passed = len(results.get('missing_files', [])) == 0 and \
                len(results.get('structure_errors', [])) == 0 and \
                len(results.get('invalid_files', [])) == 0
        
        if passed:
            summary['passed_directories'] += 1
        else:
            summary['failed_directories'] += 1
        
        summary['details'].append({
            'directory': directory,
            'report_path': report_path,
            'passed': passed,
            'issues': {
                'missing_files': len(results.get('missing_files', [])),
                'structure_errors': len(results.get('structure_errors', [])),
                'invalid_files': len(results.get('invalid_files', []))
            }
        })
    
    # 生成汇总报告
    summary_report_path = os.path.join(output_dir, f"summary_report.{report_format}")
    if report_format == 'txt':
        with open(summary_report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("批量验证汇总报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总验证目录数: {summary['total_directories']}\n")
            f.write(f"通过目录数: {summary['passed_directories']}\n")
            f.write(f"失败目录数: {summary['failed_directories']}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("[详细结果]\n")
            f.write("-" * 80 + "\n")
            for detail in summary['details']:
                f.write(f"目录: {detail['directory']}\n")
                f.write(f"状态: {'通过 ✓' if detail['passed'] else '失败 ✗'}\n")
                f.write(f"报告路径: {detail['report_path']}\n")
                f.write(f"缺失文件数: {detail['issues']['missing_files']}\n")
                f.write(f"结构错误数: {detail['issues']['structure_errors']}\n")
                f.write(f"无效文件数: {detail['issues']['invalid_files']}\n")
                f.write("-" * 80 + "\n")
    
    elif report_format == 'json':
        with open(summary_report_path, 'w', encoding='utf-8') as f:
            summary['validation_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n批量验证完成！")
    print(f"总验证目录数: {summary['total_directories']}")
    print(f"通过目录数: {summary['passed_directories']}")
    print(f"失败目录数: {summary['failed_directories']}")
    print(f"汇总报告已保存到: {summary_report_path}")
    
    return summary

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='文件结构校验工具')
    
    # 输入输出参数
    parser.add_argument('--input', '-i', required=True, help='输入目录路径')
    parser.add_argument('--config', '-c', help='规则配置文件路径（JSON格式）')
    parser.add_argument('--output', '-o', help='输出报告路径')
    
    # 报告格式
    parser.add_argument('--format', '-f', default='txt', choices=['txt', 'json', 'html'],
                      help='报告格式')
    
    # 批量模式
    parser.add_argument('--batch', '-b', action='store_true', help='批量验证模式')
    parser.add_argument('--pattern', '-p', help='批量验证的目录匹配模式（例如 "data/*"）')
    
    # 快速规则参数
    parser.add_argument('--allowed-extensions', '-ae', nargs='+',
                      help='允许的文件扩展名列表（不包含点号）')
    parser.add_argument('--max-depth', '-md', type=int, help='最大目录深度')
    parser.add_argument('--exclude-dirs', '-ed', nargs='+',
                      help='要排除的目录列表')
    
    return parser.parse_args()

def build_config_from_args(args, config=None):
    """从命令行参数构建配置"""
    if config is None:
        config = {}
    
    # 应用命令行参数覆盖配置文件中的设置
    if args.allowed_extensions:
        config['allowed_extensions'] = args.allowed_extensions
    if args.max_depth is not None:
        config['max_directory_depth'] = args.max_depth
    if args.exclude_dirs:
        config['excluded_directories'] = args.exclude_dirs
    
    return config

def main():
    """主函数"""
    args = parse_arguments()
    
    # 加载配置
    config = {}
    if args.config:
        config = load_rule_config(args.config)
    
    # 从命令行参数构建配置
    config = build_config_from_args(args, config)
    
    if args.batch:
        # 批量验证模式
        if args.pattern:
            # 使用glob匹配多个目录
            directories = glob.glob(args.pattern)
            directories = [d for d in directories if os.path.isdir(d)]
        else:
            # 假设输入是包含多个子目录的父目录
            directories = [os.path.join(args.input, d) for d in os.listdir(args.input)
                         if os.path.isdir(os.path.join(args.input, d))]
        
        if not directories:
            print("错误：没有找到要验证的目录")
            return
        
        print(f"找到 {len(directories)} 个目录待验证")
        
        # 确定输出目录
        output_dir = args.output or os.path.join(os.getcwd(), 'validation_reports')
        
        # 批量验证
        batch_validate_directories(directories, config, output_dir, args.format)
    else:
        # 单目录验证模式
        if not os.path.isdir(args.input):
            print(f"错误：输入路径不是目录 {args.input}")
            return
        
        # 确定输出报告路径
        if not args.output:
            args.output = os.path.join(os.getcwd(), f"validation_report.{args.format}")
        
        # 验证目录
        passed = validate_single_directory(args.input, config, args.output, args.format)
        
        # 输出最终结果
        if passed:
            print("\n验证结果: 通过 ✓")
        else:
            print("\n验证结果: 失败 ✗")

if __name__ == "__main__":
    main()