import os
from flask import Blueprint

from modules.cv_tools import DatasetGenerator, ImageCropper
from routes.utils import (
    ValidationError,
    queue_json_task,
    run_with_error_handling,
)


def create_crop_blueprint(task_manager):
    bp = Blueprint('crop', __name__)

    @bp.route('/api/crop', methods=['POST'])
    def crop():
        def _handle():
            def _work(data, _task_id, _cancel_event, _pause_event, progress_callback):
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
                labeled_crop_mode = data['labeled_crop_mode']
                minvis = data['minvis']

                has_annotations = bool(annotations_dir and os.path.exists(annotations_dir))

                if has_annotations:
                    if labeled_crop_mode not in ('sliding', 'target_center'):
                        raise ValidationError('Invalid labeled crop mode', code='ERR_INVALID_FIELD')
                    if overlap_ratio < 0 or overlap_ratio > 1:
                        raise ValidationError('Overlap ratio must be between 0 and 1', code='ERR_INVALID_FIELD')
                    if minvis < 0 or minvis > 1:
                        raise ValidationError('Min visible ratio must be between 0 and 1', code='ERR_INVALID_FIELD')
                elif crop_mode == 'fixed':
                    if window_width <= 0 or window_height <= 0:
                        raise ValidationError('Window size must be positive', code='ERR_INVALID_FIELD')
                    if overlap_x < 0 or overlap_y < 0:
                        raise ValidationError('Overlap must be non-negative', code='ERR_INVALID_FIELD')
                    if overlap_x >= window_width or overlap_y >= window_height:
                        raise ValidationError('Overlap must be less than window size', code='ERR_INVALID_FIELD')
                else:
                    if overlap_ratio <= 0 or overlap_ratio >= 1:
                        raise ValidationError('Overlap ratio must be between 0 and 1', code='ERR_INVALID_FIELD')

                cropper = ImageCropper()
                if has_annotations:
                    generator = DatasetGenerator()

                    annotation_files = os.listdir(annotations_dir)
                    annotation_format = None
                    if any(f.lower().endswith('.xml') for f in annotation_files):
                        annotation_format = 'voc'
                    elif any(f.lower().endswith('.txt') for f in annotation_files if f.lower() != 'classes.txt'):
                        annotation_format = 'yolo'
                    if annotation_format is None:
                        raise ValidationError('Only YOLO txt and VOC xml annotations are supported', code='ERR_INVALID_FIELD')

                    gen_config = {
                        'annotation_format': annotation_format,
                        'images_dir': input_path if mode == 'folder' else os.path.dirname(input_path),
                        'input_image_path': input_path if mode == 'single' else None,
                        'annotations_dir': annotations_dir,
                        'output_dir': output_dir,
                        'adaptive_window': True,
                        'labeled_crop_mode': labeled_crop_mode,
                        'overlap_ratio': overlap_ratio,
                        'minvis': minvis,
                        'preserve_annotation_format': True,
                    }
                    return generator.generate_dataset(gen_config, progress_callback=progress_callback)

                if mode == 'single':
                    if not os.path.isfile(input_path):
                        raise ValueError('Input path must be a file for single mode')
                    if crop_mode == 'adaptive':
                        return cropper.crop_image_adaptive(
                            image_path=input_path,
                            output_dir=output_dir,
                            overlap_ratio=overlap_ratio,
                        )
                    return cropper.crop_image_sliding_window(
                        image_path=input_path,
                        output_dir=output_dir,
                        window_width=window_width,
                        window_height=window_height,
                        overlap_x=overlap_x,
                        overlap_y=overlap_y,
                    )

                if mode == 'folder':
                    if not os.path.isdir(input_path):
                        raise ValueError('Input path must be a directory for folder mode')
                    if crop_mode == 'adaptive':
                        return cropper.crop_folder_adaptive(
                            input_dir=input_path,
                            output_dir=output_dir,
                            overlap_ratio=overlap_ratio,
                            progress_callback=progress_callback,
                        )
                    return cropper.crop_folder_sliding_window(
                        input_dir=input_path,
                        output_dir=output_dir,
                        window_width=window_width,
                        window_height=window_height,
                        overlap_x=overlap_x,
                        overlap_y=overlap_y,
                        progress_callback=progress_callback,
                    )

                raise ValueError(f'Invalid mode: {mode}')

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['mode', 'input_path', 'output_dir'],
                    'exists': ['input_path'],
                    'defaults': {
                        'crop_mode': 'adaptive',
                        'window_width': 1024,
                        'window_height': 1024,
                        'overlap_x': 512,
                        'overlap_y': 512,
                        'overlap_ratio': 0.3,
                        'labeled_crop_mode': 'sliding',
                        'minvis': 0.3,
                    },
                    'coerce': {
                        'window_width': int,
                        'window_height': int,
                        'overlap_x': int,
                        'overlap_y': int,
                        'overlap_ratio': float,
                        'minvis': float,
                    },
                },
                start_message='Starting cropping...',
                queued_message='Cropping task queued',
                success_message='Cropping completed',
                work_fn=_work,
            )

        return run_with_error_handling(_handle)

    return bp
