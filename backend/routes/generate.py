from flask import Blueprint, jsonify, request

from modules.cv_tools import DatasetGenerator
from routes.utils import get_json_body, require_values, require_exists, error_response


def create_generate_blueprint(task_manager):
    bp = Blueprint('generate', __name__)

    @bp.route('/api/generate', methods=['POST'])
    def generate():
        try:
            data = get_json_body()
            ok, resp = require_values(data, [
                ('annotation_format', 'Missing required field: annotation_format'),
                ('images_dir', 'Missing required field: images_dir'),
                ('annotations_dir', 'Missing required field: annotations_dir'),
                ('output_dir', 'Missing required field: output_dir'),
            ])
            if not ok:
                return resp

            ok, resp = require_exists(data['images_dir'], f'Images directory does not exist: {data["images_dir"]}')
            if not ok:
                return resp
            ok, resp = require_exists(data['annotations_dir'], f'Annotations directory does not exist: {data["annotations_dir"]}')
            if not ok:
                return resp

            def run_generation(task_id, cancel_event, pause_event):
                generator = DatasetGenerator()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = generator.generate_dataset(data, progress_callback=progress_callback)

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Generation completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting generation...',
                run_fn=run_generation
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
