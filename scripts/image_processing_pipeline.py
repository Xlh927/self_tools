#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像处理流程管理模块（A7）

功能：
- 图像处理流程构建与管理
- 任务调度与执行
- 并行处理支持
- 异常处理与日志记录
- 流程可视化与导出
- 支持单文件和批量文件夹处理
"""

import os
import sys
import json
import yaml
import logging
import argparse
import importlib
import time
import uuid
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Callable, Tuple, Optional, Union
import networkx as nx
import matplotlib.pyplot as plt
import cv2
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("image_processing_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ImageProcessingPipeline")

class PipelineStage:
    """流水线阶段类"""
    
    def __init__(self, name: str, processor: Callable, params: Dict[str, Any] = None):
        """
        初始化流水线阶段
        
        Args:
            name: 阶段名称
            processor: 处理函数
            params: 阶段参数
        """
        self.name = name
        self.processor = processor
        self.params = params or {}
        self.id = str(uuid.uuid4())[:8]
        self.inputs = []
        self.outputs = []
        self.execution_time = 0
        self.success = False
        self.error_message = None
    
    def execute(self, input_data: Any) -> Any:
        """
        执行阶段处理
        
        Args:
            input_data: 输入数据
            
        Returns:
            处理后的输出数据
        """
        start_time = time.time()
        try:
            logger.info(f"执行阶段: {self.name} (ID: {self.id})")
            # 执行处理函数
            output = self.processor(input_data, **self.params)
            self.execution_time = time.time() - start_time
            self.success = True
            logger.info(f"阶段 {self.name} 执行成功，耗时: {self.execution_time:.4f}s")
            return output
        except Exception as e:
            self.execution_time = time.time() - start_time
            self.success = False
            self.error_message = str(e)
            logger.error(f"阶段 {self.name} 执行失败: {self.error_message}")
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "params": self.params,
            "execution_time": self.execution_time,
            "success": self.success,
            "error_message": self.error_message
        }

class ImageProcessingPipeline:
    """图像处理流水线类"""
    
    def __init__(self, name: str = "default_pipeline"):
        """
        初始化图像处理流水线
        
        Args:
            name: 流水线名称
        """
        self.name = name
        self.stages = []
        self.stage_map = {}
        self.graph = nx.DiGraph()
        self.execution_history = []
        self.created_at = datetime.now().isoformat()
    
    def add_stage(self, name: str, processor: Callable, params: Dict[str, Any] = None) -> "ImageProcessingPipeline":
        """
        添加处理阶段
        
        Args:
            name: 阶段名称
            processor: 处理函数
            params: 阶段参数
            
        Returns:
            流水线实例（支持链式调用）
        """
        # 检查阶段名称是否已存在
        for stage in self.stages:
            if stage.name == name:
                logger.warning(f"阶段名称 '{name}' 已存在，添加失败")
                return self
        
        stage = PipelineStage(name, processor, params)
        self.stages.append(stage)
        self.stage_map[name] = stage
        
        # 更新图结构
        self.graph.add_node(stage.id, name=stage.name)
        
        # 如果不是第一个阶段，添加边
        if len(self.stages) > 1:
            prev_stage = self.stages[-2]
            self.graph.add_edge(prev_stage.id, stage.id)
            prev_stage.outputs.append(stage.id)
            stage.inputs.append(prev_stage.id)
        
        logger.info(f"添加阶段: {name}")
        return self
    
    def add_dependency(self, from_stage_name: str, to_stage_name: str) -> "ImageProcessingPipeline":
        """
        添加阶段间依赖关系
        
        Args:
            from_stage_name: 源阶段名称
            to_stage_name: 目标阶段名称
            
        Returns:
            流水线实例（支持链式调用）
        """
        if from_stage_name not in self.stage_map or to_stage_name not in self.stage_map:
            logger.error(f"依赖关系添加失败: 阶段不存在")
            return self
        
        from_stage = self.stage_map[from_stage_name]
        to_stage = self.stage_map[to_stage_name]
        
        # 检查是否会形成环
        if to_stage.id in self.graph and from_stage.id in self.graph and nx.has_path(self.graph, to_stage.id, from_stage.id):
            logger.error(f"依赖关系添加失败: 会形成环")
            return self
        
        self.graph.add_edge(from_stage.id, to_stage.id)
        from_stage.outputs.append(to_stage.id)
        to_stage.inputs.append(from_stage.id)
        
        logger.info(f"添加依赖关系: {from_stage_name} -> {to_stage_name}")
        return self
    
    def execute(self, input_data: Any, start_stage: str = None, end_stage: str = None) -> Any:
        """
        执行流水线
        
        Args:
            input_data: 输入数据
            start_stage: 起始阶段名称
            end_stage: 结束阶段名称
            
        Returns:
            流水线输出结果
        """
        start_time = time.time()
        execution_id = str(uuid.uuid4())
        logger.info(f"开始执行流水线: {self.name} (ID: {execution_id})")
        
        try:
            # 确定执行的阶段范围
            start_index = 0
            end_index = len(self.stages)
            
            if start_stage:
                for i, stage in enumerate(self.stages):
                    if stage.name == start_stage:
                        start_index = i
                        break
            
            if end_stage:
                for i, stage in enumerate(self.stages):
                    if stage.name == end_stage:
                        end_index = i + 1
                        break
            
            # 执行阶段
            current_data = input_data
            for stage in self.stages[start_index:end_index]:
                current_data = stage.execute(current_data)
            
            total_time = time.time() - start_time
            logger.info(f"流水线执行完成，总耗时: {total_time:.4f}s")
            
            # 记录执行历史
            self.execution_history.append({
                "id": execution_id,
                "start_time": start_time,
                "end_time": time.time(),
                "duration": total_time,
                "stages": [stage.to_dict() for stage in self.stages[start_index:end_index]],
                "success": all(stage.success for stage in self.stages[start_index:end_index])
            })
            
            return current_data
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"流水线执行失败: {str(e)}")
            
            # 记录失败的执行历史
            self.execution_history.append({
                "id": execution_id,
                "start_time": start_time,
                "end_time": time.time(),
                "duration": total_time,
                "stages": [stage.to_dict() for stage in self.stages],
                "success": False,
                "error": str(e)
            })
            
            raise
    
    def execute_parallel(self, input_data_list: List[Any], max_workers: int = None, 
                        start_stage: str = None, end_stage: str = None) -> List[Any]:
        """
        并行执行流水线处理多个输入
        
        Args:
            input_data_list: 输入数据列表
            max_workers: 最大工作线程数
            start_stage: 起始阶段名称
            end_stage: 结束阶段名称
            
        Returns:
            处理结果列表
        """
        start_time = time.time()
        logger.info(f"开始并行执行流水线，输入数量: {len(input_data_list)}, 最大工作线程数: {max_workers}")
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_input = {executor.submit(self.execute, input_data, start_stage, end_stage): input_data 
                              for input_data in input_data_list}
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_input):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    input_data = future_to_input[future]
                    logger.error(f"并行处理失败，输入: {input_data}, 错误: {str(e)}")
                    results.append(None)
        
        total_time = time.time() - start_time
        logger.info(f"并行执行完成，总耗时: {total_time:.4f}s")
        
        return results
    
    def save_pipeline(self, output_path: str) -> bool:
        """
        保存流水线配置
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否保存成功
        """
        try:
            # 构建流水线配置
            pipeline_config = {
                "name": self.name,
                "created_at": self.created_at,
                "stages": []
            }
            
            for stage in self.stages:
                stage_config = {
                    "name": stage.name,
                    "params": stage.params
                }
                pipeline_config["stages"].append(stage_config)
            
            # 保存为JSON或YAML
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            file_ext = os.path.splitext(output_path)[1].lower()
            if file_ext == '.json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(pipeline_config, f, indent=2, ensure_ascii=False)
            elif file_ext in ['.yaml', '.yml']:
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(pipeline_config, f, default_flow_style=False, allow_unicode=True)
            else:
                logger.error(f"不支持的文件格式: {file_ext}")
                return False
            
            logger.info(f"流水线配置已保存到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"保存流水线配置失败: {str(e)}")
            return False
    
    def visualize_pipeline(self, output_path: str = None, show: bool = False) -> bool:
        """
        可视化流水线结构
        
        Args:
            output_path: 输出图像路径
            show: 是否显示图像
            
        Returns:
            是否可视化成功
        """
        try:
            plt.figure(figsize=(10, 6))
            
            # 设置节点标签
            labels = {node: self.stage_map[attr['name']].name for node, attr in self.graph.nodes(data=True)}
            
            # 绘制图
            pos = nx.spring_layout(self.graph, seed=42)
            nx.draw_networkx_nodes(self.graph, pos, node_size=700, node_color='lightblue')
            nx.draw_networkx_edges(self.graph, pos, arrowstyle='->', arrowsize=20)
            nx.draw_networkx_labels(self.graph, pos, labels, font_size=12, font_weight='bold')
            
            plt.title(f"图像处理流水线: {self.name}")
            plt.axis('off')
            
            # 保存图像
            if output_path:
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                logger.info(f"流水线可视化已保存到: {output_path}")
            
            # 显示图像
            if show:
                plt.show()
            
            plt.close()
            return True
        except Exception as e:
            logger.error(f"流水线可视化失败: {str(e)}")
            return False
    
    def export_execution_report(self, output_path: str, format: str = 'json') -> bool:
        """
        导出执行报告
        
        Args:
            output_path: 输出文件路径
            format: 输出格式
            
        Returns:
            是否导出成功
        """
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            if format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(self.execution_history, f, indent=2, ensure_ascii=False, default=str)
            elif format == 'html':
                # 生成HTML报告
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>图像处理流水线执行报告 - {self.name}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1 {{ color: #333; }}
                        .execution {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                        .success {{ background-color: #f9fff9; }}
                        .failed {{ background-color: #fff9f9; }}
                        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                        .error {{ color: red; }}
                    </style>
                </head>
                <body>
                    <h1>图像处理流水线执行报告</h1>
                    <h2>流水线名称: {self.name}</h2>
                    <p>创建时间: {self.created_at}</p>
                    <p>执行次数: {len(self.execution_history)}</p>
                """
                
                for execution in self.execution_history:
                    status_class = "success" if execution.get("success", False) else "failed"
                    html_content += f"""
                    <div class="execution {status_class}">
                        <h3>执行 ID: {execution['id']}</h3>
                        <p>开始时间: {datetime.fromtimestamp(execution['start_time'])}</p>
                        <p>结束时间: {datetime.fromtimestamp(execution['end_time'])}</p>
                        <p>总耗时: {execution['duration']:.4f} 秒</p>
                        <p>状态: {'成功' if execution.get('success', False) else '失败'}</p>
                    """
                    
                    if 'error' in execution:
                        html_content += f"<p class='error'>错误信息: {execution['error']}</p>"
                    
                    html_content += "<table>
                        <tr>
                            <th>阶段名称</th>
                            <th>状态</th>
                            <th>耗时 (秒)</th>
                            <th>错误信息</th>
                        </tr>"
                    
                    for stage in execution['stages']:
                        stage_name = "未知"  # 默认值
                        # 尝试从stage_map中获取阶段名称
                        for name, s in self.stage_map.items():
                            if s.id == stage['id']:
                                stage_name = name
                                break
                        # 如果还是未知，则使用stage字典中的name属性（如果存在）
                        if stage_name == "未知" and 'name' in stage:
                            stage_name = stage['name']
                        
                        html_content += f"""
                        <tr>
                            <td>{stage_name}</td>
                            <td>{'成功' if stage.get('success', False) else '失败'}</td>
                            <td>{stage.get('execution_time', 0):.4f}</td>
                            <td>{stage.get('error_message', '')}</td>
                        </tr>
                        """
                    
                    html_content += "</table></div>"
                
                html_content += "</body></html>"
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            else:
                logger.error(f"不支持的导出格式: {format}")
                return False
            
            logger.info(f"执行报告已导出到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出执行报告失败: {str(e)}")
            return False

def load_pipeline_from_file(config_path: str, custom_processors: Dict[str, Callable] = None) -> Optional[ImageProcessingPipeline]:
    """
    从配置文件加载流水线
    
    Args:
        config_path: 配置文件路径
        custom_processors: 自定义处理器字典
        
    Returns:
        流水线实例
    """
    try:
        # 读取配置文件
        file_ext = os.path.splitext(config_path)[1].lower()
        if file_ext == '.json':
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        elif file_ext in ['.yaml', '.yml']:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        else:
            logger.error(f"不支持的配置文件格式: {file_ext}")
            return None
        
        # 创建流水线
        pipeline = ImageProcessingPipeline(name=config.get('name', 'loaded_pipeline'))
        
        # 添加阶段
        for stage_config in config.get('stages', []):
            stage_name = stage_config.get('name')
            stage_params = stage_config.get('params', {})
            
            # 获取处理器
            processor = None
            if custom_processors and stage_name in custom_processors:
                processor = custom_processors[stage_name]
            else:
                # 尝试从预定义处理器中获取
                processor = get_predefined_processor(stage_name)
            
            if processor:
                pipeline.add_stage(stage_name, processor, stage_params)
            else:
                logger.warning(f"无法找到处理器: {stage_name}")
        
        logger.info(f"从配置文件加载流水线: {config_path}")
        return pipeline
    except Exception as e:
        logger.error(f"加载流水线配置失败: {str(e)}")
        return None

def get_predefined_processor(processor_name: str) -> Optional[Callable]:
    """
    获取预定义处理器
    
    Args:
        processor_name: 处理器名称
        
    Returns:
        处理器函数
    """
    # 预定义的简单处理器
    processors = {
        "resize": lambda img, width=500, height=500: cv2.resize(img, (width, height)),
        "grayscale": lambda img: cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img,
        "blur": lambda img, ksize=5: cv2.GaussianBlur(img, (ksize, ksize), 0),
        "edge_detection": lambda img, low_threshold=50, high_threshold=150: cv2.Canny(img, low_threshold, high_threshold),
        "brightness": lambda img, factor=1.0: cv2.convertScaleAbs(img, alpha=factor, beta=0),
        "contrast": lambda img, alpha=1.0, beta=0: cv2.convertScaleAbs(img, alpha=alpha, beta=beta),
        "rotate": lambda img, angle=90: cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE) if angle == 90 else \
                                        cv2.rotate(img, cv2.ROTATE_180) if angle == 180 else \
                                        cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE),
        "flip": lambda img, direction=1: cv2.flip(img, direction),
        "crop": lambda img, x=0, y=0, width=None, height=None: img[y:y+height, x:x+width] if width and height else img,
        "normalize": lambda img: img / 255.0
    }
    
    return processors.get(processor_name)

def load_external_module(module_path: str, function_name: str) -> Optional[Callable]:
    """
    加载外部模块中的函数
    
    Args:
        module_path: 模块路径
        function_name: 函数名称
        
    Returns:
        函数对象
    """
    try:
        # 获取模块名和文件路径
        module_dir = os.path.dirname(module_path)
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        
        # 添加模块目录到系统路径
        sys.path.append(module_dir)
        
        # 导入模块
        module = importlib.import_module(module_name)
        
        # 获取函数
        function = getattr(module, function_name)
        
        return function
    except Exception as e:
        logger.error(f"加载外部模块失败: {str(e)}")
        return None

def process_single_image(image_path: str, pipeline: ImageProcessingPipeline, output_path: str = None) -> Optional[np.ndarray]:
    """
    处理单个图像
    
    Args:
        image_path: 输入图像路径
        pipeline: 图像处理流水线
        output_path: 输出图像路径
        
    Returns:
        处理后的图像
    """
    try:
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        # 执行流水线
        processed_image = pipeline.execute(image)
        
        # 保存结果
        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            cv2.imwrite(output_path, processed_image)
            logger.info(f"处理后的图像已保存到: {output_path}")
        
        return processed_image
    except Exception as e:
        logger.error(f"处理图像失败: {str(e)}")
        return None

def process_directory(input_dir: str, pipeline: ImageProcessingPipeline, output_dir: str, 
                      recursive: bool = False, image_extensions: List[str] = None) -> Dict[str, str]:
    """
    批量处理目录中的图像
    
    Args:
        input_dir: 输入目录
        pipeline: 图像处理流水线
        output_dir: 输出目录
        recursive: 是否递归处理子目录
        image_extensions: 图像文件扩展名列表
        
    Returns:
        处理结果映射（输入路径 -> 输出路径）
    """
    if image_extensions is None:
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    results = {}
    processed_count = 0
    failed_count = 0
    
    # 遍历目录
    for root, _, files in os.walk(input_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                # 构建输入路径
                input_path = os.path.join(root, file)
                
                # 构建输出路径
                if recursive:
                    # 保持目录结构
                    relative_path = os.path.relpath(root, input_dir)
                    output_subdir = os.path.join(output_dir, relative_path)
                else:
                    output_subdir = output_dir
                
                output_path = os.path.join(output_subdir, file)
                
                # 处理图像
                if process_single_image(input_path, pipeline, output_path):
                    results[input_path] = output_path
                    processed_count += 1
                else:
                    failed_count += 1
        
        # 如果不递归，只处理顶层目录
        if not recursive:
            break
    
    logger.info(f"批量处理完成，成功: {processed_count}, 失败: {failed_count}")
    return results

def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='图像处理流水线管理工具')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 创建流水线命令
    create_parser = subparsers.add_parser('create', help='创建流水线')
    create_parser.add_argument('--name', '-n', default='new_pipeline', help='流水线名称')
    create_parser.add_argument('--output', '-o', required=True, help='输出配置文件路径')
    create_parser.add_argument('--stages', '-s', nargs='+', help='阶段配置，格式为 "name:processor:param1=value1:param2=value2"')
    
    # 执行流水线命令
    execute_parser = subparsers.add_parser('execute', help='执行流水线')
    execute_parser.add_argument('--config', '-c', required=True, help='流水线配置文件路径')
    execute_parser.add_argument('--input', '-i', required=True, help='输入图像或目录路径')
    execute_parser.add_argument('--output', '-o', required=True, help='输出目录路径')
    execute_parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    execute_parser.add_argument('--parallel', '-p', type=int, default=0, help='并行处理线程数，0表示不并行')
    
    # 可视化流水线命令
    visualize_parser = subparsers.add_parser('visualize', help='可视化流水线')
    visualize_parser.add_argument('--config', '-c', required=True, help='流水线配置文件路径')
    visualize_parser.add_argument('--output', '-o', required=True, help='输出图像路径')
    visualize_parser.add_argument('--show', action='store_true', help='显示图像')
    
    # 导出报告命令
    report_parser = subparsers.add_parser('report', help='导出执行报告')
    report_parser.add_argument('--config', '-c', required=True, help='流水线配置文件路径')
    report_parser.add_argument('--output', '-o', required=True, help='输出报告路径')
    report_parser.add_argument('--format', default='json', choices=['json', 'html'], help='报告格式')
    
    return parser.parse_args()

def create_pipeline_from_args(args):
    """
    根据命令行参数创建流水线
    """
    pipeline = ImageProcessingPipeline(name=args.name)
    
    # 添加阶段
    if args.stages:
        for stage_config in args.stages:
            parts = stage_config.split(':')
            if len(parts) < 2:
                logger.error(f"无效的阶段配置: {stage_config}")
                continue
            
            stage_name = parts[0]
            processor_name = parts[1]
            
            # 解析参数
            params = {}
            for param_part in parts[2:]:
                if '=' in param_part:
                    key, value = param_part.split('=', 1)
                    # 尝试转换值类型
                    try:
                        if value.lower() == 'true':
                            params[key] = True
                        elif value.lower() == 'false':
                            params[key] = False
                        elif '.' in value:
                            params[key] = float(value)
                        else:
                            params[key] = int(value)
                    except ValueError:
                        params[key] = value
            
            # 获取处理器
            processor = get_predefined_processor(processor_name)
            
            if processor:
                pipeline.add_stage(stage_name, processor, params)
            else:
                logger.warning(f"无法找到处理器: {processor_name}")
    
    # 保存流水线
    if pipeline.save_pipeline(args.output):
        print(f"流水线已创建并保存到: {args.output}")

def execute_pipeline_from_args(args):
    """
    根据命令行参数执行流水线
    """
    # 加载流水线
    pipeline = load_pipeline_from_file(args.config)
    if not pipeline:
        print("加载流水线失败")
        return
    
    # 确保输出目录存在
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # 处理输入
    if os.path.isfile(args.input):
        # 处理单个文件
        output_path = os.path.join(args.output, os.path.basename(args.input))
        if process_single_image(args.input, pipeline, output_path):
            print(f"图像处理完成: {output_path}")
    elif os.path.isdir(args.input):
        # 批量处理目录
        if args.parallel > 0:
            # 收集所有图像文件
            image_files = []
            for root, _, files in os.walk(args.input):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']):
                        image_files.append(os.path.join(root, file))
                if not args.recursive:
                    break
            
            # 并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
                futures = []
                for image_file in image_files:
                    # 构建输出路径
                    if args.recursive:
                        relative_path = os.path.relpath(os.path.dirname(image_file), args.input)
                        output_subdir = os.path.join(args.output, relative_path)
                    else:
                        output_subdir = args.output
                    
                    if not os.path.exists(output_subdir):
                        os.makedirs(output_subdir)
                    
                    output_path = os.path.join(output_subdir, os.path.basename(image_file))
                    futures.append(executor.submit(process_single_image, image_file, pipeline, output_path))
                
                # 等待完成
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"处理失败: {str(e)}")
        else:
            # 顺序处理
            process_directory(args.input, pipeline, args.output, args.recursive)
    else:
        print(f"输入路径不存在: {args.input}")

def visualize_pipeline_from_args(args):
    """
    根据命令行参数可视化流水线
    """
    # 加载流水线
    pipeline = load_pipeline_from_file(args.config)
    if not pipeline:
        print("加载流水线失败")
        return
    
    # 可视化
    if pipeline.visualize_pipeline(args.output, args.show):
        print(f"流水线可视化已保存到: {args.output}")

def export_report_from_args(args):
    """
    根据命令行参数导出执行报告
    """
    # 加载流水线
    pipeline = load_pipeline_from_file(args.config)
    if not pipeline:
        print("加载流水线失败")
        return
    
    # 导出报告
    if pipeline.export_execution_report(args.output, args.format):
        print(f"执行报告已导出到: {args.output}")

def main():
    """
    主函数
    """
    args = parse_arguments()
    
    if args.command == 'create':
        create_pipeline_from_args(args)
    elif args.command == 'execute':
        execute_pipeline_from_args(args)
    elif args.command == 'visualize':
        visualize_pipeline_from_args(args)
    elif args.command == 'report':
        export_report_from_args(args)
    else:
        print("请指定命令")
        sys.exit(1)

if __name__ == "__main__":
    main()
