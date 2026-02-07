from flask import Blueprint

from modules.cv_tools import DatasetGenerator
from routes.utils import (
    queue_json_task,
    run_with_error_handling,
)


def create_generate_blueprint(task_manager):
    bp = Blueprint('generate', __name__)

    @bp.route('/api/generate', methods=['POST'])
    def generate():
        def _handle():
            def _work(data, _task_id, _cancel_event, _pause_event, progress_callback):
                generator = DatasetGenerator()
                return generator.generate_dataset(data, progress_callback=progress_callback)

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['annotation_format', 'images_dir', 'annotations_dir', 'output_dir'],
                    'exists': ['images_dir', 'annotations_dir'],
                    'dirs': ['images_dir', 'annotations_dir'],
                },
                start_message='Starting generation...',
                queued_message='Generation task queued',
                success_message='Generation completed',
                work_fn=_work,
            )

        return run_with_error_handling(_handle)

    return bp
