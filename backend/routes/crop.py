import os
from flask import Blueprint

from modules.cv_tools import DatasetGenerator, ImageCropper
from routes.utils import (
    ValidationError,
    error_response,
    handle_validation_error,
    parse_json_request,
    task_queued_response,
)


def create_crop_blueprint(task_manager):
    bp = Blueprint('crop', __name__)

    @bp.route('/api/crop', methods=['POST'])
    def crop():
        try:
            data = parse_json_request(
                required=['mode', 'input_path', 'output_dir'],
                exists=['input_path'],
                defaults={
                    'crop_mode': 'adaptive',
                    'window_width': 1024,
                    'window_height': 1024,
                    'overlap_x': 512,
                    'overlap_y': 512,
                    'overlap_ratio': 0.3,
                    'max_retries': 1,
                },
                coerce={
                    'window_width': int,
                    'window_height': int,
                    'overlap_x': int,
                    'overlap_y': int,
                    'overlap_ratio': float,
                    'max_retries': int,
                },
            )

            mode = data['mode']
            crop_mode = data.get('crop_mode', 'adaptive')
            input_path = data['input_path']
            annotations_dir = data.get('annotations_dir')
            output_dir = data['output_dir']
            window_width = data['window_width']
            window_height = data['window_height']
            overlap_x = data['overlap_x']
            overlap_y = data['overlap_y']
            overlap_ratio = data['overlap_ratio']

            if crop_mode == 'fixed':
                if window_width <= 0 or window_height <= 0:
                    raise ValidationError('Window size must be positive', code='ERR_INVALID_FIELD')
                if overlap_x < 0 or overlap_y < 0:
                    raise ValidationError('Overlap must be non-negative', code='ERR_INVALID_FIELD')
                if overlap_x >= window_width or overlap_y >= window_height:
                    raise ValidationError('Overlap must be less than window size', code='ERR_INVALID_FIELD')
            else:
                if overlap_ratio <= 0 or overlap_ratio >= 1:
                    raise ValidationError('Overlap ratio must be between 0 and 1', code='ERR_INVALID_FIELD')

            def run_cropping(task_id, cancel_event, pause_event):
                cropper = ImageCropper()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                if annotations_dir and os.path.exists(annotations_dir):
                    generator = DatasetGenerator()

                    annotation_format = 'voc'
                    if any(f.endswith('.xml') for f in os.listdir(annotations_dir)):
                        annotation_format = 'voc'
                    elif any(f.endswith('.txt') for f in os.listdir(annotations_dir)):
                        annotation_format = 'yolo'
                    elif any(f.endswith('.json') for f in os.listdir(annotations_dir)):
                        annotation_format = 'json'

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
                        'overlap_threshold': 0
                    }

                    result = generator.generate_dataset(gen_config, progress_callback=progress_callback)

                elif mode == 'single':
                    if not os.path.isfile(input_path):
                        raise ValueError('Input path must be a file for single mode')

                    if crop_mode == 'adaptive':
                        result = cropper.crop_image_adaptive(
                            image_path=input_path,
                            output_dir=output_dir,
                            overlap_ratio=overlap_ratio
                        )
                    else:
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
                        raise ValueError('Input path must be a directory for folder mode')

                    if crop_mode == 'adaptive':
                        result = cropper.crop_folder_adaptive(
                            input_dir=input_path,
                            output_dir=output_dir,
                            overlap_ratio=overlap_ratio,
                            progress_callback=progress_callback
                        )
                    else:
                        result = cropper.crop_folder_sliding_window(
                            input_dir=input_path,
                            output_dir=output_dir,
                            window_width=window_width,
                            window_height=window_height,
                            overlap_x=overlap_x,
                            overlap_y=overlap_y,
                            progress_callback=progress_callback
                        )
                else:
                    raise ValueError(f'Invalid mode: {mode}')

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Cropping completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting cropping...',
                run_fn=run_cropping,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Cropping task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
