from flask import Blueprint, jsonify, request

from modules.cv_tools import DataAugmentor
from routes.utils import get_json_body, require_values, require_exists, error_response


def create_augment_blueprint(task_manager):
    bp = Blueprint('augment', __name__)

    @bp.route('/api/augment', methods=['POST'])
    def augment_dataset():
        try:
            data = get_json_body()
            ok, resp = require_values(data, [
                ('images_dir', 'Missing required field: images_dir'),
                ('annotations_dir', 'Missing required field: annotations_dir'),
                ('output_dir', 'Missing required field: output_dir'),
                ('annotation_format', 'Missing required field: annotation_format'),
            ])
            if not ok:
                return resp

            ok, resp = require_exists(data['images_dir'], f'Images directory does not exist: {data["images_dir"]}')
            if not ok:
                return resp
            ok, resp = require_exists(data['annotations_dir'], f'Annotations directory does not exist: {data["annotations_dir"]}')
            if not ok:
                return resp

            def run_augmentation(task_id, cancel_event, pause_event):
                augmentor = DataAugmentor()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = augmentor.augment_dataset(
                    config=data,
                    progress_callback=progress_callback
                )

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Augmentation completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting augmentation...',
                run_fn=run_augmentation
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
