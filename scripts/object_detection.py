#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目标检测模块（A4）

功能：
- 支持多种目标检测算法（Haar级联、HOG+SVM、SSD、YOLO等）
- 支持自定义模型加载
- 支持目标类别筛选
- 支持置信度阈值调整
- 支持非极大值抑制
- 支持边界框绘制和标签标注
- 支持检测结果导出（JSON/CSV/XML）
- 支持批量处理图像
- 支持视频实时检测

作者: AI助手
日期: 2024
"""

import os
import sys
import cv2
import numpy as np
import argparse
import logging
import time
import json
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("object_detection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ObjectDetectionTool:
    """目标检测工具类"""
    
    def __init__(self):
        self.supported_algorithms = [
            'haar_cascade',    # Haar级联分类器
            'hog_svm',         # HOG+SVM
            'ssd',             # SSD (Single Shot MultiBox Detector)
            'yolo_v3',         # YOLOv3
            'yolo_v4',         # YOLOv4
            'yolo_v5',         # YOLOv5
            'yolo_v8',         # YOLOv8
            'faster_rcnn'      # Faster R-CNN
        ]
        
        # 预定义的类别
        self.coco_classes = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
            'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator',
            'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        
        # 常见对象类别
        self.common_classes = {
            'person': self.coco_classes[0],
            'car': self.coco_classes[2],
            'dog': self.coco_classes[16],
            'cat': self.coco_classes[15]
        }
        
        # 生成颜色映射
        self.colormap = self._generate_colormap()
        
        # 初始化检测器
        self.detectors = {}
    
    def _generate_colormap(self, num_colors=80):
        """生成用于绘制边界框的颜色映射"""
        colormap = np.zeros((num_colors, 3), dtype=np.uint8)
        for i in range(num_colors):
            # 使用HSV颜色空间生成均匀分布的颜色
            hue = i / num_colors
            colormap[i] = np.array(plt.cm.hsv(hue)[:3]) * 255
        return colormap
    
    def load_model(self, algorithm, model_path=None, config_path=None, class_names=None, **kwargs):
        """
        加载检测模型
        
        Args:
            algorithm: 算法名称
            model_path: 模型文件路径
            config_path: 配置文件路径
            class_names: 类别名称列表
            **kwargs: 其他参数
            
        Returns:
            bool: 是否成功加载
        """
        if algorithm not in self.supported_algorithms:
            logger.error(f"不支持的检测算法: {algorithm}")
            return False
        
        try:
            if algorithm == 'haar_cascade':
                # 默认使用OpenCV内置的人脸检测模型
                if model_path is None:
                    model_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.detectors[algorithm] = cv2.CascadeClassifier(model_path)
            
            elif algorithm == 'hog_svm':
                # 使用OpenCV内置的HOG+SVM行人检测模型
                self.detectors[algorithm] = cv2.HOGDescriptor()
                self.detectors[algorithm].setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            elif algorithm in ['ssd']:
                # 加载SSD模型
                if model_path is None:
                    model_path = cv2.data.haarcascades + 'MobileNetSSD_deploy.caffemodel'
                    config_path = cv2.data.haarcascades + 'MobileNetSSD_deploy.prototxt.txt'
                
                self.detectors[algorithm] = cv2.dnn.readNetFromCaffe(config_path, model_path)
            
            elif algorithm in ['yolo_v3', 'yolo_v4']:
                # 加载YOLO模型
                if model_path is None or config_path is None:
                    logger.error(f"YOLO模型需要指定model_path和config_path")
                    return False
                
                self.detectors[algorithm] = cv2.dnn.readNetFromDarknet(config_path, model_path)
                # 设置计算后端
                self.detectors[algorithm].setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
                self.detectors[algorithm].setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            elif algorithm in ['yolo_v5', 'yolo_v8', 'faster_rcnn']:
                # 这些模型可能需要其他框架（如PyTorch）支持
                # 这里提供基本框架，实际使用时可能需要安装额外依赖
                logger.warning(f"{algorithm}需要额外依赖，当前仅提供基础接口")
                # 可以根据需要在这里添加PyTorch等框架的支持
            
            # 设置类别名称
            if class_names:
                self.class_names = class_names
            elif algorithm in ['yolo_v3', 'yolo_v4', 'yolo_v5', 'yolo_v8', 'ssd', 'faster_rcnn']:
                self.class_names = self.coco_classes
            else:
                # 对于Haar和HOG+SVM，默认为人或人脸
                self.class_names = ['person'] if algorithm == 'hog_svm' else ['face']
            
            logger.info(f"成功加载{algorithm}模型")
            return True
            
        except Exception as e:
            logger.error(f"加载{algorithm}模型失败: {str(e)}")
            return False
    
    def detect_objects(self, image_path, algorithm='haar_cascade', confidence_threshold=0.5,
                      nms_threshold=0.4, classes=None, **kwargs):
        """
        检测图像中的对象
        
        Args:
            image_path: 图像路径
            algorithm: 检测算法
            confidence_threshold: 置信度阈值
            nms_threshold: 非极大值抑制阈值
            classes: 要检测的类别列表
            **kwargs: 其他参数
            
        Returns:
            tuple: (原始图像, 检测结果, 绘制了边界框的图像)
        """
        if not os.path.isfile(image_path):
            logger.error(f"图像文件不存在: {image_path}")
            return None, None, None
        
        if algorithm not in self.supported_algorithms:
            logger.error(f"不支持的检测算法: {algorithm}")
            return None, None, None
        
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"无法读取图像: {image_path}")
                return None, None, None
            
            # 复制原始图像用于绘制
            image_copy = image.copy()
            
            # 确保模型已加载
            if algorithm not in self.detectors:
                self.load_model(algorithm)
            
            if algorithm not in self.detectors:
                logger.error(f"模型未加载: {algorithm}")
                return None, None, None
            
            # 根据算法调用不同的检测函数
            if algorithm == 'haar_cascade':
                results = self._detect_haar_cascade(image, confidence_threshold, **kwargs)
            elif algorithm == 'hog_svm':
                results = self._detect_hog_svm(image, confidence_threshold, **kwargs)
            elif algorithm == 'ssd':
                results = self._detect_ssd(image, confidence_threshold, nms_threshold, **kwargs)
            elif algorithm in ['yolo_v3', 'yolo_v4']:
                results = self._detect_yolo(image, algorithm, confidence_threshold, nms_threshold, **kwargs)
            else:
                logger.warning(f"{algorithm}的检测功能尚未完全实现")
                results = []
            
            # 类别过滤
            if classes:
                results = [r for r in results if self.class_names[r['class_id']] in classes]
            
            # 绘制边界框
            image_with_boxes = self._draw_boxes(image_copy, results)
            
            return image, results, image_with_boxes
            
        except Exception as e:
            logger.error(f"对象检测失败 {image_path}: {str(e)}")
            return None, None, None
    
    def batch_detect_objects(self, input_dir, output_dir, algorithm='haar_cascade', 
                            confidence_threshold=0.5, nms_threshold=0.4, recursive=True,
                            num_workers=4, file_patterns=None, classes=None, **kwargs):
        """
        批量检测图像中的对象
        
        Args:
            input_dir: 输入图像目录
            output_dir: 输出结果目录
            algorithm: 检测算法
            confidence_threshold: 置信度阈值
            nms_threshold: 非极大值抑制阈值
            recursive: 是否递归处理子目录
            num_workers: 并行工作线程数
            file_patterns: 要处理的文件模式列表
            classes: 要检测的类别列表
            **kwargs: 其他参数
            
        Returns:
            dict: {图像路径: 处理结果}
        """
        if not os.path.isdir(input_dir):
            logger.error(f"输入目录不存在: {input_dir}")
            return {}
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'annotations'), exist_ok=True)
        
        # 收集要处理的图像文件
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        image_files = []
        
        for root, _, files in os.walk(input_dir):
            for file in files:
                file_ext = Path(file).suffix.lower()
                # 检查文件扩展名
                if file_ext in image_extensions:
                    # 如果指定了文件模式，检查是否匹配
                    if file_patterns:
                        if any(pattern in file for pattern in file_patterns):
                            image_files.append(os.path.join(root, file))
                    else:
                        image_files.append(os.path.join(root, file))
            
            # 是否递归处理子目录
            if not recursive:
                break
        
        total_files = len(image_files)
        logger.info(f"找到 {total_files} 个图像文件需要处理")
        
        # 初始化模型
        self.load_model(algorithm, **kwargs)
        
        # 使用线程池并行处理图像
        results = {}
        processed_files = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # 提交所有任务
            future_to_file = {executor.submit(
                self.detect_objects, 
                image_path, 
                algorithm, 
                confidence_threshold, 
                nms_threshold, 
                classes, 
                **kwargs
            ): image_path for image_path in image_files}
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                image_path = future_to_file[future]
                try:
                    image, detections, image_with_boxes = future.result()
                    if image is not None:
                        # 生成输出文件路径
                        rel_path = os.path.relpath(image_path, input_dir)
                        output_base = os.path.join(output_dir, 'images', os.path.splitext(rel_path)[0])
                        annotation_base = os.path.join(output_dir, 'annotations', os.path.splitext(rel_path)[0])
                        
                        # 确保输出子目录存在
                        os.makedirs(os.path.dirname(output_base), exist_ok=True)
                        os.makedirs(os.path.dirname(annotation_base), exist_ok=True)
                        
                        # 保存结果
                        output_image_path = f"{output_base}_detected.jpg"
                        json_path = f"{annotation_base}_detections.json"
                        
                        cv2.imwrite(output_image_path, image_with_boxes)
                        
                        # 保存检测结果为JSON
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump({
                                'image_path': image_path,
                                'detections': detections,
                                'class_names': self.class_names
                            }, f, ensure_ascii=False, indent=2)
                        
                        results[image_path] = {
                            'output_image_path': output_image_path,
                            'json_path': json_path,
                            'num_detections': len(detections)
                        }
                        
                except Exception as e:
                    logger.error(f"处理图像时出错 {image_path}: {str(e)}")
                
                # 更新进度
                processed_files += 1
                self._show_progress(processed_files, total_files, start_time)
        
        logger.info(f"批量检测完成: 成功 {len(results)}/{total_files}")
        return results
    
    def _detect_haar_cascade(self, image, confidence_threshold=0.5, **kwargs):
        """使用Haar级联分类器检测对象"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 调用检测器
        detector = self.detectors['haar_cascade']
        
        # 获取额外参数
        scale_factor = kwargs.get('scale_factor', 1.1)
        min_neighbors = kwargs.get('min_neighbors', 5)
        min_size = kwargs.get('min_size', (30, 30))
        max_size = kwargs.get('max_size', None)
        
        # 检测对象
        rects = detector.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=min_size,
            maxSize=max_size
        )
        
        # 构建结果列表
        results = []
        for (x, y, w, h) in rects:
            results.append({
                'class_id': 0,  # Haar级联通常用于单类别检测
                'confidence': 1.0,  # Haar不提供置信度，设为1.0
                'box': [x, y, x + w, y + h],  # [x1, y1, x2, y2]
                'width': w,
                'height': h
            })
        
        return results
    
    def _detect_hog_svm(self, image, confidence_threshold=0.5, **kwargs):
        """使用HOG+SVM检测行人"""
        detector = self.detectors['hog_svm']
        
        # 获取额外参数
        win_stride = kwargs.get('win_stride', (8, 8))
        padding = kwargs.get('padding', (16, 16))
        scale = kwargs.get('scale', 1.05)
        
        # 检测对象
        rects, weights = detector.detectMultiScale(
            image,
            winStride=win_stride,
            padding=padding,
            scale=scale
        )
        
        # 构建结果列表
        results = []
        for i, (x, y, w, h) in enumerate(rects):
            confidence = float(weights[i]) if len(weights) > i else 0.9
            
            if confidence >= confidence_threshold:
                results.append({
                    'class_id': 0,  # HOG+SVM通常用于行人检测
                    'confidence': confidence,
                    'box': [x, y, x + w, y + h],
                    'width': w,
                    'height': h
                })
        
        return results
    
    def _detect_ssd(self, image, confidence_threshold=0.5, nms_threshold=0.4, **kwargs):
        """使用SSD检测对象"""
        net = self.detectors['ssd']
        
        # 获取图像尺寸
        (h, w) = image.shape[:2]
        
        # 创建blob
        blob = cv2.dnn.blobFromImage(
            cv2.resize(image, (300, 300)),
            0.007843,  # 缩放因子
            (300, 300),  # 输出尺寸
            127.5       # 均值减法
        )
        
        # 设置输入并前向传播
        net.setInput(blob)
        detections = net.forward()
        
        # 构建结果列表
        results = []
        boxes = []
        confidences = []
        class_ids = []
        
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > confidence_threshold:
                class_id = int(detections[0, 0, i, 1])
                
                # 计算边界框坐标
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x1, y1, x2, y2) = box.astype("int")
                
                boxes.append([x1, y1, x2, y2])
                confidences.append(float(confidence))
                class_ids.append(class_id)
        
        # 应用非极大值抑制
        indices = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold)
        
        # 处理NMS结果
        if len(indices) > 0:
            for i in indices.flatten():
                x1, y1, x2, y2 = boxes[i]
                w = x2 - x1
                h = y2 - y1
                
                results.append({
                    'class_id': class_ids[i],
                    'confidence': confidences[i],
                    'box': [x1, y1, x2, y2],
                    'width': w,
                    'height': h
                })
        
        return results
    
    def _detect_yolo(self, image, algorithm, confidence_threshold=0.5, nms_threshold=0.4, **kwargs):
        """使用YOLO检测对象"""
        net = self.detectors[algorithm]
        
        # 获取图像尺寸
        (h, w) = image.shape[:2]
        
        # 获取输出层名称
        ln = net.getLayerNames()
        if isinstance(ln, list):
            ln = [ln[i - 1] for i in net.getUnconnectedOutLayers()]
        else:
            ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]
        
        # 创建blob
        blob = cv2.dnn.blobFromImage(
            image,
            1 / 255.0,  # 缩放因子
            (416, 416),  # 输出尺寸
            swapRB=True,  # 交换RB通道
            crop=False    # 不裁剪
        )
        
        # 设置输入并前向传播
        net.setInput(blob)
        start = time.time()
        layer_outputs = net.forward(ln)
        end = time.time()
        
        logger.debug(f"YOLO前向传播时间: {end - start:.6f}秒")
        
        # 构建结果列表
        results = []
        boxes = []
        confidences = []
        class_ids = []
        
        # 处理每个输出层
        for output in layer_outputs:
            for detection in output:
                # 获取类别概率
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > confidence_threshold:
                    # 计算边界框坐标
                    box = detection[0:4] * np.array([w, h, w, h])
                    (center_x, center_y, width, height) = box.astype("int")
                    
                    # 计算边界框的左上角坐标
                    x1 = int(center_x - (width / 2))
                    y1 = int(center_y - (height / 2))
                    x2 = x1 + width
                    y2 = y1 + height
                    
                    boxes.append([x1, y1, x2, y2])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # 应用非极大值抑制
        indices = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold)
        
        # 处理NMS结果
        if len(indices) > 0:
            for i in indices.flatten():
                x1, y1, x2, y2 = boxes[i]
                width = x2 - x1
                height = y2 - y1
                
                results.append({
                    'class_id': class_ids[i],
                    'confidence': confidences[i],
                    'box': [x1, y1, x2, y2],
                    'width': width,
                    'height': height
                })
        
        return results
    
    def _draw_boxes(self, image, results):
        """在图像上绘制边界框和标签"""
        for result in results:
            class_id = result['class_id']
            confidence = result['confidence']
            x1, y1, x2, y2 = result['box']
            
            # 获取颜色
            color = self.colormap[class_id % len(self.colormap)].tolist()
            
            # 绘制边界框
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # 获取类别名称
            class_name = self.class_names[class_id] if 0 <= class_id < len(self.class_names) else f'Class {class_id}'
            
            # 绘制标签
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(image, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return image
    
    def export_detections(self, detections, image_path, output_dir, format='json', image_info=None):
        """
        导出检测结果
        
        Args:
            detections: 检测结果列表
            image_path: 图像路径
            output_dir: 输出目录
            format: 导出格式 ('json', 'csv', 'xml')
            image_info: 图像信息字典
            
        Returns:
            str: 导出文件路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        if format == 'json':
            output_path = os.path.join(output_dir, f"{base_name}_detections.json")
            
            # 准备JSON数据
            data = {
                'image_path': image_path,
                'detections': detections,
                'class_names': self.class_names
            }
            
            if image_info:
                data['image_info'] = image_info
            
            # 保存JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        elif format == 'csv':
            output_path = os.path.join(output_dir, f"{base_name}_detections.csv")
            
            # 保存CSV文件
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(['class_id', 'class_name', 'confidence', 'x1', 'y1', 'x2', 'y2', 'width', 'height'])
                
                # 写入数据
                for detection in detections:
                    class_id = detection['class_id']
                    class_name = self.class_names[class_id] if 0 <= class_id < len(self.class_names) else f'Class {class_id}'
                    x1, y1, x2, y2 = detection['box']
                    writer.writerow([
                        class_id,
                        class_name,
                        detection['confidence'],
                        x1, y1, x2, y2,
                        detection['width'],
                        detection['height']
                    ])
        
        elif format == 'xml':
            output_path = os.path.join(output_dir, f"{base_name}_detections.xml")
            
            # 构建XML内容
            import xml.etree.ElementTree as ET
            root = ET.Element('annotations')
            
            # 添加图像信息
            ET.SubElement(root, 'image_path').text = image_path
            if image_info:
                for key, value in image_info.items():
                    ET.SubElement(root, key).text = str(value)
            
            # 添加检测结果
            for i, detection in enumerate(detections):
                obj = ET.SubElement(root, 'object', id=str(i))
                class_id = detection['class_id']
                class_name = self.class_names[class_id] if 0 <= class_id < len(self.class_names) else f'Class {class_id}'
                
                ET.SubElement(obj, 'class_id').text = str(class_id)
                ET.SubElement(obj, 'class_name').text = class_name
                ET.SubElement(obj, 'confidence').text = str(detection['confidence'])
                
                bbox = ET.SubElement(obj, 'bndbox')
                x1, y1, x2, y2 = detection['box']
                ET.SubElement(bbox, 'xmin').text = str(x1)
                ET.SubElement(bbox, 'ymin').text = str(y1)
                ET.SubElement(bbox, 'xmax').text = str(x2)
                ET.SubElement(bbox, 'ymax').text = str(y2)
            
            # 保存XML文件
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        else:
            logger.error(f"不支持的导出格式: {format}")
            return None
        
        logger.info(f"检测结果已导出到: {output_path}")
        return output_path
    
    def analyze_detections(self, detections):
        """
        分析检测结果
        
        Args:
            detections: 检测结果列表
            
        Returns:
            dict: 分析结果
        """
        if not detections:
            return {'total_objects': 0, 'class_distribution': {}}
        
        # 统计各类别数量
        class_counts = {}
        for detection in detections:
            class_id = detection['class_id']
            class_name = self.class_names[class_id] if 0 <= class_id < len(self.class_names) else f'Class {class_id}'
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        # 计算平均置信度
        avg_confidence = sum(d['confidence'] for d in detections) / len(detections)
        
        # 找出最大和最小的对象
        if detections:
            max_size = max(d['width'] * d['height'] for d in detections)
            min_size = min(d['width'] * d['height'] for d in detections)
        else:
            max_size = 0
            min_size = 0
        
        analysis = {
            'total_objects': len(detections),
            'class_distribution': class_counts,
            'average_confidence': avg_confidence,
            'max_object_area': max_size,
            'min_object_area': min_size
        }
        
        return analysis
    
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
    
    def detect_video(self, video_path, output_path, algorithm='haar_cascade', 
                    confidence_threshold=0.5, nms_threshold=0.4, classes=None, 
                    fps=None, codec='mp4v', **kwargs):
        """
        检测视频中的对象
        
        Args:
            video_path: 视频路径或摄像头ID
            output_path: 输出视频路径
            algorithm: 检测算法
            confidence_threshold: 置信度阈值
            nms_threshold: 非极大值抑制阈值
            classes: 要检测的类别列表
            fps: 输出视频帧率
            codec: 视频编码器
            **kwargs: 其他参数
            
        Returns:
            bool: 是否成功处理
        """
        try:
            # 打开视频
            is_camera = isinstance(video_path, int) or video_path.isdigit()
            if is_camera:
                cap = cv2.VideoCapture(int(video_path))
            else:
                if not os.path.isfile(video_path):
                    logger.error(f"视频文件不存在: {video_path}")
                    return False
                cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                logger.error(f"无法打开视频: {video_path}")
                return False
            
            # 获取视频信息
            original_fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 设置输出视频参数
            out_fps = fps if fps else original_fps
            fourcc = cv2.VideoWriter_fourcc(*codec)
            out = cv2.VideoWriter(output_path, fourcc, out_fps, (width, height))
            
            # 初始化模型
            self.load_model(algorithm, **kwargs)
            
            # 处理视频帧
            frame_count = 0
            start_time = time.time()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # 检测对象
                _, detections, frame_with_boxes = self.detect_objects(
                    None, algorithm, confidence_threshold, nms_threshold, classes, 
                    frame=frame, **kwargs
                )
                
                if frame_with_boxes is not None:
                    # 写入输出视频
                    out.write(frame_with_boxes)
                    
                    # 显示进度
                    if frame_count % 10 == 0:
                        elapsed_time = time.time() - start_time
                        fps = frame_count / elapsed_time
                        sys.stdout.write(f'\r已处理帧: {frame_count}, 帧率: {fps:.2f}fps')
                        sys.stdout.flush()
            
            # 释放资源
            cap.release()
            out.release()
            
            logger.info(f"视频处理完成，输出保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"视频处理失败: {str(e)}")
            return False


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='目标检测工具')
    
    # 输入输出参数
    parser.add_argument('-i', '--input', type=str, required=True, help='输入图像/视频文件或目录路径')
    parser.add_argument('-o', '--output', type=str, required=True, help='输出目录或文件路径')
    
    # 模式参数
    parser.add_argument('--mode', type=str, default='image', choices=['image', 'video', 'camera'],
                      help='处理模式')
    
    # 检测算法参数
    parser.add_argument('-a', '--algorithm', type=str, default='haar_cascade', 
                      help=f'检测算法 ({" ".join(ObjectDetectionTool().supported_algorithms)})')
    parser.add_argument('--model', type=str, help='模型文件路径')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--class-names', type=str, help='类别名称文件路径')
    
    # 检测参数
    parser.add_argument('--confidence', type=float, default=0.5, help='置信度阈值')
    parser.add_argument('--nms-threshold', type=float, default=0.4, help='非极大值抑制阈值')
    parser.add_argument('--classes', type=str, nargs='+', help='要检测的类别列表')
    
    # 批量处理参数
    parser.add_argument('-r', '--recursive', action='store_true', default=False, 
                      help='递归处理子目录')
    parser.add_argument('-w', '--workers', type=int, default=4, help='并行工作线程数')
    parser.add_argument('--patterns', type=str, nargs='+', help='文件匹配模式')
    
    # Haar级联参数
    parser.add_argument('--scale-factor', type=float, default=1.1, help='Haar级联缩放因子')
    parser.add_argument('--min-neighbors', type=int, default=5, help='Haar级联最小邻居数')
    parser.add_argument('--min-size', type=int, nargs=2, default=(30, 30), help='Haar级联最小对象尺寸')
    parser.add_argument('--max-size', type=int, nargs=2, help='Haar级联最大对象尺寸')
    
    # HOG+SVM参数
    parser.add_argument('--win-stride', type=int, nargs=2, default=(8, 8), help='HOG窗口步长')
    parser.add_argument('--padding', type=int, nargs=2, default=(16, 16), help='HOG填充')
    parser.add_argument('--hog-scale', type=float, default=1.05, help='HOG缩放因子')
    
    # 视频处理参数
    parser.add_argument('--fps', type=float, help='输出视频帧率')
    parser.add_argument('--codec', type=str, default='mp4v', help='视频编码器')
    
    # 导出参数
    parser.add_argument('--export-format', type=str, default='json', choices=['json', 'csv', 'xml'],
                      help='检测结果导出格式')
    parser.add_argument('--analyze', action='store_true', default=False, help='分析检测结果')
    
    return parser.parse_args()


def load_class_names(class_names_path):
    """从文件加载类别名称"""
    if not os.path.isfile(class_names_path):
        logger.error(f"类别名称文件不存在: {class_names_path}")
        return None
    
    try:
        with open(class_names_path, 'r', encoding='utf-8') as f:
            class_names = [line.strip() for line in f if line.strip()]
        return class_names
    except Exception as e:
        logger.error(f"加载类别名称文件失败: {str(e)}")
        return None


def get_algorithm_kwargs(args):
    """根据命令行参数生成算法特定的参数字典"""
    kwargs = {}
    
    # 通用参数
    kwargs['model_path'] = args.model
    kwargs['config_path'] = args.config
    
    # 加载类别名称
    if args.class_names:
        class_names = load_class_names(args.class_names)
        if class_names:
            kwargs['class_names'] = class_names
    
    # Haar级联参数
    if args.algorithm == 'haar_cascade':
        kwargs['scale_factor'] = args.scale_factor
        kwargs['min_neighbors'] = args.min_neighbors
        kwargs['min_size'] = tuple(args.min_size)
        if args.max_size:
            kwargs['max_size'] = tuple(args.max_size)
    
    # HOG+SVM参数
    elif args.algorithm == 'hog_svm':
        kwargs['win_stride'] = tuple(args.win_stride)
        kwargs['padding'] = tuple(args.padding)
        kwargs['scale'] = args.hog_scale
    
    return kwargs


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 初始化检测工具
    tool = ObjectDetectionTool()
    
    # 获取算法特定参数
    algorithm_kwargs = get_algorithm_kwargs(args)
    
    try:
        # 确保输出目录存在
        if args.mode in ['image', 'video']:
            if os.path.isdir(args.output):
                os.makedirs(args.output, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
        # 根据模式选择处理方式
        if args.mode == 'image':
            # 处理单文件或目录
            if os.path.isfile(args.input):
                # 处理单个图像
                image, detections, image_with_boxes = tool.detect_objects(
                    args.input, 
                    args.algorithm, 
                    args.confidence,
                    args.nms_threshold,
                    args.classes,
                    **algorithm_kwargs
                )
                
                if image is not None:
                    # 生成输出文件路径
                    if os.path.isdir(args.output):
                        base_name = os.path.splitext(os.path.basename(args.input))[0]
                        output_image_path = os.path.join(args.output, f"{base_name}_detected.jpg")
                    else:
                        output_image_path = args.output
                    
                    # 保存结果图像
                    cv2.imwrite(output_image_path, image_with_boxes)
                    
                    # 导出检测结果
                    output_dir = os.path.dirname(output_image_path)
                    tool.export_detections(
                        detections, 
                        args.input, 
                        output_dir, 
                        args.export_format,
                        {'width': image.shape[1], 'height': image.shape[0]}
                    )
                    
                    # 分析检测结果
                    if args.analyze:
                        analysis = tool.analyze_detections(detections)
                        logger.info(f"检测分析结果: {analysis}")
                    
                    logger.info(f"图像检测完成，结果保存到: {output_image_path}")
                    return 0
                else:
                    return 1
            
            elif os.path.isdir(args.input):
                # 批量处理图像
                results = tool.batch_detect_objects(
                    args.input,
                    args.output,
                    args.algorithm,
                    args.confidence,
                    args.nms_threshold,
                    args.recursive,
                    args.workers,
                    args.patterns,
                    args.classes,
                    **algorithm_kwargs
                )
                
                logger.info(f"批量检测完成: 成功处理 {len(results)} 个图像")
                return 0 if results else 1
            
            else:
                logger.error(f"输入路径不存在: {args.input}")
                return 1
        
        elif args.mode == 'video':
            # 处理视频
            success = tool.detect_video(
                args.input,
                args.output,
                args.algorithm,
                args.confidence,
                args.nms_threshold,
                args.classes,
                args.fps,
                args.codec,
                **algorithm_kwargs
            )
            
            return 0 if success else 1
        
        elif args.mode == 'camera':
            # 从摄像头检测
            camera_id = int(args.input) if args.input.isdigit() else 0
            success = tool.detect_video(
                camera_id,
                args.output,
                args.algorithm,
                args.confidence,
                args.nms_threshold,
                args.classes,
                args.fps,
                args.codec,
                **algorithm_kwargs
            )
            
            return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        return 1
    except Exception as e:
        logger.error(f"发生未预期的错误: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
