#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析scripts目录下所有Python脚本，提取其功能描述
"""

import os
import re
import json
import subprocess
import sys

# 脚本目录路径
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')

# 结果输出文件
OUTPUT_FILE = 'scripts_info.json'

def extract_script_params(file_path):
    """
    提取脚本的参数信息并生成默认值
    """
    params = []
    
    # 基础参数，大多数脚本都会用到
    basic_params = [
        {
            'name': 'input_path',
            'type': 'string',
            'required': True,
            'help': '输入文件或目录路径',
            'default': './input'
        },
        {
            'name': 'output_path',
            'type': 'string',
            'required': True,
            'help': '输出文件或目录路径',
            'default': './output'
        },
        {
            'name': 'verbose',
            'type': 'boolean',
            'required': False,
            'help': '启用详细输出模式',
            'default': False
        }
    ]
    
    # 尝试通过--help获取参数信息
    try:
        result = subprocess.run(
            [sys.executable, file_path, '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            help_text = result.stdout
            
            # 基于文件名添加特定的默认参数
            filename = os.path.basename(file_path)
            
            # 为不同类型的脚本添加特定参数
            if 'image' in filename or 'video' in filename:
                # 图像处理脚本特定参数
                image_params = [
                    {
                        'name': 'width',
                        'type': 'integer',
                        'required': False,
                        'help': '输出图像宽度',
                        'default': 800
                    },
                    {
                        'name': 'height',
                        'type': 'integer',
                        'required': False,
                        'help': '输出图像高度',
                        'default': 600
                    },
                    {
                        'name': 'quality',
                        'type': 'integer',
                        'required': False,
                        'help': '输出图像质量(0-100)',
                        'default': 90
                    }
                ]
                params.extend(image_params)
            
            if 'dataset' in filename or 'data' in filename:
                # 数据集处理脚本特定参数
                dataset_params = [
                    {
                        'name': 'split_ratio',
                        'type': 'float',
                        'required': False,
                        'help': '数据集分割比例',
                        'default': 0.8
                    },
                    {
                        'name': 'seed',
                        'type': 'integer',
                        'required': False,
                        'help': '随机种子',
                        'default': 42
                    }
                ]
                params.extend(dataset_params)
            
            if 'file' in filename or 'rename' in filename:
                # 文件处理脚本特定参数
                file_params = [
                    {
                        'name': 'pattern',
                        'type': 'string',
                        'required': False,
                        'help': '文件匹配模式',
                        'default': '*.txt'
                    },
                    {
                        'name': 'recursive',
                        'type': 'boolean',
                        'required': False,
                        'help': '递归处理子目录',
                        'default': True
                    }
                ]
                params.extend(file_params)
    except Exception as e:
        print(f"获取脚本参数帮助失败: {str(e)}")
    
    # 添加基础参数
    params = basic_params + params
    
    return params

def extract_script_info(file_path):
    """
    从Python文件中提取模块名称、功能描述和参数信息
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取模块名称（文件名去掉.py后缀）
        module_name = os.path.basename(file_path).replace('.py', '')
        
        # 尝试从注释中提取模块名称和功能描述
        # 匹配"模块名称（代码）"和功能列表
        name_pattern = r'"""\s*([^（]*?)\s*\(\w+\)\s*'  # 匹配模块名称
        func_pattern = r'功能：\s*\n(.*?)\s*支持'  # 匹配功能描述
        
        name_match = re.search(name_pattern, content, re.DOTALL)
        func_match = re.search(func_pattern, content, re.DOTALL)
        
        # 如果没找到，则使用更通用的模式
        if not name_match:
            name_pattern_alt = r'"""\s*(.+?)\s*'  # 匹配第一行注释
            name_match = re.search(name_pattern_alt, content, re.DOTALL)
            module_display_name = name_match.group(1).strip() if name_match else module_name
        else:
            module_display_name = name_match.group(1).strip()
        
        if not func_match:
            # 尝试找到功能描述的其他格式
            func_pattern_alt = r'功能：(.*?)\s*"""'
            func_match = re.search(func_pattern_alt, content, re.DOTALL)
            
            if func_match:
                func_text = func_match.group(1).strip()
                # 分割功能列表
                functions = [line.strip('- ').strip() for line in func_text.split('\n') if line.strip()]
            else:
                functions = ['功能描述未找到']
        else:
            func_text = func_match.group(1).strip()
            # 分割功能列表
            functions = [line.strip('- ').strip() for line in func_text.split('\n') if line.strip()]
        
        # 提取脚本参数信息
        params = extract_script_params(file_path)
        
        return {
            'module_name': module_name,
            'display_name': module_display_name,
            'file_path': os.path.relpath(file_path, SCRIPTS_DIR),
            'functions': functions,
            'params': params
        }
    except Exception as e:
        print(f"解析文件 {file_path} 时出错: {str(e)}")
        return {
            'module_name': os.path.basename(file_path).replace('.py', ''),
            'display_name': os.path.basename(file_path).replace('.py', ''),
            'file_path': os.path.relpath(file_path, SCRIPTS_DIR),
            'functions': ['解析失败']
        }

def analyze_scripts():
    """
    分析scripts目录下的所有Python脚本
    """
    scripts_info = []
    
    # 获取scripts目录下所有.py文件
    for filename in os.listdir(SCRIPTS_DIR):
        if filename.endswith('.py') and not filename.startswith('__'):
            file_path = os.path.join(SCRIPTS_DIR, filename)
            script_info = extract_script_info(file_path)
            scripts_info.append(script_info)
    
    # 按模块名称排序
    scripts_info.sort(key=lambda x: x['display_name'])
    
    # 保存结果到JSON文件
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    
    # 转换为字典格式，便于快速查找
    scripts_dict = {}
    for script in scripts_info:
        module_name = script['module_name']
        # 创建简化版本的脚本信息字典
        scripts_dict[module_name] = {
            'display_name': script['display_name'],
            'functions': script['functions'],
            'params': script['params']
        }
    
    # 保存完整信息和简化字典
    output_data = {
        'scripts_list': scripts_info,
        'scripts_dict': scripts_dict
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"分析完成，共找到 {len(scripts_info)} 个脚本")
    print(f"结果已保存到 {output_path}")
    
    # 打印脚本列表及其功能摘要
    print("\n脚本列表:")
    for i, script in enumerate(scripts_info, 1):
        print(f"{i}. {script['display_name']} ({script['module_name']})")
        for func in script['functions'][:3]:  # 只显示前3个功能
            print(f"   - {func}")
        if len(script['functions']) > 3:
            print(f"   - ... 还有 {len(script['functions']) - 3} 个功能")
    
    return scripts_info

if __name__ == "__main__":
    analyze_scripts()
