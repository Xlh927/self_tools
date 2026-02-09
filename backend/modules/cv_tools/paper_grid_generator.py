"""
Paper Grid Generator
论文宫格排版工具 - 用于生成学术论文风格的图片网格
支持灵活布局、合并单元格 (rowspan/colspan)
"""

import os
import cv2
import numpy as np
import concurrent.futures
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union

try:
    from parallelism_config import get_executor_plan
except Exception:  # pragma: no cover - import path differs by runtime entrypoint
    from backend.parallelism_config import get_executor_plan


class PaperGridGenerator:
    """论文宫格生成器"""
    
    def __init__(self):
        self.default_font = "DejaVuSans.ttf"  # Linux常用字体

    @staticmethod
    def _prepare_cell_render_task(
        index: int,
        cell: Dict,
        base_w: int,
        base_h: int,
        padding: int,
        subtitle_height: int,
        margin: int,
        row_label_width: int,
        col_label_height: int,
    ) -> Dict:
        try:
            if 'pil_image' in cell and cell['pil_image'] is not None:
                pil_img = cell['pil_image']
            elif 'path' in cell and cell['path'] and os.path.exists(cell['path']):
                with Image.open(cell['path']) as loaded:
                    pil_img = loaded.copy()
            else:
                return {'success': False, 'index': index, 'error': 'No valid image source'}

            r = int(cell.get('row', 0))
            c = int(cell.get('col', 0))
            rs = int(cell.get('rowspan', 1))
            cs = int(cell.get('colspan', 1))

            target_w = (base_w * cs) + (padding * (cs - 1))
            target_h = (base_h * rs) + (subtitle_height * (rs - 1)) + (padding * (rs - 1))

            pos_x = margin + row_label_width + (c * (base_w + padding))
            pos_y = margin + col_label_height + (r * (base_h + subtitle_height + padding))

            resized = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return {
                'success': True,
                'index': index,
                'image': resized,
                'pos_x': pos_x,
                'pos_y': pos_y,
                'target_w': target_w,
                'target_h': target_h,
                'subtitle': cell.get('subtitle'),
                'row': r,
                'col': c,
            }
        except Exception as e:
            return {'success': False, 'index': index, 'error': str(e)}
        
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
                # Prefer in-memory PIL image if provided
                if 'pil_image' in cell and cell['pil_image'] is not None:
                    img = cell['pil_image']
                    rs = int(cell.get('rowspan', 1))
                    cs = int(cell.get('colspan', 1))
                    w, h = img.size
                    base_w = int((w - (padding * (cs - 1))) / cs)
                    base_h = int((h - (padding * (rs - 1))) / rs)
                    break
                # Fallback to path on disk
                if 'path' in cell and cell['path'] and os.path.exists(cell['path']):
                    try:
                        img = Image.open(cell['path'])
                        rs = int(cell.get('rowspan', 1))
                        cs = int(cell.get('colspan', 1))
                        w, h = img.size
                        base_w = int((w - (padding * (cs - 1))) / cs)
                        base_h = int((h - (padding * (rs - 1))) / rs)
                        break
                    except Exception:
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
            
            # Check if any subtitles exist
            has_subtitles = any(cell.get('subtitle') for cell in cells)
            subtitle_height = 0
            if has_subtitles:
                subtitle_height = font_size + int(padding / 2)

            # 总宽高
            total_width = margin * 2 + row_label_width + (base_w * cols) + (padding * (cols - 1))
            total_height = margin * 2 + col_label_height + (base_h * rows) + (subtitle_height * rows) + (padding * (rows - 1))
            
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
            
            prepared_cells = []
            plan = get_executor_plan(len(cells), workload='io', prefer_process=False)
            if plan.kind == 'serial':
                for index, cell in enumerate(cells):
                    result = self._prepare_cell_render_task(
                        index,
                        cell,
                        base_w,
                        base_h,
                        padding,
                        subtitle_height,
                        margin,
                        row_label_width,
                        col_label_height,
                    )
                    prepared_cells.append(result)
            else:
                # Cell payload may include in-memory PIL objects, so use threads here.
                with concurrent.futures.ThreadPoolExecutor(max_workers=plan.workers) as executor:
                    futures = {
                        executor.submit(
                            self._prepare_cell_render_task,
                            index,
                            cell,
                            base_w,
                            base_h,
                            padding,
                            subtitle_height,
                            margin,
                            row_label_width,
                            col_label_height,
                        ): index
                        for index, cell in enumerate(cells)
                    }
                    for future in concurrent.futures.as_completed(futures):
                        prepared_cells.append(future.result())

            # 按原始顺序绘制，保持同一输入下输出稳定。
            prepared_cells.sort(key=lambda item: item.get('index', 0))
            for item in prepared_cells:
                if not item.get('success'):
                    err = item.get('error', 'unknown error')
                    print(f"Error processing cell index {item.get('index')}: {err}")
                    continue

                pos_x = item['pos_x']
                pos_y = item['pos_y']
                target_w = item['target_w']
                target_h = item['target_h']
                img = item['image']
                canvas.paste(img, (pos_x, pos_y))

                subtitle = item.get('subtitle')
                if subtitle:
                    bbox = draw.textbbox((0, 0), subtitle, font=font)
                    sw = bbox[2] - bbox[0]
                    sh = bbox[3] - bbox[1]
                    sx = pos_x + (target_w - sw) // 2
                    sy = pos_y + target_h + (subtitle_height - sh) // 2
                    draw.text((sx, sy), subtitle, fill=text_color, font=font)
            
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
