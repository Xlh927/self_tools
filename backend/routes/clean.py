from flask import Blueprint

from modules.cv_tools import DatasetCleaner
from routes.utils import (
    ValidationError,
    error_response,
    handle_validation_error,
    parse_json_request,
    task_queued_response,
)


def create_clean_blueprint(task_manager):
    bp = Blueprint('clean', __name__)

    @bp.route('/api/clean-dataset', methods=['POST'])
    def clean_dataset():
        try:
            data = parse_json_request(
                required=['images_dir', 'labels_dir', 'output_dir'],
                exists=['images_dir', 'labels_dir'],
                dirs=['images_dir', 'labels_dir'],
                defaults={'dry_run': False, 'max_retries': 1},
                coerce={'max_retries': int},
            )

            def run_cleaning(task_id, cancel_event, pause_event):
                cleaner = DatasetCleaner()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = cleaner.clean(
                    data['images_dir'],
                    data['labels_dir'],
                    data['output_dir'],
                    data.get('dry_run', False),
                    progress_callback=progress_callback,
                )

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Cleaning completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting cleaning...',
                run_fn=run_cleaning,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Cleaning task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
