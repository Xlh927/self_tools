from flask import Blueprint

from modules.cv_tools import DatasetCleaner
from routes.utils import (
    queue_json_task,
    run_with_error_handling,
)


def create_clean_blueprint(task_manager):
    bp = Blueprint('clean', __name__)

    @bp.route('/api/clean-dataset', methods=['POST'])
    def clean_dataset():
        def _handle():
            def _work(data, _task_id, _cancel_event, _pause_event, progress_callback):
                cleaner = DatasetCleaner()
                return cleaner.clean(
                    data['images_dir'],
                    data['labels_dir'],
                    data['output_dir'],
                    data.get('dry_run', False),
                    progress_callback=progress_callback,
                )

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['images_dir', 'labels_dir', 'output_dir'],
                    'exists': ['images_dir', 'labels_dir'],
                    'dirs': ['images_dir', 'labels_dir'],
                    'defaults': {'dry_run': False},
                },
                start_message='Starting cleaning...',
                queued_message='Cleaning task queued',
                success_message='Cleaning completed',
                work_fn=_work,
            )

        return run_with_error_handling(_handle)

    return bp
