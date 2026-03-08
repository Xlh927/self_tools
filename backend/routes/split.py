from flask import Blueprint

from modules.cv_tools import DatasetSplitter
from routes.utils import (
    queue_json_task,
    run_with_error_handling,
)


def create_split_blueprint(task_manager):
    bp = Blueprint('split', __name__)

    @bp.route('/api/split', methods=['POST'])
    def split():
        def _handle():
            def _work(data, _task_id, _cancel_event, _pause_event, progress_callback):
                splitter = DatasetSplitter()
                return splitter.split_dataset(data, progress_callback=progress_callback)

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['format', 'images_dir', 'annotations_dir', 'output_dir'],
                    'exists': ['images_dir', 'annotations_dir'],
                    'dirs': ['images_dir', 'annotations_dir'],
                },
                start_message='Starting splitting...',
                queued_message='Split task queued',
                success_message='Splitting completed',
                work_fn=_work,
            )

        return run_with_error_handling(_handle)

    return bp
