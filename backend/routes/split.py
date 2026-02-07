from flask import Blueprint

from modules.cv_tools import DatasetSplitter
from routes.utils import (
    ValidationError,
    error_response,
    finish_task_from_result,
    handle_validation_error,
    parse_json_request,
    task_queued_response,
)


def create_split_blueprint(task_manager):
    bp = Blueprint('split', __name__)

    @bp.route('/api/split', methods=['POST'])
    def split():
        try:
            data = parse_json_request(
                required=['format', 'images_dir', 'annotations_dir', 'output_dir'],
                exists=['images_dir', 'annotations_dir'],
                dirs=['images_dir', 'annotations_dir'],
                defaults={'max_retries': 1},
                coerce={'max_retries': int},
            )

            def run_splitting(task_id, cancel_event, pause_event):
                splitter = DatasetSplitter()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)
                result = splitter.split_dataset(data, progress_callback=progress_callback)

                finish_task_from_result(
                    task_manager,
                    task_id,
                    result,
                    'Splitting completed',
                )

            task_id = task_manager.start_task(
                message='Starting splitting...',
                run_fn=run_splitting,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Split task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
