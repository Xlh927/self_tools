import os
import sys
import subprocess
import tempfile
import json
import ast
import inspect
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

# 添加scripts目录到Python路径
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

# 加载脚本信息
import os
import json

SCRIPTS_INFO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts_info.json')

# 重新加载脚本信息的函数
def load_scripts_info():
    try:
        with open(SCRIPTS_INFO_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 支持新旧格式
        if 'scripts_dict' in data:
            return data
        else:
            # 转换为新格式
            scripts_dict = {}
            for script in data:
                module_name = script['module_name']
                scripts_dict[module_name] = {
                    'display_name': script['display_name'],
                    'functions': script['functions'],
                    'params': script.get('params', [])
                }
            return {
                'scripts_list': data,
                'scripts_dict': scripts_dict
            }
    except Exception as e:
        print(f"加载脚本信息失败: {str(e)}")
        return {'scripts_list': [], 'scripts_dict': {}}

# 初始加载脚本信息
scripts_info = load_scripts_info()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute_script', methods=['POST'])
def execute_script():
    try:
        # 获取模块名称
        module_name = request.form.get('module')
        if not module_name:
            return jsonify({'error': '请指定要执行的模块名称'}), 400
        
        # 脚本目录路径
        scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
        script_path = os.path.join(scripts_dir, f'{module_name}.py')
        
        # 检查脚本文件是否存在
        if not os.path.exists(script_path):
            return jsonify({'error': f'脚本文件 {module_name}.py 不存在'}), 404
        
        # 构建基本命令
        cmd_args = ['python', script_path]
        
        # 获取输入路径、输出路径和其他参数
        input_path = request.form.get('input_path')
        output_path = request.form.get('output_path')
        params = request.form.get('params', '{}')
        
        # 添加输入输出路径参数
        if input_path:
            cmd_args.extend(['--input-path', input_path])
        if output_path:
            cmd_args.extend(['--output-path', output_path])
        
        # 尝试解析JSON参数
        try:
            custom_params = json.loads(params)
            # 将JSON参数转换为命令行参数
            for key, value in custom_params.items():
                # 将key转换为命令行参数格式，如param1 -> --param1
                param_name = f'--{key.replace("_", "-")}'
                # 添加参数
                if isinstance(value, bool):
                    # 布尔值参数只添加标志，不添加值
                    if value:
                        cmd_args.append(param_name)
                elif isinstance(value, list):
                    # 列表参数为多个值
                    for v in value:
                        cmd_args.extend([param_name, str(v)])
                else:
                    # 其他类型参数
                    cmd_args.extend([param_name, str(value)])
        except json.JSONDecodeError:
            return jsonify({'error': '参数格式错误，请确保为有效的JSON格式'}), 400
        
        # 执行命令
        print(f"执行脚本: {' '.join(cmd_args)}")
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        
        # 检查是否成功执行
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '脚本执行成功',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': '脚本执行失败',
                'output': result.stdout,
                'stderr': result.stderr
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convert', methods=['POST'])
def convert():
    try:
        # 获取表单数据
        command = request.form.get('command')
        
        if not command:
            return jsonify({'error': '请选择转换命令'}), 400
        
        # 构建命令参数
        cmd_args = ['python', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts', 'dataset_format_converter.py'), command]
        
        # 根据命令类型添加相应参数
        if command == 'voc2yolo':
            voc_dir = request.form.get('voc_dir')
            output_dir = request.form.get('output_dir')
            class_file = request.form.get('class_file')
            image_dir = request.form.get('image_dir')
            
            if not voc_dir or not output_dir:
                return jsonify({'error': '请提供VOC目录和输出目录'}), 400
            
            cmd_args.extend(['--voc-dir', voc_dir])
            cmd_args.extend(['--output-dir', output_dir])
            if class_file:
                cmd_args.extend(['--class-file', class_file])
            if image_dir:
                cmd_args.extend(['--image-dir', image_dir])
        
        elif command == 'yolo2voc':
            yolo_dir = request.form.get('yolo_dir')
            output_dir = request.form.get('output_dir')
            class_file = request.form.get('class_file')
            image_dir = request.form.get('image_dir')
            
            if not yolo_dir or not output_dir:
                return jsonify({'error': '请提供YOLO目录和输出目录'}), 400
            
            cmd_args.extend(['--yolo-dir', yolo_dir])
            cmd_args.extend(['--output-dir', output_dir])
            if class_file:
                cmd_args.extend(['--class-file', class_file])
            if image_dir:
                cmd_args.extend(['--image-dir', image_dir])
        
        elif command == 'yolo2coco':
            yolo_dir = request.form.get('yolo_dir')
            image_dir = request.form.get('image_dir')
            output_json = request.form.get('output_json')
            class_file = request.form.get('class_file')
            
            if not yolo_dir or not image_dir or not output_json:
                return jsonify({'error': '请提供YOLO目录、图像目录和输出JSON文件'}), 400
            
            cmd_args.extend(['--yolo-dir', yolo_dir])
            cmd_args.extend(['--image-dir', image_dir])
            cmd_args.extend(['--output-json', output_json])
            if class_file:
                cmd_args.extend(['--class-file', class_file])
        
        elif command == 'coco2yolo':
            coco_json = request.form.get('coco_json')
            output_dir = request.form.get('output_dir')
            image_dir = request.form.get('image_dir')
            
            if not coco_json or not output_dir:
                return jsonify({'error': '请提供COCO JSON文件和输出目录'}), 400
            
            cmd_args.extend(['--coco-json', coco_json])
            cmd_args.extend(['--output-dir', output_dir])
            if image_dir:
                cmd_args.extend(['--image-dir', image_dir])
        
        # 执行命令
        print(f"执行命令: {' '.join(cmd_args)}")
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        
        # 检查是否成功执行
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '转换成功',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': '转换失败',
                'output': result.stdout,
                'stderr': result.stderr
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def parse_script_params(script_path):
    """
    解析Python脚本并提取参数信息
    尝试通过多种方法获取参数信息：
    1. 分析argparse定义
    2. 查找docstring中的参数说明
    3. 返回通用参数模板
    """
    params_info = {
        'params': [],
        'description': '通用参数设置'
    }
    
    try:
        # 尝试运行脚本并获取参数帮助信息
        result = subprocess.run(
            ['python', script_path, '--help'],
            capture_output=True, 
            text=True,
            timeout=5  # 5秒超时，防止脚本执行其他操作
        )
        
        # 如果--help执行成功，解析帮助输出
        if result.returncode == 0 and '--help' in result.stdout:
            # 这里可以添加更复杂的解析逻辑来提取参数信息
            # 简化版本：设置通用参数并包含帮助文本
            params_info['description'] = '根据脚本帮助文档自动生成'
            params_info['help_text'] = result.stdout
    except Exception as e:
        print(f"解析脚本参数失败: {str(e)}")
    
    # 如果无法自动解析，添加通用参数模板
    if len(params_info['params']) == 0:
        params_info['params'] = [
            {
                'name': 'input_path',
                'type': 'string',
                'required': True,
                'help': '输入文件或目录路径'
            },
            {
                'name': 'output_path',
                'type': 'string',
                'required': True,
                'help': '输出文件或目录路径'
            },
            {
                'name': 'verbose',
                'type': 'boolean',
                'required': False,
                'help': '启用详细输出模式'
            }
        ]
    
    return params_info

@app.route('/get_script_params/<module_name>', methods=['GET'])
def get_script_params(module_name):
    """
    获取指定脚本的参数信息
    """
    # 重新加载脚本信息，确保使用最新数据
    current_info = load_scripts_info()
    
    # 首先尝试从scripts_dict中获取
    if 'scripts_dict' in current_info and module_name in current_info['scripts_dict']:
        script_data = current_info['scripts_dict'][module_name]
        if 'params' in script_data and script_data['params']:
            return jsonify({
                'success': True,
                'module': module_name,
                'params': script_data['params'],
                'description': script_data.get('display_name', '脚本参数'),
                'help_text': ''
            })
    
    # 如果未找到，尝试从scripts_list中查找
    if 'scripts_list' in current_info:
        for script in current_info['scripts_list']:
            if script.get('module_name') == module_name:
                if 'params' in script and script['params']:
                    return jsonify({
                        'success': True,
                        'module': module_name,
                        'params': script['params'],
                        'description': script.get('display_name', '脚本参数'),
                        'help_text': ''
                    })
                break
    
    # 如果仍然未找到，尝试原始的解析方法
    try:
        # 脚本目录路径
        scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
        script_path = os.path.join(scripts_dir, f'{module_name}.py')
        
        # 检查脚本文件是否存在
        if not os.path.exists(script_path):
            return jsonify({'error': f'脚本文件 {module_name}.py 不存在'}), 404
        
        # 解析脚本参数
        params_info = parse_script_params(script_path)
        
        return jsonify({
            'success': True,
            'module': module_name,
            'params': params_info['params'],
            'description': params_info['description'],
            'help_text': params_info.get('help_text', '')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
