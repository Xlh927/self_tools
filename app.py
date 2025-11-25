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

app = Flask(__name__)


@app.route('/')
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
        "classes_file": "path/to/classes.txt" (optional for voc_to_yolo, required for yolo_to_voc)
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
        elif conversion_type == 'yolo_to_voc':
            if not classes_file or not os.path.exists(classes_file):
                return jsonify({
                    'success': False,
                    'error': 'Classes file is required for YOLO to VOC conversion'
                }), 400
            
            result = converter.yolo_to_voc(
                yolo_txt_dir=annotations_dir,
                images_dir=images_dir,
                output_dir=output_dir,
                classes_file=classes_file
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
        if mode == 'single':
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
        "input_dir": "path/to/dataset",
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
        required_fields = ['format', 'input_dir', 'output_dir']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate paths
        if not os.path.exists(data['input_dir']):
            return jsonify({
                'success': False,
                'error': f'Input directory does not exist: {data["input_dir"]}'
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


if __name__ == '__main__':
    print('🚀 Image Processing Tools Server Starting...')
    print('📱 Open your browser and navigate to: http://localhost:5001')
    print('   - Home: http://localhost:5001/')
    print('   - Dataset Converter: http://localhost:5001/converter')
    print('   - Image Cropper: http://localhost:5001/cropper')
    print('   - Dataset Generator: http://localhost:5001/generator')
    print('   - Dataset Splitter: http://localhost:5001/splitter')
    print('Press Ctrl+C to stop the server')
    app.run(debug=True, host='0.0.0.0', port=5001)
