#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像标注工具模块（A9）

功能：
- 支持多种标注类型：矩形框、多边形、线条、点标注
- 支持保存为多种格式：YOLO、COCO、Pascal VOC、JSON
- 支持读取和编辑现有标注
- 支持快捷键操作
- 支持类别管理
- 支持图像缩放、平移、旋转等操作
- 支持批量处理模式
- 支持标注统计和可视化
- 支持自动保存和撤销/重做功能

支持单文件和批量文件夹处理
"""

import os
import json
import argparse
import cv2
import numpy as np
import time
from datetime import datetime
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from tqdm import tqdm
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, Arrow
from matplotlib.widgets import Button, TextBox, CheckButtons
import matplotlib

# 设置matplotlib后端，避免显示问题
matplotlib.use('TkAgg')

def ensure_directory(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)

class AnnotationFormatConverter:
    """标注格式转换器"""
    
    @staticmethod
    def to_yolo(annotations, image_width, image_height, class_names, output_path):
        """转换为YOLO格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for ann in annotations:
                if ann['type'] == 'rect':
                    # YOLO格式：class_id center_x center_y width height (归一化)
                    class_id = class_names.index(ann['class_name'])
                    x_min, y_min, x_max, y_max = ann['coordinates']
                    
                    # 计算中心点和宽高
                    center_x = (x_min + x_max) / 2 / image_width
                    center_y = (y_min + y_max) / 2 / image_height
                    width = (x_max - x_min) / image_width
                    height = (y_max - y_min) / image_height
                    
                    f.write(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}\n")
                elif ann['type'] == 'polygon':
                    # YOLO格式多边形：class_id x1 y1 x2 y2 ... (归一化)
                    class_id = class_names.index(ann['class_name'])
                    coords = ann['coordinates']
                    normalized_coords = []
                    for x, y in coords:
                        normalized_coords.extend([x/image_width, y/image_height])
                    
                    f.write(f"{class_id} {' '.join([f'{coord:.6f}' for coord in normalized_coords])}\n")
    
    @staticmethod
    def from_yolo(file_path, image_width, image_height, class_names):
        """从YOLO格式转换为内部格式"""
        annotations = []
        
        if not os.path.exists(file_path):
            return annotations
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = list(map(float, line.strip().split()))
                if not parts:
                    continue
                
                class_id = int(parts[0])
                class_name = class_names[class_id] if class_id < len(class_names) else f"class_{class_id}"
                
                if len(parts) == 5:
                    # 矩形框
                    center_x, center_y, width, height = parts[1:5]
                    
                    # 转换为x_min, y_min, x_max, y_max
                    x_min = (center_x - width/2) * image_width
                    y_min = (center_y - height/2) * image_height
                    x_max = (center_x + width/2) * image_width
                    y_max = (center_y + height/2) * image_height
                    
                    annotations.append({
                        'type': 'rect',
                        'class_name': class_name,
                        'coordinates': [x_min, y_min, x_max, y_max]
                    })
                elif len(parts) > 5 and len(parts) % 2 == 1:
                    # 多边形
                    coords = []
                    for i in range(1, len(parts), 2):
                        x = parts[i] * image_width
                        y = parts[i+1] * image_height
                        coords.append([x, y])
                    
                    annotations.append({
                        'type': 'polygon',
                        'class_name': class_name,
                        'coordinates': coords
                    })
        
        return annotations
    
    @staticmethod
    def to_coco(annotations, image_id, image_width, image_height, category_map, output_dict):
        """转换为COCO格式"""
        annotation_id = output_dict.get('annotations', [])[-1]['id'] + 1 if output_dict.get('annotations') else 1
        
        for ann in annotations:
            category_id = category_map.get(ann['class_name'], 1)
            
            if ann['type'] == 'rect':
                x_min, y_min, x_max, y_max = ann['coordinates']
                width = x_max - x_min
                height = y_max - y_min
                
                annotation = {
                    'id': annotation_id,
                    'image_id': image_id,
                    'category_id': category_id,
                    'bbox': [x_min, y_min, width, height],
                    'area': width * height,
                    'segmentation': [],
                    'iscrowd': 0
                }
                output_dict['annotations'].append(annotation)
            
            elif ann['type'] == 'polygon':
                # 转换多边形为COCO格式的segmentation
                segmentation = [coord for point in ann['coordinates'] for coord in point]
                
                # 计算边界框和面积
                x_coords = [p[0] for p in ann['coordinates']]
                y_coords = [p[1] for p in ann['coordinates']]
                x_min, y_min = min(x_coords), min(y_coords)
                width, height = max(x_coords) - x_min, max(y_coords) - y_min
                
                annotation = {
                    'id': annotation_id,
                    'image_id': image_id,
                    'category_id': category_id,
                    'bbox': [x_min, y_min, width, height],
                    'area': width * height,  # 简化计算，实际应该用多边形面积公式
                    'segmentation': [segmentation],
                    'iscrowd': 0
                }
                output_dict['annotations'].append(annotation)
            
            annotation_id += 1
    
    @staticmethod
    def to_pascal_voc(annotations, image_path, image_width, image_height, output_path):
        """转换为Pascal VOC格式"""
        root = ET.Element('annotation')
        
        # 添加图像信息
        folder = ET.SubElement(root, 'folder')
        folder.text = os.path.basename(os.path.dirname(image_path))
        
        filename = ET.SubElement(root, 'filename')
        filename.text = os.path.basename(image_path)
        
        path = ET.SubElement(root, 'path')
        path.text = os.path.abspath(image_path)
        
        # 源信息
        source = ET.SubElement(root, 'source')
        database = ET.SubElement(source, 'database')
        database.text = 'Unknown'
        
        # 大小信息
        size = ET.SubElement(root, 'size')
        width_elem = ET.SubElement(size, 'width')
        width_elem.text = str(image_width)
        height_elem = ET.SubElement(size, 'height')
        height_elem.text = str(image_height)
        depth_elem = ET.SubElement(size, 'depth')
        depth_elem.text = '3'
        
        segmented = ET.SubElement(root, 'segmented')
        segmented.text = '0'
        
        # 添加标注对象
        for ann in annotations:
            obj = ET.SubElement(root, 'object')
            
            name = ET.SubElement(obj, 'name')
            name.text = ann['class_name']
            
            pose = ET.SubElement(obj, 'pose')
            pose.text = 'Unspecified'
            
            truncated = ET.SubElement(obj, 'truncated')
            truncated.text = '0'
            
            difficult = ET.SubElement(obj, 'difficult')
            difficult.text = '0'
            
            bndbox = ET.SubElement(obj, 'bndbox')
            
            if ann['type'] == 'rect':
                x_min, y_min, x_max, y_max = ann['coordinates']
                
                xmin = ET.SubElement(bndbox, 'xmin')
                xmin.text = str(int(round(x_min)))
                ymin = ET.SubElement(bndbox, 'ymin')
                ymin.text = str(int(round(y_min)))
                xmax = ET.SubElement(bndbox, 'xmax')
                xmax.text = str(int(round(x_max)))
                ymax = ET.SubElement(bndbox, 'ymax')
                ymax.text = str(int(round(y_max)))
            
            elif ann['type'] == 'polygon':
                # 对于多边形，取边界框
                x_coords = [p[0] for p in ann['coordinates']]
                y_coords = [p[1] for p in ann['coordinates']]
                x_min, y_min = min(x_coords), min(y_coords)
                x_max, y_max = max(x_coords), max(y_coords)
                
                xmin = ET.SubElement(bndbox, 'xmin')
                xmin.text = str(int(round(x_min)))
                ymin = ET.SubElement(bndbox, 'ymin')
                ymin.text = str(int(round(y_min)))
                xmax = ET.SubElement(bndbox, 'xmax')
                xmax.text = str(int(round(x_max)))
                ymax = ET.SubElement(bndbox, 'ymax')
                ymax.text = str(int(round(y_max)))
        
        # 写入XML文件
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    @staticmethod
    def save_as_json(annotations, image_path, image_width, image_height, output_path):
        """保存为JSON格式"""
        data = {
            'image_path': image_path,
            'image_width': image_width,
            'image_height': image_height,
            'annotations': annotations,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_from_json(file_path):
        """从JSON格式加载"""
        if not os.path.exists(file_path):
            return [], 0, 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        annotations = data.get('annotations', [])
        image_width = data.get('image_width', 0)
        image_height = data.get('image_height', 0)
        
        return annotations, image_width, image_height

class AnnotationEditor:
    """图像标注编辑器"""
    
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.current_image = None
        self.current_image_path = None
        self.annotations = []
        self.class_names = ['person', 'car', 'bicycle', 'motorcycle', 'bus', 'truck']
        self.current_class_idx = 0
        self.current_tool = 'rect'  # rect, polygon, line, point
        self.is_drawing = False
        self.start_point = None
        self.current_polygon_points = []
        self.temp_patch = None
        self.selected_annotation_idx = -1
        self.zoom_factor = 1.0
        self.pan_offset = (0, 0)
        self.history = []  # 用于撤销/重做
        self.history_index = -1
        self.auto_save_interval = 30  # 自动保存间隔（秒）
        self.last_save_time = time.time()
        
        # 初始化界面
        self._init_ui()
        
        # 连接事件处理
        self.fig.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.fig.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key_press)
    
    def _init_ui(self):
        """初始化用户界面"""
        # 设置工具栏按钮
        self.fig.subplots_adjust(bottom=0.2)
        
        # 工具选择按钮
        tools = ['rect', 'polygon', 'line', 'point']
        for i, tool in enumerate(tools):
            ax_button = plt.axes([0.1 + i*0.1, 0.05, 0.08, 0.05])
            button = Button(ax_button, tool)
            button.on_clicked(lambda event, t=tool: self._select_tool(t))
        
        # 类别选择文本框
        ax_class = plt.axes([0.1, 0.12, 0.15, 0.05])
        self.class_textbox = TextBox(ax_class, 'Class: ')
        self.class_textbox.on_submit(self._change_class)
        self.class_textbox.set_val(self.class_names[self.current_class_idx])
        
        # 下一个/上一个类别按钮
        ax_next_class = plt.axes([0.26, 0.12, 0.08, 0.05])
        self.next_class_button = Button(ax_next_class, 'Next Class')
        self.next_class_button.on_clicked(self._next_class)
        
        ax_prev_class = plt.axes([0.35, 0.12, 0.08, 0.05])
        self.prev_class_button = Button(ax_prev_class, 'Prev Class')
        self.prev_class_button.on_clicked(self._prev_class)
        
        # 删除选中标注按钮
        ax_delete = plt.axes([0.44, 0.12, 0.1, 0.05])
        self.delete_button = Button(ax_delete, 'Delete')
        self.delete_button.on_clicked(self._delete_annotation)
        
        # 撤销/重做按钮
        ax_undo = plt.axes([0.55, 0.12, 0.08, 0.05])
        self.undo_button = Button(ax_undo, 'Undo')
        self.undo_button.on_clicked(self._undo)
        
        ax_redo = plt.axes([0.64, 0.12, 0.08, 0.05])
        self.redo_button = Button(ax_redo, 'Redo')
        self.redo_button.on_clicked(self._redo)
        
        # 缩放按钮
        ax_zoom_in = plt.axes([0.73, 0.12, 0.08, 0.05])
        self.zoom_in_button = Button(ax_zoom_in, 'Zoom In')
        self.zoom_in_button.on_clicked(self._zoom_in)
        
        ax_zoom_out = plt.axes([0.82, 0.12, 0.08, 0.05])
        self.zoom_out_button = Button(ax_zoom_out, 'Zoom Out')
        self.zoom_out_button.on_clicked(self._zoom_out)
        
        ax_reset_view = plt.axes([0.73, 0.05, 0.17, 0.05])
        self.reset_view_button = Button(ax_reset_view, 'Reset View')
        self.reset_view_button.on_clicked(self._reset_view)
    
    def _select_tool(self, tool):
        """选择标注工具"""
        self.current_tool = tool
        print(f"Selected tool: {tool}")
    
    def _change_class(self, text):
        """改变当前类别"""
        if text not in self.class_names:
            self.class_names.append(text)
        self.current_class_idx = self.class_names.index(text)
        print(f"Current class: {self.class_names[self.current_class_idx]}")
    
    def _next_class(self, event):
        """选择下一个类别"""
        self.current_class_idx = (self.current_class_idx + 1) % len(self.class_names)
        self.class_textbox.set_val(self.class_names[self.current_class_idx])
        print(f"Current class: {self.class_names[self.current_class_idx]}")
    
    def _prev_class(self, event):
        """选择上一个类别"""
        self.current_class_idx = (self.current_class_idx - 1) % len(self.class_names)
        self.class_textbox.set_val(self.class_names[self.current_class_idx])
        print(f"Current class: {self.class_names[self.current_class_idx]}")
    
    def _delete_annotation(self, event):
        """删除选中的标注"""
        if self.selected_annotation_idx >= 0 and self.selected_annotation_idx < len(self.annotations):
            self._save_state()
            del self.annotations[self.selected_annotation_idx]
            self.selected_annotation_idx = -1
            self._redraw_image()
    
    def _undo(self, event):
        """撤销操作"""
        if self.history_index > 0:
            self.history_index -= 1
            self.annotations = self.history[self.history_index].copy()
            self.selected_annotation_idx = -1
            self._redraw_image()
    
    def _redo(self, event):
        """重做操作"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.annotations = self.history[self.history_index].copy()
            self.selected_annotation_idx = -1
            self._redraw_image()
    
    def _zoom_in(self, event):
        """放大图像"""
        self.zoom_factor *= 1.2
        self._redraw_image()
    
    def _zoom_out(self, event):
        """缩小图像"""
        self.zoom_factor /= 1.2
        self._redraw_image()
    
    def _reset_view(self, event):
        """重置视图"""
        self.zoom_factor = 1.0
        self.pan_offset = (0, 0)
        self._redraw_image()
    
    def _save_state(self):
        """保存当前状态用于撤销/重做"""
        # 截断历史记录
        self.history = self.history[:self.history_index + 1]
        # 保存当前状态
        self.history.append([ann.copy() for ann in self.annotations])
        self.history_index = len(self.history) - 1
    
    def _on_mouse_press(self, event):
        """鼠标按下事件"""
        if event.inaxes != self.ax:
            return
        
        # 检查是否点击了标注
        for i, ann in enumerate(self.annotations):
            if self._is_point_in_annotation(event.xdata, event.ydata, ann):
                self.selected_annotation_idx = i
                self._redraw_image()
                return
        
        # 如果没有选中标注，开始新的标注
        self.selected_annotation_idx = -1
        
        # 计算实际图像坐标
        x = (event.xdata - self.pan_offset[0]) / self.zoom_factor
        y = (event.ydata - self.pan_offset[1]) / self.zoom_factor
        
        if self.current_tool == 'rect':
            self.is_drawing = True
            self.start_point = (x, y)
            self._save_state()
        elif self.current_tool == 'polygon':
            if event.button == 1:  # 左键添加点
                self.current_polygon_points.append((x, y))
                if len(self.current_polygon_points) == 1:
                    self._save_state()
                self._redraw_image()
            elif event.button == 3:  # 右键完成多边形
                if len(self.current_polygon_points) >= 3:
                    self.annotations.append({
                        'type': 'polygon',
                        'class_name': self.class_names[self.current_class_idx],
                        'coordinates': self.current_polygon_points.copy()
                    })
                self.current_polygon_points = []
                self._redraw_image()
        elif self.current_tool == 'point':
            self._save_state()
            self.annotations.append({
                'type': 'point',
                'class_name': self.class_names[self.current_class_idx],
                'coordinates': [x, y]
            })
            self._redraw_image()
    
    def _on_mouse_move(self, event):
        """鼠标移动事件"""
        if not self.is_drawing or event.inaxes != self.ax:
            return
        
        # 计算实际图像坐标
        x = (event.xdata - self.pan_offset[0]) / self.zoom_factor
        y = (event.ydata - self.pan_offset[1]) / self.zoom_factor
        
        if self.current_tool == 'rect':
            # 更新临时矩形
            if self.temp_patch:
                self.temp_patch.remove()
            
            x_min = min(self.start_point[0], x)
            y_min = min(self.start_point[1], y)
            width = abs(x - self.start_point[0])
            height = abs(y - self.start_point[1])
            
            self.temp_patch = Rectangle(
                (x_min * self.zoom_factor + self.pan_offset[0], y_min * self.zoom_factor + self.pan_offset[1]),
                width * self.zoom_factor, height * self.zoom_factor,
                edgecolor='red', facecolor='none', linewidth=2
            )
            self.ax.add_patch(self.temp_patch)
            self.fig.canvas.draw_idle()
    
    def _on_mouse_release(self, event):
        """鼠标释放事件"""
        if not self.is_drawing or event.inaxes != self.ax:
            return
        
        self.is_drawing = False
        
        # 计算实际图像坐标
        x = (event.xdata - self.pan_offset[0]) / self.zoom_factor
        y = (event.ydata - self.pan_offset[1]) / self.zoom_factor
        
        if self.current_tool == 'rect':
            # 移除临时矩形
            if self.temp_patch:
                self.temp_patch.remove()
                self.temp_patch = None
            
            # 添加矩形标注
            x_min = min(self.start_point[0], x)
            y_min = min(self.start_point[1], y)
            x_max = max(self.start_point[0], x)
            y_max = max(self.start_point[1], y)
            
            # 确保标注有一定大小
            if abs(x_max - x_min) > 1 and abs(y_max - y_min) > 1:
                self.annotations.append({
                    'type': 'rect',
                    'class_name': self.class_names[self.current_class_idx],
                    'coordinates': [x_min, y_min, x_max, y_max]
                })
                self._redraw_image()
    
    def _on_key_press(self, event):
        """键盘按键事件"""
        # 保存标注
        if event.key == 's':
            self.save_annotations()
        # 切换工具
        elif event.key == '1':
            self.current_tool = 'rect'
            print("Tool: Rectangle")
        elif event.key == '2':
            self.current_tool = 'polygon'
            print("Tool: Polygon")
        elif event.key == '3':
            self.current_tool = 'line'
            print("Tool: Line")
        elif event.key == '4':
            self.current_tool = 'point'
            print("Tool: Point")
        # 删除标注
        elif event.key == 'delete' or event.key == 'backspace':
            self._delete_annotation(None)
        # 平移图像
        elif event.key == 'up':
            self.pan_offset = (self.pan_offset[0], self.pan_offset[1] + 50)
            self._redraw_image()
        elif event.key == 'down':
            self.pan_offset = (self.pan_offset[0], self.pan_offset[1] - 50)
            self._redraw_image()
        elif event.key == 'left':
            self.pan_offset = (self.pan_offset[0] + 50, self.pan_offset[1])
            self._redraw_image()
        elif event.key == 'right':
            self.pan_offset = (self.pan_offset[0] - 50, self.pan_offset[1])
            self._redraw_image()
    
    def _is_point_in_annotation(self, x, y, annotation):
        """检查点是否在标注内"""
        # 转换为图像坐标
        img_x = (x - self.pan_offset[0]) / self.zoom_factor
        img_y = (y - self.pan_offset[1]) / self.zoom_factor
        
        if annotation['type'] == 'rect':
            x_min, y_min, x_max, y_max = annotation['coordinates']
            return x_min - 5 <= img_x <= x_max + 5 and y_min - 5 <= img_y <= y_max + 5
        elif annotation['type'] == 'polygon':
            # 使用射线法判断点是否在多边形内
            points = annotation['coordinates']
            n = len(points)
            inside = False
            
            p1x, p1y = points[0]
            for i in range(n + 1):
                p2x, p2y = points[i % n]
                if img_y > min(p1y, p2y):
                    if img_y <= max(p1y, p2y):
                        if img_x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (img_y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or img_x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y
            
            return inside
        elif annotation['type'] == 'point':
            px, py = annotation['coordinates']
            # 点的点击区域稍大一些
            return (img_x - px)**2 + (img_y - py)**2 <= 25
        
        return False
    
    def _redraw_image(self):
        """重绘图像和标注"""
        self.ax.clear()
        
        if self.current_image is not None:
            # 应用缩放和平移
            h, w = self.current_image.shape[:2]
            self.ax.imshow(self.current_image)
            self.ax.set_xlim(-self.pan_offset[0], w * self.zoom_factor - self.pan_offset[0])
            self.ax.set_ylim(h * self.zoom_factor - self.pan_offset[1], -self.pan_offset[1])
        
        # 绘制标注
        for i, ann in enumerate(self.annotations):
            # 选中的标注用不同颜色显示
            color = 'blue' if i == self.selected_annotation_idx else 'red'
            
            if ann['type'] == 'rect':
                x_min, y_min, x_max, y_max = ann['coordinates']
                width = x_max - x_min
                height = y_max - y_min
                
                # 应用缩放和平移
                rect = Rectangle(
                    (x_min * self.zoom_factor + self.pan_offset[0], y_min * self.zoom_factor + self.pan_offset[1]),
                    width * self.zoom_factor, height * self.zoom_factor,
                    edgecolor=color, facecolor='none', linewidth=2
                )
                self.ax.add_patch(rect)
                
                # 添加类别标签
                self.ax.text(
                    x_min * self.zoom_factor + self.pan_offset[0],
                    y_min * self.zoom_factor + self.pan_offset[1] - 5,
                    ann['class_name'],
                    color=color, fontsize=8, backgroundcolor='white'
                )
            
            elif ann['type'] == 'polygon':
                # 应用缩放和平移
                transformed_points = []
                for x, y in ann['coordinates']:
                    transformed_points.append((x * self.zoom_factor + self.pan_offset[0], y * self.zoom_factor + self.pan_offset[1]))
                
                polygon = Polygon(
                    transformed_points, edgecolor=color, facecolor='none', linewidth=2
                )
                self.ax.add_patch(polygon)
                
                # 添加类别标签
                self.ax.text(
                    transformed_points[0][0], transformed_points[0][1] - 5,
                    ann['class_name'],
                    color=color, fontsize=8, backgroundcolor='white'
                )
            
            elif ann['type'] == 'point':
                x, y = ann['coordinates']
                
                # 应用缩放和平移
                circle = Circle(
                    (x * self.zoom_factor + self.pan_offset[0], y * self.zoom_factor + self.pan_offset[1]),
                    5, edgecolor=color, facecolor=color, linewidth=1
                )
                self.ax.add_patch(circle)
                
                # 添加类别标签
                self.ax.text(
                    x * self.zoom_factor + self.pan_offset[0] + 10,
                    y * self.zoom_factor + self.pan_offset[1],
                    ann['class_name'],
                    color=color, fontsize=8, backgroundcolor='white'
                )
        
        # 绘制多边形临时点
        if self.current_tool == 'polygon' and self.current_polygon_points:
            # 应用缩放和平移
            transformed_points = []
            for x, y in self.current_polygon_points:
                transformed_points.append((x * self.zoom_factor + self.pan_offset[0], y * self.zoom_factor + self.pan_offset[1]))
            
            # 绘制点
            for point in transformed_points:
                circle = Circle(point, 3, edgecolor='green', facecolor='green')
                self.ax.add_patch(circle)
            
            # 绘制连线
            if len(transformed_points) > 1:
                for i in range(len(transformed_points) - 1):
                    self.ax.plot(
                        [transformed_points[i][0], transformed_points[i+1][0]],
                        [transformed_points[i][1], transformed_points[i+1][1]],
                        'g-', linewidth=2
                    )
        
        self.ax.set_title(f"Tool: {self.current_tool} | Class: {self.class_names[self.current_class_idx]} | Zoom: {self.zoom_factor:.2f}")
        self.fig.canvas.draw_idle()
    
    def load_image(self, image_path):
        """加载图像"""
        self.current_image_path = image_path
        self.current_image = cv2.imread(image_path)
        if self.current_image is None:
            print(f"无法加载图像: {image_path}")
            return False
        
        # 转换BGR为RGB用于matplotlib显示
        self.current_image = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
        
        # 重置状态
        self.annotations = []
        self.selected_annotation_idx = -1
        self.current_polygon_points = []
        self.history = []
        self.history_index = -1
        self.last_save_time = time.time()
        
        # 尝试加载现有标注
        self._load_existing_annotations()
        
        # 重绘图像
        self._redraw_image()
        
        print(f"已加载图像: {image_path}")
        return True
    
    def _load_existing_annotations(self):
        """加载现有的标注文件"""
        if not self.current_image_path:
            return
        
        base_name = os.path.splitext(self.current_image_path)[0]
        possible_formats = ['.json', '.xml', '.txt']
        
        for ext in possible_formats:
            ann_path = base_name + ext
            if os.path.exists(ann_path):
                print(f"正在加载现有标注: {ann_path}")
                
                if ext == '.json':
                    self.annotations, _, _ = AnnotationFormatConverter.load_from_json(ann_path)
                elif ext == '.xml':
                    # 简化的Pascal VOC加载
                    try:
                        tree = ET.parse(ann_path)
                        root = tree.getroot()
                        
                        for obj in root.findall('object'):
                            class_name = obj.find('name').text
                            bndbox = obj.find('bndbox')
                            x_min = float(bndbox.find('xmin').text)
                            y_min = float(bndbox.find('ymin').text)
                            x_max = float(bndbox.find('xmax').text)
                            y_max = float(bndbox.find('ymax').text)
                            
                            self.annotations.append({
                                'type': 'rect',
                                'class_name': class_name,
                                'coordinates': [x_min, y_min, x_max, y_max]
                            })
                            
                            # 添加类别到列表
                            if class_name not in self.class_names:
                                self.class_names.append(class_name)
                    except Exception as e:
                        print(f"加载XML标注失败: {e}")
                elif ext == '.txt':
                    # 假设是YOLO格式
                    h, w = self.current_image.shape[:2]
                    self.annotations = AnnotationFormatConverter.from_yolo(ann_path, w, h, self.class_names)
                    
                    # 更新类别列表
                    for ann in self.annotations:
                        if ann['class_name'] not in self.class_names:
                            self.class_names.append(ann['class_name'])
                
                break
    
    def save_annotations(self, output_format='json'):
        """保存标注"""
        if not self.current_image_path or not self.current_image:
            print("没有可保存的标注")
            return False
        
        base_name = os.path.splitext(self.current_image_path)[0]
        h, w = self.current_image.shape[:2]
        
        if output_format == 'json':
            output_path = base_name + '.json'
            AnnotationFormatConverter.save_as_json(self.annotations, self.current_image_path, w, h, output_path)
        elif output_format == 'xml':
            output_path = base_name + '.xml'
            AnnotationFormatConverter.to_pascal_voc(self.annotations, self.current_image_path, w, h, output_path)
        elif output_format == 'yolo':
            output_path = base_name + '.txt'
            AnnotationFormatConverter.to_yolo(self.annotations, w, h, self.class_names, output_path)
        
        print(f"已保存标注到: {output_path}")
        self.last_save_time = time.time()
        return True
    
    def start_editing(self):
        """开始编辑"""
        print("图像标注工具已启动")
        print("快捷键:")
        print("  s: 保存标注")
        print("  1-4: 切换工具 (矩形, 多边形, 线条, 点)")
        print("  delete/backspace: 删除选中的标注")
        print("  方向键: 平移图像")
        print("  多边形工具: 左键添加点, 右键完成")
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n退出标注工具")
    
    def update(self):
        """更新函数，用于自动保存"""
        current_time = time.time()
        if current_time - self.last_save_time > self.auto_save_interval:
            self.save_annotations()

class BatchAnnotationProcessor:
    """批量标注处理器"""
    
    def __init__(self):
        self.converter = AnnotationFormatConverter()
    
    def convert_format_batch(self, input_dir, output_dir, input_format, output_format, class_names=None):
        """批量转换标注格式"""
        ensure_directory(output_dir)
        
        # 获取所有图像文件
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        image_files = []
        
        for ext in image_extensions:
            pattern = os.path.join(input_dir, f'**/*{ext}')
            image_files.extend(glob.glob(pattern, recursive=True))
        
        print(f"找到 {len(image_files)} 个图像文件")
        
        for image_path in tqdm(image_files, desc="转换进度"):
            # 读取图像获取尺寸
            image = cv2.imread(image_path)
            if image is None:
                continue
            
            h, w = image.shape[:2]
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            
            # 加载标注
            annotations = []
            if input_format == 'json':
                ann_path = os.path.join(input_dir, base_name + '.json')
                annotations, _, _ = self.converter.load_from_json(ann_path)
            elif input_format == 'xml':
                ann_path = os.path.join(input_dir, base_name + '.xml')
                if os.path.exists(ann_path):
                    try:
                        tree = ET.parse(ann_path)
                        root = tree.getroot()
                        
                        for obj in root.findall('object'):
                            class_name = obj.find('name').text
                            bndbox = obj.find('bndbox')
                            x_min = float(bndbox.find('xmin').text)
                            y_min = float(bndbox.find('ymin').text)
                            x_max = float(bndbox.find('xmax').text)
                            y_max = float(bndbox.find('ymax').text)
                            
                            annotations.append({
                                'type': 'rect',
                                'class_name': class_name,
                                'coordinates': [x_min, y_min, x_max, y_max]
                            })
                    except Exception as e:
                        print(f"加载XML标注失败 {ann_path}: {e}")
            elif input_format == 'yolo':
                ann_path = os.path.join(input_dir, base_name + '.txt')
                if os.path.exists(ann_path) and class_names:
                    annotations = self.converter.from_yolo(ann_path, w, h, class_names)
            
            # 保存为新格式
            if annotations:
                if output_format == 'json':
                    output_path = os.path.join(output_dir, base_name + '.json')
                    self.converter.save_as_json(annotations, image_path, w, h, output_path)
                elif output_format == 'xml':
                    output_path = os.path.join(output_dir, base_name + '.xml')
                    self.converter.to_pascal_voc(annotations, image_path, w, h, output_path)
                elif output_format == 'yolo':
                    output_path = os.path.join(output_dir, base_name + '.txt')
                    if class_names:
                        self.converter.to_yolo(annotations, w, h, class_names, output_path)
    
    def generate_annotation_report(self, input_dir, output_path):
        """生成标注统计报告"""
        # 获取所有标注文件
        annotation_extensions = ['.json', '.xml', '.txt']
        annotation_files = []
        
        for ext in annotation_extensions:
            pattern = os.path.join(input_dir, f'**/*{ext}')
            annotation_files.extend(glob.glob(pattern, recursive=True))
        
        print(f"找到 {len(annotation_files)} 个标注文件")
        
        # 统计各类别数量
        class_count = {}
        annotation_type_count = {}
        image_with_annotations = 0
        
        for ann_path in tqdm(annotation_files, desc="统计进度"):
            ext = os.path.splitext(ann_path)[1]
            annotations = []
            
            if ext == '.json':
                annotations, _, _ = self.converter.load_from_json(ann_path)
            elif ext == '.xml':
                try:
                    tree = ET.parse(ann_path)
                    root = tree.getroot()
                    
                    for obj in root.findall('object'):
                        class_name = obj.find('name').text
                        bndbox = obj.find('bndbox')
                        x_min = float(bndbox.find('xmin').text)
                        y_min = float(bndbox.find('ymin').text)
                        x_max = float(bndbox.find('xmax').text)
                        y_max = float(bndbox.find('ymax').text)
                        
                        annotations.append({
                            'type': 'rect',
                            'class_name': class_name,
                            'coordinates': [x_min, y_min, x_max, y_max]
                        })
                except Exception as e:
                    print(f"加载XML标注失败 {ann_path}: {e}")
            
            # 统计
            if annotations:
                image_with_annotations += 1
                
                for ann in annotations:
                    # 统计类别
                    class_name = ann['class_name']
                    class_count[class_name] = class_count.get(class_name, 0) + 1
                    
                    # 统计标注类型
                    ann_type = ann['type']
                    annotation_type_count[ann_type] = annotation_type_count.get(ann_type, 0) + 1
        
        # 生成报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("标注统计报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总标注文件数: {len(annotation_files)}\n")
            f.write(f"有标注的图像数: {image_with_annotations}\n")
            f.write(f"总标注数量: {sum(class_count.values())}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("[类别统计]\n")
            f.write("-" * 80 + "\n")
            for class_name, count in sorted(class_count.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{class_name}: {count}\n")
            f.write("\n")
            
            f.write("[标注类型统计]\n")
            f.write("-" * 80 + "\n")
            for ann_type, count in annotation_type_count.items():
                f.write(f"{ann_type}: {count}\n")
        
        print(f"标注统计报告已保存到: {output_path}")

# 兼容性函数，用于命令行调用
def annotate_image(image_path, output_format='json', class_file=None):
    """标注单个图像"""
    editor = AnnotationEditor()
    
    # 加载类别文件
    if class_file and os.path.exists(class_file):
        try:
            with open(class_file, 'r', encoding='utf-8') as f:
                editor.class_names = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"加载类别文件失败: {e}")
    
    # 加载图像
    if editor.load_image(image_path):
        editor.start_editing()
        # 退出时保存
        editor.save_annotations(output_format)

def batch_convert_annotations(input_dir, output_dir, input_format, output_format, class_file=None):
    """批量转换标注格式"""
    processor = BatchAnnotationProcessor()
    
    # 加载类别文件
    class_names = None
    if class_file and os.path.exists(class_file):
        try:
            with open(class_file, 'r', encoding='utf-8') as f:
                class_names = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"加载类别文件失败: {e}")
    
    processor.convert_format_batch(input_dir, output_dir, input_format, output_format, class_names)

def generate_annotation_stats(input_dir, output_path):
    """生成标注统计报告"""
    processor = BatchAnnotationProcessor()
    processor.generate_annotation_report(input_dir, output_path)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='图像标注工具')
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 标注命令
    annotate_parser = subparsers.add_parser('annotate', help='启动交互式标注工具')
    annotate_parser.add_argument('--image', '-i', required=True, help='要标注的图像路径')
    annotate_parser.add_argument('--format', '-f', default='json', choices=['json', 'xml', 'yolo'],
                               help='标注保存格式')
    annotate_parser.add_argument('--classes', '-c', help='类别列表文件路径')
    
    # 批量转换命令
    convert_parser = subparsers.add_parser('convert', help='批量转换标注格式')
    convert_parser.add_argument('--input-dir', '-i', required=True, help='输入目录')
    convert_parser.add_argument('--output-dir', '-o', required=True, help='输出目录')
    convert_parser.add_argument('--input-format', '-if', required=True, choices=['json', 'xml', 'yolo'],
                              help='输入格式')
    convert_parser.add_argument('--output-format', '-of', required=True, choices=['json', 'xml', 'yolo'],
                               help='输出格式')
    convert_parser.add_argument('--classes', '-c', help='类别列表文件路径')
    
    # 统计命令
    stats_parser = subparsers.add_parser('stats', help='生成标注统计报告')
    stats_parser.add_argument('--input-dir', '-i', required=True, help='包含标注文件的目录')
    stats_parser.add_argument('--output', '-o', default='annotation_stats.txt', help='输出报告路径')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    if args.command == 'annotate':
        # 启动交互式标注工具
        annotate_image(args.image, args.format, args.classes)
    elif args.command == 'convert':
        # 批量转换标注格式
        batch_convert_annotations(args.input_dir, args.output_dir, args.input_format, args.output_format, args.classes)
    elif args.command == 'stats':
        # 生成标注统计报告
        generate_annotation_stats(args.input_dir, args.output)
    else:
        # 显示帮助信息
        print("请指定命令")
        print("可用命令: annotate, convert, stats")
        print("使用 -h 参数查看各命令的详细用法")

if __name__ == "__main__":
    import glob
    main()