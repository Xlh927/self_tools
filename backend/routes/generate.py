from flask import Blueprint

from modules.cv_tools import DatasetGenerator
from routes.utils import (
    ValidationError,
    error_response,
    handle_validation_error,
    parse_json_request,
    task_queued_response,
)


def create_generate_blueprint(task_manager):
    bp = Blueprint('generate', __name__)

    @bp.route('/api/generate', methods=['POST'])
    def generate():
        try:
            data = parse_json_request(
                required=['annotation_format', 'images_dir', 'annotations_dir', 'output_dir'],
                exists=['images_dir', 'annotations_dir'],
                dirs=['images_dir', 'annotations_dir'],
                defaults={'max_retries': 1},
                coerce={'max_retries': int},
            )

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
                run_fn=run_generation,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Generation task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
