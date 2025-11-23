#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理模块（A8）

功能：
- 视频剪辑、合并、转码
- 视频帧提取、插入
- 视频倍速调整
- 视频降噪
- 视频字幕叠加
- 视频水印添加/移除

支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
from tqdm import tqdm
import subprocess
import tempfile
import shutil
from datetime import timedelta

def get_video_info(video_path):
    """获取视频信息"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"无法打开视频文件: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    
    cap.release()
    return {
        'fps': fps,
        'frame_count': frame_count,
        'width': width,
        'height': height,
        'duration': duration
    }

def format_time(seconds):
    """将秒数格式化为 HH:MM:SS.XXX 格式"""
    return str(timedelta(seconds=seconds))

def cut_video(input_path, output_path, start_time, end_time):
    """
    视频剪辑
    start_time: 开始时间（秒）
    end_time: 结束时间（秒）
    """
    try:
        # 使用ffmpeg进行视频剪辑（更高效和稳定）
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-ss', format_time(start_time),
            '-to', format_time(end_time),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-strict', 'experimental',
            '-preset', 'medium',
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"视频剪辑失败: {e}")
        return False
    except Exception as e:
        print(f"视频剪辑错误: {e}")
        return False

def merge_videos(input_paths, output_path):
    """合并多个视频文件"""
    try:
        # 创建临时文件列表
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for path in input_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
            temp_list_file = f.name
        
        # 使用ffmpeg合并视频
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', temp_list_file,
            '-c', 'copy',
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.unlink(temp_list_file)  # 删除临时文件
        return True
    except subprocess.CalledProcessError as e:
        print(f"视频合并失败: {e}")
        return False
    except Exception as e:
        print(f"视频合并错误: {e}")
        return False

def transcode_video(input_path, output_path, codec='libx264', crf=23, preset='medium', audio_codec='aac'):
    """
    视频转码
    codec: 视频编码器
    crf: 恒定质量因子 (0-51, 越低质量越好)
    preset: 编码速度/质量预设
    """
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', codec,
            '-crf', str(crf),
            '-preset', preset,
            '-c:a', audio_codec,
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"视频转码失败: {e}")
        return False
    except Exception as e:
        print(f"视频转码错误: {e}")
        return False

def extract_frames(video_path, output_dir, interval=1, start_time=0, end_time=None):
    """
    提取视频帧
    interval: 提取间隔（秒）
    start_time: 开始时间（秒）
    end_time: 结束时间（秒）
    """
    try:
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"无法打开视频文件: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # 设置时间范围
        start_frame = int(start_time * fps)
        end_frame = total_frames if end_time is None else min(int(end_time * fps), total_frames)
        
        # 计算提取帧的间隔（帧数）
        frame_interval = max(1, int(interval * fps))
        
        # 设置起始位置
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        extracted_count = 0
        for frame_idx in tqdm(range(start_frame, end_frame, frame_interval), desc="提取帧"):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            
            # 保存帧
            frame_time = frame_idx / fps
            output_path = os.path.join(output_dir, f"frame_{frame_time:.3f}s.jpg")
            cv2.imwrite(output_path, frame)
            extracted_count += 1
        
        cap.release()
        print(f"共提取 {extracted_count} 帧到目录: {output_dir}")
        return True
    except Exception as e:
        print(f"帧提取错误: {e}")
        return False

def adjust_speed(video_path, output_path, speed_factor):
    """
    调整视频速度
    speed_factor: 速度因子 (>1 加速, <1 减速)
    """
    try:
        # 计算音频和视频的变速参数
        atempo = min(2.0, max(0.5, speed_factor))  # atempo限制在0.5-2.0之间
        video_timescale = 1.0 / speed_factor
        
        # 对于超出范围的速度因子，可能需要多次应用atempo
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-filter_complex',
            f"[0:v]setpts={video_timescale}*PTS[v];[0:a]atempo={atempo}[a]"
        ]
        
        if speed_factor > 2.0:
            # 对于更快的速度，链式应用atempo
            atempo_steps = int(np.log2(speed_factor))
            remaining_factor = speed_factor / (2.0 ** atempo_steps)
            
            atempo_filters = "[0:a]"
            for i in range(atempo_steps):
                atempo_filters += f"atempo=2.0[{i}a];[{i}a]"
            atempo_filters += f"atempo={remaining_factor}[a]"
            
            cmd[5] = f"[0:v]setpts={video_timescale}*PTS[v];{atempo_filters}"
        
        cmd.extend(['-map', '[v]', '-map', '[a]', output_path])
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"速度调整失败: {e}")
        return False
    except Exception as e:
        print(f"速度调整错误: {e}")
        return False

def denoise_video(input_path, output_path, strength=10):
    """
    视频降噪
    strength: 降噪强度
    """
    try:
        # 使用ffmpeg的hqdn3d滤镜进行降噪
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-vf', f'hqdn3d={strength}:{strength}:{strength}:{strength}',
            '-c:a', 'copy',
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"视频降噪失败: {e}")
        return False
    except Exception as e:
        print(f"视频降噪错误: {e}")
        return False

def add_subtitle(video_path, subtitle_path, output_path):
    """
    视频添加字幕
    subtitle_path: SRT或ASS格式的字幕文件
    """
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', f"subtitles={subtitle_path}",
            '-c:a', 'copy',
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"添加字幕失败: {e}")
        return False
    except Exception as e:
        print(f"添加字幕错误: {e}")
        return False

def add_watermark(video_path, watermark_path, output_path, position='bottom-right', opacity=0.5):
    """
    视频添加水印
    position: 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'
    opacity: 水印透明度 (0.0-1.0)
    """
    try:
        # 构建水印滤镜
        position_map = {
            'top-left': '10:10',
            'top-right': 'main_w-overlay_w-10:10',
            'bottom-left': '10:main_h-overlay_h-10',
            'bottom-right': 'main_w-overlay_w-10:main_h-overlay_h-10',
            'center': 'main_w/2-overlay_w/2:main_h/2-overlay_h/2'
        }
        
        pos = position_map.get(position, 'bottom-right')
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', watermark_path,
            '-filter_complex',
            f"[1]format=rgba,colorchannelmixer=aa={opacity}[watermark];[0][watermark]overlay={pos}",
            '-c:a', 'copy',
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"添加水印失败: {e}")
        return False
    except Exception as e:
        print(f"添加水印错误: {e}")
        return False

def process_directory(input_dir, output_dir, operation_func, operation_args, recursive=False, video_extensions=None):
    """批量处理目录中的视频"""
    if video_extensions is None:
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    
    processed_count = 0
    failed_count = 0
    
    if recursive:
        walk_func = os.walk
    else:
        def walk_func(path):
            yield (path, [], [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
    
    for root, _, files in tqdm(walk_func(input_dir), desc="处理进度"):
        for file in files:
            if any(file.lower().endswith(ext) for ext in video_extensions):
                input_path = os.path.join(root, file)
                
                # 保持目录结构
                relative_path = os.path.relpath(root, input_dir)
                if relative_path == '.':
                    relative_path = ''
                
                output_path = os.path.join(output_dir, relative_path, file)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 执行操作
                if operation_func(input_path, output_path, **operation_args):
                    processed_count += 1
                else:
                    failed_count += 1
    
    print(f"处理完成! 成功: {processed_count}, 失败: {failed_count}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='视频处理工具')
    parser.add_argument('--input', '-i', required=True, help='输入视频或目录路径')
    parser.add_argument('--output', '-o', required=True, help='输出视频或目录路径')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    # 操作类型选择
    operation_group = parser.add_mutually_exclusive_group(required=True)
    operation_group.add_argument('--info', action='store_true', help='显示视频信息')
    operation_group.add_argument('--cut', action='store_true', help='视频剪辑')
    operation_group.add_argument('--merge', action='store_true', help='合并视频（输入应为包含多个视频的目录）')
    operation_group.add_argument('--transcode', action='store_true', help='视频转码')
    operation_group.add_argument('--extract-frames', action='store_true', help='提取视频帧')
    operation_group.add_argument('--adjust-speed', action='store_true', help='调整视频速度')
    operation_group.add_argument('--denoise', action='store_true', help='视频降噪')
    operation_group.add_argument('--add-subtitle', action='store_true', help='添加字幕')
    operation_group.add_argument('--add-watermark', action='store_true', help='添加水印')
    
    # 视频剪辑参数
    parser.add_argument('--start-time', type=float, default=0, help='剪辑开始时间（秒）')
    parser.add_argument('--end-time', type=float, help='剪辑结束时间（秒）')
    
    # 转码参数
    parser.add_argument('--codec', type=str, default='libx264', help='视频编码器')
    parser.add_argument('--crf', type=int, default=23, help='恒定质量因子 (0-51, 越低质量越好)')
    parser.add_argument('--preset', type=str, default='medium', help='编码速度/质量预设')
    parser.add_argument('--audio-codec', type=str, default='aac', help='音频编码器')
    
    # 帧提取参数
    parser.add_argument('--interval', type=float, default=1, help='帧提取间隔（秒）')
    
    # 速度调整参数
    parser.add_argument('--speed-factor', type=float, default=1.0, help='速度因子 (>1 加速, <1 减速)')
    
    # 降噪参数
    parser.add_argument('--denoise-strength', type=int, default=10, help='降噪强度')
    
    # 字幕参数
    parser.add_argument('--subtitle', type=str, help='字幕文件路径')
    
    # 水印参数
    parser.add_argument('--watermark', type=str, help='水印图像路径')
    parser.add_argument('--position', type=str, default='bottom-right',
                      choices=['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'],
                      help='水印位置')
    parser.add_argument('--opacity', type=float, default=0.5, help='水印透明度 (0.0-1.0)')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 显示视频信息
    if args.info:
        if os.path.isfile(args.input):
            try:
                info = get_video_info(args.input)
                print(f"视频信息:")
                print(f"  分辨率: {info['width']}x{info['height']}")
                print(f"  FPS: {info['fps']}")
                print(f"  总帧数: {info['frame_count']}")
                print(f"  时长: {format_time(info['duration'])}")
            except Exception as e:
                print(f"获取视频信息失败: {e}")
        else:
            print(f"输入路径不是文件: {args.input}")
        return
    
    # 视频剪辑
    elif args.cut:
        if os.path.isfile(args.input):
            # 获取视频信息以确定默认结束时间
            if args.end_time is None:
                try:
                    info = get_video_info(args.input)
                    args.end_time = info['duration']
                except:
                    print("警告: 无法获取视频时长，请手动指定结束时间")
                    return
            
            if cut_video(args.input, args.output, args.start_time, args.end_time):
                print(f"视频已成功剪辑并保存到: {args.output}")
            else:
                print("视频剪辑失败")
        elif os.path.isdir(args.input):
            operation_args = {
                'start_time': args.start_time,
                'end_time': args.end_time
            }
            process_directory(args.input, args.output, cut_video, operation_args, args.recursive)
        else:
            print(f"输入路径不存在: {args.input}")
    
    # 合并视频
    elif args.merge:
        if os.path.isdir(args.input):
            # 获取目录中的所有视频文件
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
            video_files = [os.path.join(args.input, f) for f in os.listdir(args.input)
                          if os.path.isfile(os.path.join(args.input, f)) and \
                          any(f.lower().endswith(ext) for ext in video_extensions)]
            
            if video_files:
                if merge_videos(sorted(video_files), args.output):
                    print(f"视频已成功合并并保存到: {args.output}")
                else:
                    print("视频合并失败")
            else:
                print(f"目录中没有找到视频文件: {args.input}")
        else:
            print(f"输入路径不是目录: {args.input}")
    
    # 视频转码
    elif args.transcode:
        operation_args = {
            'codec': args.codec,
            'crf': args.crf,
            'preset': args.preset,
            'audio_codec': args.audio_codec
        }
        
        if os.path.isfile(args.input):
            if transcode_video(args.input, args.output, **operation_args):
                print(f"视频已成功转码并保存到: {args.output}")
            else:
                print("视频转码失败")
        elif os.path.isdir(args.input):
            process_directory(args.input, args.output, transcode_video, operation_args, args.recursive)
        else:
            print(f"输入路径不存在: {args.input}")
    
    # 提取视频帧
    elif args.extract_frames:
        if os.path.isfile(args.input):
            extract_frames(args.input, args.output, args.interval, args.start_time, args.end_time)
        elif os.path.isdir(args.input):
            # 为每个视频创建单独的输出子目录
            for file in os.listdir(args.input):
                file_path = os.path.join(args.input, file)
                if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in 
                                                   ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']):
                    # 获取文件名（不含扩展名）作为子目录名
                    base_name = os.path.splitext(file)[0]
                    output_subdir = os.path.join(args.output, base_name)
                    extract_frames(file_path, output_subdir, args.interval, args.start_time, args.end_time)
        else:
            print(f"输入路径不存在: {args.input}")
    
    # 调整视频速度
    elif args.adjust_speed:
        operation_args = {'speed_factor': args.speed_factor}
        
        if os.path.isfile(args.input):
            if adjust_speed(args.input, args.output, args.speed_factor):
                print(f"视频速度已成功调整并保存到: {args.output}")
            else:
                print("视频速度调整失败")
        elif os.path.isdir(args.input):
            process_directory(args.input, args.output, adjust_speed, operation_args, args.recursive)
        else:
            print(f"输入路径不存在: {args.input}")
    
    # 视频降噪
    elif args.denoise:
        operation_args = {'strength': args.denoise_strength}
        
        if os.path.isfile(args.input):
            if denoise_video(args.input, args.output, args.denoise_strength):
                print(f"视频已成功降噪并保存到: {args.output}")
            else:
                print("视频降噪失败")
        elif os.path.isdir(args.input):
            process_directory(args.input, args.output, denoise_video, operation_args, args.recursive)
        else:
            print(f"输入路径不存在: {args.input}")
    
    # 添加字幕
    elif args.add_subtitle:
        if not args.subtitle:
            print("错误: 请指定字幕文件路径")
            return
        
        if os.path.isfile(args.input):
            if add_subtitle(args.input, args.subtitle, args.output):
                print(f"字幕已成功添加并保存到: {args.output}")
            else:
                print("添加字幕失败")
        elif os.path.isdir(args.input):
            # 批量添加字幕，假设字幕文件与视频文件同名但扩展名为.srt
            for file in os.listdir(args.input):
                file_path = os.path.join(args.input, file)
                if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in 
                                                   ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']):
                    # 尝试找到对应的字幕文件
                    base_name = os.path.splitext(file)[0]
                    sub_path = os.path.join(os.path.dirname(args.subtitle), f"{base_name}.srt")
                    
                    if os.path.exists(sub_path):
                        output_path = os.path.join(args.output, file)
                        os.makedirs(args.output, exist_ok=True)
                        add_subtitle(file_path, sub_path, output_path)
                    else:
                        print(f"未找到对应的字幕文件: {sub_path}")
        else:
            print(f"输入路径不存在: {args.input}")
    
    # 添加水印
    elif args.add_watermark:
        if not args.watermark:
            print("错误: 请指定水印图像路径")
            return
        
        operation_args = {
            'watermark_path': args.watermark,
            'position': args.position,
            'opacity': args.opacity
        }
        
        if os.path.isfile(args.input):
            if add_watermark(args.input, args.watermark, args.output, args.position, args.opacity):
                print(f"水印已成功添加并保存到: {args.output}")
            else:
                print("添加水印失败")
        elif os.path.isdir(args.input):
            # 使用自定义的处理函数以适应多参数
            def watermark_func(input_path, output_path, **kwargs):
                return add_watermark(input_path, kwargs['watermark_path'], output_path, 
                                   kwargs['position'], kwargs['opacity'])
            
            process_directory(args.input, args.output, watermark_func, operation_args, args.recursive)
        else:
            print(f"输入路径不存在: {args.input}")

if __name__ == "__main__":
    main()