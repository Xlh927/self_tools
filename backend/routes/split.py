from flask import Blueprint, jsonify, request

from modules.cv_tools import DatasetSplitter
from routes.utils import get_json_body, require_values, error_response


def create_split_blueprint(task_manager):
    bp = Blueprint('split', __name__)

    @bp.route('/api/split', methods=['POST'])
    def split():
        try:
            data = get_json_body()
            ok, resp = require_values(data, [
                ('format', 'Missing required field: format'),
                ('images_dir', 'Missing required field: images_dir'),
                ('annotations_dir', 'Missing required field: annotations_dir'),
                ('output_dir', 'Missing required field: output_dir'),
            ])
            if not ok:
                return resp

            def run_splitting(task_id, cancel_event, pause_event):
                splitter = DatasetSplitter()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = splitter.split_dataset(data, progress_callback=progress_callback)

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Splitting completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting splitting...',
                run_fn=run_splitting
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
