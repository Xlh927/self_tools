#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本/配置文件处理模块（C4）

功能：
- JSON/YAML/CSV 校验
- 批量 JSON 修复（补逗号/格式错误）
- 编码转换（GBK ⇄ UTF-8）

支持单文件和批量文件夹处理
"""

import os
import re
import json
import yaml
import csv
import argparse
import glob
from typing import List, Dict, Any, Optional


def validate_json_file(file_path: str) -> Dict[str, Any]:
    """
    验证JSON文件
    
    Args:
        file_path: JSON文件路径
    
    Returns:
        包含验证结果的字典
    """
    result = {
        "file": file_path,
        "valid": False,
        "error": None,
        "data": None
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result["valid"] = True
        result["data"] = data
    except json.JSONDecodeError as e:
        result["error"] = f"JSON解析错误: {str(e)}"
    except UnicodeDecodeError:
        # 尝试GBK编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                data = json.load(f)
            result["valid"] = True
            result["data"] = data
        except Exception as e:
            result["error"] = f"编码错误: {str(e)}"
    except Exception as e:
        result["error"] = f"验证失败: {str(e)}"
    
    return result


def validate_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    验证YAML文件
    
    Args:
        file_path: YAML文件路径
    
    Returns:
        包含验证结果的字典
    """
    result = {
        "file": file_path,
        "valid": False,
        "error": None,
        "data": None
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        result["valid"] = True
        result["data"] = data
    except yaml.YAMLError as e:
        result["error"] = f"YAML解析错误: {str(e)}"
    except UnicodeDecodeError:
        # 尝试GBK编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                data = yaml.safe_load(f)
            result["valid"] = True
            result["data"] = data
        except Exception as e:
            result["error"] = f"编码错误: {str(e)}"
    except Exception as e:
        result["error"] = f"验证失败: {str(e)}"
    
    return result


def validate_csv_file(file_path: str) -> Dict[str, Any]:
    """
    验证CSV文件
    
    Args:
        file_path: CSV文件路径
    
    Returns:
        包含验证结果的字典
    """
    result = {
        "file": file_path,
        "valid": False,
        "error": None,
        "rows": 0,
        "columns": 0
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if rows:
            result["rows"] = len(rows)
            result["columns"] = len(rows[0])
        result["valid"] = True
    except UnicodeDecodeError:
        # 尝试GBK编码
        try:
            with open(file_path, 'r', encoding='gbk', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            if rows:
                result["rows"] = len(rows)
                result["columns"] = len(rows[0])
            result["valid"] = True
        except Exception as e:
            result["error"] = f"编码错误: {str(e)}"
    except Exception as e:
        result["error"] = f"验证失败: {str(e)}"
    
    return result


def fix_json_file(file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    修复JSON文件中的常见错误
    
    Args:
        file_path: 源JSON文件路径
        output_path: 修复后的输出文件路径，None表示覆盖原文件
    
    Returns:
        包含修复结果的字典
    """
    result = {
        "file": file_path,
        "fixed": False,
        "error": None
    }
    
    # 如果未指定输出路径，使用原文件
    if output_path is None:
        output_path = file_path
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 常见JSON修复：
        # 1. 修复末尾缺少逗号
        content = re.sub(r'\}\s*\n\s*{', '},\n{', content)
        content = re.sub(r'"\}\s*\n\s*"', '"},\n"', content)
        
        # 2. 修复多余的逗号
        content = re.sub(r',\s*\}', '}', content)
        content = re.sub(r',\s*\]', ']', content)
        
        # 3. 修复字符串中的换行符
        content = content.replace('\n', '\\n')
        
        # 4. 尝试解析修复后的内容
        json.loads(content)
        
        # 写入修复后的内容
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result["fixed"] = True
        print(f"修复成功: {file_path} -> {output_path}")
    
    except Exception as e:
        result["error"] = f"修复失败: {str(e)}"
        print(f"修复失败 {file_path}: {str(e)}")
    
    return result


def convert_encoding(
    file_path: str,
    output_path: Optional[str] = None,
    from_encoding: str = 'gbk',
    to_encoding: str = 'utf-8'
) -> Dict[str, Any]:
    """
    转换文件编码
    
    Args:
        file_path: 源文件路径
        output_path: 输出文件路径，None表示覆盖原文件
        from_encoding: 源编码
        to_encoding: 目标编码
    
    Returns:
        包含转换结果的字典
    """
    result = {
        "file": file_path,
        "converted": False,
        "error": None
    }
    
    # 如果未指定输出路径，使用原文件
    if output_path is None:
        output_path = file_path
    
    try:
        # 读取源文件
        with open(file_path, 'r', encoding=from_encoding) as f:
            content = f.read()
        
        # 写入目标编码文件
        with open(output_path, 'w', encoding=to_encoding) as f:
            f.write(content)
        
        result["converted"] = True
        print(f"编码转换成功: {file_path} ({from_encoding} -> {to_encoding})")
    except UnicodeDecodeError:
        result["error"] = f"无法使用 {from_encoding} 解码文件"
        print(f"编码转换失败 {file_path}: 无法使用 {from_encoding} 解码")
    except Exception as e:
        result["error"] = f"转换失败: {str(e)}"
        print(f"编码转换失败 {file_path}: {str(e)}")
    
    return result


def batch_process_files(
    input_path: str,
    file_type: str,
    operation: str,
    recursive: bool = False,
    output_dir: Optional[str] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    批量处理文件
    
    Args:
        input_path: 输入文件或目录路径
        file_type: 文件类型 (json/yaml/csv)
        operation: 操作类型 (validate/fix/convert)
        recursive: 是否递归处理子目录
        output_dir: 输出目录
        **kwargs: 其他参数
    
    Returns:
        处理结果列表
    """
    results = []
    
    # 检查输入路径是否存在
    if not os.path.exists(input_path):
        print(f"错误：路径不存在 - {input_path}")
        return results
    
    # 确定文件扩展名
    ext_map = {
        'json': ['.json'],
        'yaml': ['.yaml', '.yml'],
        'csv': ['.csv']
    }
    extensions = ext_map.get(file_type, [])
    
    # 获取文件列表
    if os.path.isfile(input_path):
        # 单文件处理
        file_list = [input_path]
    else:
        # 目录处理
        if recursive:
            glob_pattern = os.path.join(input_path, "**", "*")
        else:
            glob_pattern = os.path.join(input_path, "*")
        
        file_list = [
            f for f in glob.glob(glob_pattern, recursive=recursive)
            if os.path.isfile(f) and any(f.lower().endswith(ext) for ext in extensions)
        ]
    
    # 确保输出目录存在
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 处理每个文件
    for file_path in file_list:
        # 确定输出路径
        if output_dir:
            base_name = os.path.basename(file_path)
            output_path = os.path.join(output_dir, base_name)
        else:
            output_path = None
        
        # 执行相应操作
        if operation == 'validate':
            if file_type == 'json':
                result = validate_json_file(file_path)
            elif file_type == 'yaml':
                result = validate_yaml_file(file_path)
            elif file_type == 'csv':
                result = validate_csv_file(file_path)
        elif operation == 'fix' and file_type == 'json':
            result = fix_json_file(file_path, output_path)
        elif operation == 'convert':
            result = convert_encoding(
                file_path, 
                output_path,
                kwargs.get('from_encoding', 'gbk'),
                kwargs.get('to_encoding', 'utf-8')
            )
        else:
            print(f"不支持的操作: {operation} 对于 {file_type}")
            continue
        
        results.append(result)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="文本/配置文件处理工具")
    
    # 基本参数
    parser.add_argument("-i", "--input", required=True, help="输入文件或目录路径")
    parser.add_argument("-o", "--output", help="输出目录路径")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    
    # 文件类型选择
    parser.add_argument(
        "--type", 
        choices=["json", "yaml", "csv"], 
        default="json",
        help="文件类型 (默认: json)"
    )
    
    # 功能选择组
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate", action="store_true", help="验证文件格式")
    group.add_argument("--fix", action="store_true", help="修复JSON文件")
    group.add_argument("--convert", action="store_true", help="转换文件编码")
    
    # 编码转换参数
    parser.add_argument("--from", dest="from_encoding", default="gbk", help="源编码 (默认: gbk)")
    parser.add_argument("--to", dest="to_encoding", default="utf-8", help="目标编码 (默认: utf-8)")
    
    args = parser.parse_args()
    
    # 检查参数组合
    if args.fix and args.type != "json":
        parser.error("修复功能仅支持JSON文件")
    
    # 确定操作类型
    if args.validate:
        operation = "validate"
    elif args.fix:
        operation = "fix"
    elif args.convert:
        operation = "convert"
    
    # 批量处理文件
    kwargs = {}
    if operation == "convert":
        kwargs["from_encoding"] = args.from_encoding
        kwargs["to_encoding"] = args.to_encoding
    
    results = batch_process_files(
        input_path=args.input,
        file_type=args.type,
        operation=operation,
        recursive=args.recursive,
        output_dir=args.output,
        **kwargs
    )
    
    # 统计结果
    if operation == "validate":
        valid_count = sum(1 for r in results if r.get("valid", False))
        print(f"\n验证完成。总共: {len(results)}, 有效: {valid_count}, 无效: {len(results) - valid_count}")
    elif operation == "fix":
        fixed_count = sum(1 for r in results if r.get("fixed", False))
        print(f"\n修复完成。总共: {len(results)}, 成功: {fixed_count}, 失败: {len(results) - fixed_count}")
    elif operation == "convert":
        converted_count = sum(1 for r in results if r.get("converted", False))
        print(f"\n转换完成。总共: {len(results)}, 成功: {converted_count}, 失败: {len(results) - converted_count}")


if __name__ == "__main__":
    main()