"""
Flask Web Application for Image Processing Tools
Includes dataset format converter and image cropper
"""

from flask import Flask, render_template, request, jsonify
import os
import sys

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from converter import DatasetConverter
from image_cropper import ImageCropper
from dataset_generator import DatasetGenerator
from dataset_splitter import DatasetSplitter
from image_deduplicator import ImageDeduplicator

app = Flask(__name__)


@app.route('/')
def dashboard():
    """Serve the new dashboard"""
    return render_template('dashboard.html')


@app.route('/legacy')
def index():
    """Serve the home page with tool selection"""
    return render_template('index.html')


@app.route('/converter')
def converter_page():
    """Serve the dataset converter page"""
    return render_template('converter.html')


@app.route('/cropper')
def cropper_page():
    """Serve the image cropper page"""
    return render_template('cropper.html')


@app.route('/generator')
def generator_page():
    """Serve the dataset generator page"""
    return render_template('generator.html')


@app.route('/splitter')
def splitter_page():
    """Serve the dataset splitter page"""
    return render_template('splitter.html')


@app.route('/deduplicator')
def deduplicator_page():
    """Serve the image deduplicator page"""
    return render_template('deduplicator.html')


@app.route('/api/convert', methods=['POST'])
def convert():
    """
    Handle dataset conversion requests
    
    Expected JSON payload:
    {
        "conversion_type": "voc_to_yolo" or "yolo_to_voc",
        "annotations_dir": "path/to/annotations",
        "images_dir": "path/to/images",
        "output_dir": "path/to/output",
        "classes_file": "path/to/classes.txt" (optional),
        "custom_classes": ["class0", "class1"] (optional for yolo_to_voc),
        "selected_classes": [0, 1, 2] (optional for voc_to_yolo to filter classes)
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['conversion_type', 'annotations_dir', 'images_dir', 'output_dir']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        conversion_type = data['conversion_type']
        annotations_dir = data['annotations_dir']
        images_dir = data['images_dir']
        output_dir = data['output_dir']
        classes_file = data.get('classes_file', '')
        custom_classes = data.get('custom_classes')
        selected_classes = data.get('selected_classes')
        
        # Validate paths
        if not os.path.exists(annotations_dir):
            return jsonify({
                'success': False,
                'error': f'Annotations directory does not exist: {annotations_dir}'
            }), 400
        
        if not os.path.exists(images_dir):
            return jsonify({
                'success': False,
                'error': f'Images directory does not exist: {images_dir}'
            }), 400
        
        # Create converter
        converter = DatasetConverter(classes_file if classes_file else None)
        
        # Perform conversion
        if conversion_type == 'voc_to_yolo':
            result = converter.voc_to_yolo(
                voc_xml_dir=annotations_dir,
                images_dir=images_dir,
                output_dir=output_dir,
                classes_file=classes_file if classes_file else None
            )
            
            # 应用选定的类别过滤（如果提供）
            if selected_classes and result['success'] and result['classes']:
                # 过滤类别列表
                filtered_classes = [result['classes'][i] for i in selected_classes if i < len(result['classes'])]
                # 过滤后的类别映射
                class_map = {old_idx: new_idx for new_idx, old_idx in enumerate(selected_classes)}
                
                # 重新处理生成的YOLO文件，只保留选定的类别
                output_files = list(Path(output_dir).glob('*.txt'))
                for txt_file in output_files:
                    filtered_lines = []
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            parts = line.strip().split()
                            if parts and int(parts[0]) in selected_classes:
                                # 更新类别ID并添加到过滤行
                                parts[0] = str(class_map[int(parts[0])])
                                filtered_lines.append(' '.join(parts))
                    
                    # 写回过滤后的文件
                    with open(txt_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(filtered_lines))
                
                # 更新类别文件
                classes_output = Path(output_dir) / 'classes.txt'
                with open(classes_output, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(filtered_classes))
                
                # 更新结果
                result['classes'] = filtered_classes
        
        elif conversion_type == 'yolo_to_voc':
            # YOLO到VOC转换不再强制要求classes_file
            result = converter.yolo_to_voc(
                yolo_txt_dir=annotations_dir,
                images_dir=images_dir,
                output_dir=output_dir,
                classes_file=classes_file,
                custom_classes=custom_classes
            )
        else:
            return jsonify({
                'success': False,
                'error': f'Invalid conversion type: {conversion_type}'
            }), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/crop', methods=['POST'])
def crop():
    """
    Handle image cropping requests
    
    Expected JSON payload:
    {
        "mode": "single" or "folder",
        "input_path": "path/to/image or folder",
        "annotations_dir": "path/to/annotations" (optional),
        "output_dir": "path/to/output",
        "window_width": 1024,
        "window_height": 1024,
        "overlap_x": 512,
        "overlap_y": 512
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['mode', 'input_path', 'output_dir']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        mode = data['mode']
        input_path = data['input_path']
        annotations_dir = data.get('annotations_dir')
        output_dir = data['output_dir']
        window_width = int(data.get('window_width', 1024))
        window_height = int(data.get('window_height', 1024))
        overlap_x = int(data.get('overlap_x', 512))
        overlap_y = int(data.get('overlap_y', 512))
        
        # Validate input path
        if not os.path.exists(input_path):
            return jsonify({
                'success': False,
                'error': f'Input path does not exist: {input_path}'
            }), 400
        
        # Validate parameters
        if window_width <= 0 or window_height <= 0:
            return jsonify({
                'success': False,
                'error': 'Window size must be positive'
            }), 400
        
        if overlap_x < 0 or overlap_y < 0:
            return jsonify({
                'success': False,
                'error': 'Overlap must be non-negative'
            }), 400
        
        if overlap_x >= window_width or overlap_y >= window_height:
            return jsonify({
                'success': False,
                'error': 'Overlap must be less than window size'
            }), 400
        
        # Create cropper
        cropper = ImageCropper()
        
        # Perform cropping
        # Perform cropping
        if annotations_dir and os.path.exists(annotations_dir):
            # Use DatasetGenerator for annotation-aware cropping
            generator = DatasetGenerator()
            
            # Auto-detect format
            annotation_format = 'voc' # Default
            if any(f.endswith('.xml') for f in os.listdir(annotations_dir)):
                annotation_format = 'voc'
            elif any(f.endswith('.txt') for f in os.listdir(annotations_dir)):
                annotation_format = 'yolo'
            elif any(f.endswith('.json') for f in os.listdir(annotations_dir)):
                annotation_format = 'json'
            
            # Calculate strides
            stride_x = window_width - overlap_x
            stride_y = window_height - overlap_y
            
            gen_config = {
                'annotation_format': annotation_format,
                'images_dir': input_path if mode == 'folder' else os.path.dirname(input_path),
                'annotations_dir': annotations_dir,
                'output_dir': output_dir,
                'window_width': window_width,
                'window_height': window_height,
                'stride_x': stride_x,
                'stride_y': stride_y,
                'overlap_threshold': 0 # Keep all
            }
            
            # If single mode, we might need to filter or just run for folder (DatasetGenerator is folder-based)
            # For now, running on folder is safer as DatasetGenerator expects dir. 
            # If single file, we could try to restrict but DatasetGenerator scans dir.
            # We'll assume folder mode or user accepts folder processing for now.
            
            result = generator.generate_dataset(gen_config)
            
        elif mode == 'single':
            if not os.path.isfile(input_path):
                return jsonify({
                    'success': False,
                    'error': 'Input path must be a file for single mode'
                }), 400
            
            result = cropper.crop_image_sliding_window(
                image_path=input_path,
                output_dir=output_dir,
                window_width=window_width,
                window_height=window_height,
                overlap_x=overlap_x,
                overlap_y=overlap_y
            )
        elif mode == 'folder':
            if not os.path.isdir(input_path):
                return jsonify({
                    'success': False,
                    'error': 'Input path must be a directory for folder mode'
                }), 400
            
            result = cropper.crop_folder_sliding_window(
                input_dir=input_path,
                output_dir=output_dir,
                window_width=window_width,
                window_height=window_height,
                overlap_x=overlap_x,
                overlap_y=overlap_y
            )
        else:
            return jsonify({
                'success': False,
                'error': f'Invalid mode: {mode}'
            }), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate', methods=['POST'])
def generate():
    """
    Handle dataset generation requests
    
    Expected JSON payload:
    {
        "annotation_format": "voc", "yolo", or "json",
        "images_dir": "path/to/images",
        "annotations_dir": "path/to/annotations",
        "output_dir": "path/to/output",
        "classes": ["person", "car"] or [0, 1, 3],
        "window_width": 640,
        "window_height": 640,
        "stride_x": 320,
        "stride_y": 320,
        "overlap_threshold": 100
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['annotation_format', 'images_dir', 'annotations_dir', 'output_dir']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate paths
        if not os.path.exists(data['images_dir']):
            return jsonify({
                'success': False,
                'error': f'Images directory does not exist: {data["images_dir"]}'
            }), 400
        
        if not os.path.exists(data['annotations_dir']):
            return jsonify({
                'success': False,
                'error': f'Annotations directory does not exist: {data["annotations_dir"]}'
            }), 400
        
        # Create generator
        generator = DatasetGenerator()
        
        # Perform generation
        result = generator.generate_dataset(data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/split', methods=['POST'])
def split():
    """
    Handle dataset splitting requests
    
    Expected JSON payload:
    {
        "format": "voc" or "yolo",
        "format": "voc" or "yolo",
        "images_dir": "path/to/images",
        "annotations_dir": "path/to/annotations",
        "output_dir": "path/to/output",
        "train_ratio": 70,
        "val_ratio": 20,
        "test_ratio": 10,
        "use_background": true,
        "random_seed": 42
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['format', 'images_dir', 'annotations_dir', 'output_dir']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate paths
        if not os.path.exists(data['images_dir']):
            return jsonify({
                'success': False,
                'error': f'Images directory does not exist: {data["images_dir"]}'
            }), 400

        if not os.path.exists(data['annotations_dir']):
            return jsonify({
                'success': False,
                'error': f'Annotations directory does not exist: {data["annotations_dir"]}'
            }), 400
        
        # Create splitter
        splitter = DatasetSplitter()
        
        # Perform splitting
        result = splitter.split_dataset(data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/find-duplicates', methods=['POST'])
def find_duplicates():
    """
    Handle duplicate image detection requests
    
    Expected JSON payload:
    {
        "folder_path": "path/to/images",
        "hash_algorithm": "average", "perceptual", "difference", or "wavelet",
        "use_md5": false,
        "similarity_threshold": 5
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'folder_path' not in data or not data['folder_path']:
            return jsonify({
                'success': False,
                'error': 'Missing required field: folder_path'
            }), 400
        
        folder_path = data['folder_path']
        hash_algorithm = data.get('hash_algorithm', 'average')
        use_md5 = data.get('use_md5', False)
        similarity_threshold = int(data.get('similarity_threshold', 5))
        
        # Validate paths
        if not os.path.exists(folder_path):
            return jsonify({
                'success': False,
                'error': f'Folder does not exist: {folder_path}'
            }), 400
        
        if not os.path.isdir(folder_path):
            return jsonify({
                'success': False,
                'error': f'Path is not a directory: {folder_path}'
            }), 400
        
        # Create deduplicator
        deduplicator = ImageDeduplicator()
        
        # Find duplicates
        duplicates = deduplicator.find_duplicates(
            folder_path=folder_path,
            hash_algorithm=hash_algorithm,
            use_md5=use_md5,
            similarity_threshold=similarity_threshold
        )
        
        # Generate report
        report = deduplicator.get_duplicate_report(duplicates)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/remove-duplicates', methods=['POST'])
def remove_duplicates():
    """
    Handle duplicate image removal requests
    
    Expected JSON payload:
    {
        "folder_path": "path/to/images",
        "hash_algorithm": "average",
        "use_md5": false,
        "similarity_threshold": 5,
        "keep_strategy": "first", "last", "smallest", or "largest",
        "dry_run": true
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'folder_path' not in data or not data['folder_path']:
            return jsonify({
                'success': False,
                'error': 'Missing required field: folder_path'
            }), 400
        
        folder_path = data['folder_path']
        hash_algorithm = data.get('hash_algorithm', 'average')
        use_md5 = data.get('use_md5', False)
        similarity_threshold = int(data.get('similarity_threshold', 5))
        keep_strategy = data.get('keep_strategy', 'first')
        dry_run = data.get('dry_run', True)
        
        # Validate paths
        if not os.path.exists(folder_path):
            return jsonify({
                'success': False,
                'error': f'Folder does not exist: {folder_path}'
            }), 400
        
        # Create deduplicator
        deduplicator = ImageDeduplicator()
        
        # Find duplicates
        duplicates = deduplicator.find_duplicates(
            folder_path=folder_path,
            hash_algorithm=hash_algorithm,
            use_md5=use_md5,
            similarity_threshold=similarity_threshold
        )
        
        # Remove duplicates
        result = deduplicator.remove_duplicates(
            duplicates=duplicates,
            keep_strategy=keep_strategy,
            dry_run=dry_run
        )
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print('🚀 Image Processing Tools Server Starting...')
    print('📱 Open your browser and navigate to: http://localhost:5001')
    print('   - Home: http://localhost:5001/')
    print('   - Dataset Converter: http://localhost:5001/converter')
    print('   - Image Cropper: http://localhost:5001/cropper')
    print('   - Dataset Generator: http://localhost:5001/generator')
    print('   - Dataset Splitter: http://localhost:5001/splitter')
    print('   - Image Deduplicator: http://localhost:5001/deduplicator')
    print('Press Ctrl+C to stop the server')
    app.run(debug=True, host='0.0.0.0', port=5001)