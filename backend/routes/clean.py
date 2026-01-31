from flask import Blueprint, jsonify, request

from modules.cv_tools import DatasetCleaner
from routes.utils import get_json_body, require_values, error_response


def create_clean_blueprint(task_manager):
    bp = Blueprint('clean', __name__)

    @bp.route('/api/clean-dataset', methods=['POST'])
    def clean_dataset():
        try:
            data = get_json_body()

            images_dir = data.get('images_dir')
            labels_dir = data.get('labels_dir')
            output_dir = data.get('output_dir')
            dry_run = data.get('dry_run', False)
            ok, resp = require_values(data, [
                ('images_dir', 'Missing required fields: images_dir, labels_dir, or output_dir'),
                ('labels_dir', 'Missing required fields: images_dir, labels_dir, or output_dir'),
                ('output_dir', 'Missing required fields: images_dir, labels_dir, or output_dir'),
            ])
            if not ok:
                return resp

            def run_cleaning(task_id, cancel_event, pause_event):
                cleaner = DatasetCleaner()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = cleaner.clean(images_dir, labels_dir, output_dir, dry_run, progress_callback=progress_callback)

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Cleaning completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting cleaning...',
                run_fn=run_cleaning
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
