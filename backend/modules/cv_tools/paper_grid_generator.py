"""
Paper Grid Generator
论文宫格排版工具 - 用于生成学术论文风格的图片网格
支持灵活布局、合并单元格 (rowspan/colspan)
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union


class PaperGridGenerator:
    """论文宫格生成器"""
    
    def __init__(self):
        self.default_font = "DejaVuSans.ttf"  # Linux常用字体
        
    def generate_grid(self, config: Dict) -> Dict:
        """
        生成图片网格
        
        Args:
            config: 配置字典
                - cells: List[Dict] 单元格列表
                    - path: str 图片路径
                    - row: int 行索引
                    - col: int 列索引
                    - rowspan: int 跨行数 (默认1)
                    - colspan: int 跨列数 (默认1)
                - row_labels: List[str] 行标签
                - col_labels: List[str] 列标签
                - output_path: str 输出路径
                - padding: int 图片间距
                - font_size: int 字体大小
                - margin: int 边距
                - background: str 背景颜色
                
        Returns:
            Dict: 结果信息
        """
        try:
            # 解析配置
            cells = config.get('cells', [])
            if not cells:
                # 兼容旧版 images 二维数组输入
                images = config.get('images', [])
                if images:
                    cells = []
                    for r, row_imgs in enumerate(images):
                        for c, img_path in enumerate(row_imgs):
                            if img_path:
                                cells.append({
                                    'path': img_path,
                                    'row': r,
                                    'col': c,
                                    'rowspan': 1,
                                    'colspan': 1
                                })
            
            if not cells:
                return {'success': False, 'error': 'No images provided'}
                
            row_labels = config.get('row_labels', [])
            col_labels = config.get('col_labels', [])
            output_path = config.get('output_path')
            padding = int(config.get('padding', 10))
            font_size = int(config.get('font_size', 24))
            margin = int(config.get('margin', 20))
            bg_color = config.get('background', 'white')
            
            # 计算网格总行列数
            max_row = 0
            max_col = 0
            for cell in cells:
                r = int(cell.get('row', 0))
                c = int(cell.get('col', 0))
                rs = int(cell.get('rowspan', 1))
                cs = int(cell.get('colspan', 1))
                max_row = max(max_row, r + rs)
                max_col = max(max_col, c + cs)
            
            rows = max_row
            cols = max_col
            
            # 确定基准尺寸
            # 找到第一个有效的图片作为基准
            base_w, base_h = 0, 0
            for cell in cells:
                if os.path.exists(cell['path']):
                    try:
                        img = Image.open(cell['path'])
                        # 如果是跨行/跨列的图片，需要反推基准尺寸
                        # 这里简化处理：假设第一个非跨行跨列的图片为基准
                        # 如果都是跨行跨列，则取第一个图片尺寸除以跨度
                        rs = int(cell.get('rowspan', 1))
                        cs = int(cell.get('colspan', 1))
                        
                        w, h = img.size
                        # 估算单个单元格尺寸 (减去间距)
                        base_w = int((w - (padding * (cs - 1))) / cs)
                        base_h = int((h - (padding * (rs - 1))) / rs)
                        break
                    except:
                        continue
            
            if base_w == 0:
                base_w, base_h = 512, 512 # 默认
            
            # 加载字体
            try:
                font = ImageFont.truetype(self.default_font, font_size)
            except:
                font = ImageFont.load_default()
            
            # 计算标签尺寸
            col_label_height = 0
            if col_labels:
                col_label_height = font_size + padding * 2
                
            row_label_width = 0
            if row_labels:
                max_len = 0
                dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
                for label in row_labels:
                    if label:
                        bbox = dummy_draw.textbbox((0, 0), label, font=font)
                        w = bbox[2] - bbox[0]
                        max_len = max(max_len, w)
                if max_len > 0:
                    row_label_width = max_len + padding * 2
            
            # 总宽高
            total_width = margin * 2 + row_label_width + (base_w * cols) + (padding * (cols - 1))
            total_height = margin * 2 + col_label_height + (base_h * rows) + (padding * (rows - 1))
            
            # 创建画布
            if bg_color == 'transparent':
                canvas = Image.new('RGBA', (total_width, total_height), (0, 0, 0, 0))
                text_color = 'black'
            elif bg_color == 'black':
                canvas = Image.new('RGB', (total_width, total_height), 'black')
                text_color = 'white'
            else:
                canvas = Image.new('RGB', (total_width, total_height), 'white')
                text_color = 'black'
                
            draw = ImageDraw.Draw(canvas)
            
            # 绘制列标签
            if col_labels:
                for c in range(cols):
                    if c < len(col_labels) and col_labels[c]:
                        label = col_labels[c]
                        bbox = draw.textbbox((0, 0), label, font=font)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        
                        # 标签居中于该列
                        x = margin + row_label_width + (c * (base_w + padding)) + (base_w - w) // 2
                        y = margin + (col_label_height - h) // 2 - padding
                        
                        draw.text((x, y), label, fill=text_color, font=font)
            
            # 绘制行标签
            if row_labels:
                for r in range(rows):
                    if r < len(row_labels) and row_labels[r]:
                        label = row_labels[r]
                        bbox = draw.textbbox((0, 0), label, font=font)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        
                        x = margin + (row_label_width - w) // 2 - padding
                        y = margin + col_label_height + (r * (base_h + padding)) + (base_h - h) // 2
                        
                        draw.text((x, y), label, fill=text_color, font=font)
            
            # 绘制图片
            for cell in cells:
                # Check if we have a PIL image object directly
                if 'pil_image' in cell and cell['pil_image'] is not None:
                    pil_img = cell['pil_image']
                elif 'path' in cell and cell['path'] and os.path.exists(cell['path']):
                    try:
                        pil_img = Image.open(cell['path'])
                    except Exception as e:
                        print(f"Error loading {cell['path']}: {e}")
                        continue
                else:
                    continue  # No valid image source
                
                r = int(cell.get('row', 0))
                c = int(cell.get('col', 0))
                rs = int(cell.get('rowspan', 1))
                cs = int(cell.get('colspan', 1))
                
                # 计算目标尺寸
                target_w = (base_w * cs) + (padding * (cs - 1))
                target_h = (base_h * rs) + (padding * (rs - 1))
                
                # 计算位置
                pos_x = margin + row_label_width + (c * (base_w + padding))
                pos_y = margin + col_label_height + (r * (base_h + padding))
                
                try:
                    # 缩放
                    img = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    canvas.paste(img, (pos_x, pos_y))
                except Exception as e:
                    print(f"Error processing cell at ({r}, {c}): {e}")
            
            # 保存结果
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            canvas.save(output_path, quality=95)
            
            return {
                'success': True,
                'output_path': output_path,
                'width': total_width,
                'height': total_height
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
