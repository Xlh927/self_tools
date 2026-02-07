from flask import Blueprint

from modules.cv_tools import DataAugmentor
from routes.utils import (
    queue_json_task,
    run_with_error_handling,
)


def create_augment_blueprint(task_manager):
    bp = Blueprint('augment', __name__)

    @bp.route('/api/augment', methods=['POST'])
    def augment_dataset():
        def _handle():
            def _work(data, _task_id, _cancel_event, _pause_event, progress_callback):
                augmentor = DataAugmentor()
                return augmentor.augment_dataset(
                    config=data,
                    progress_callback=progress_callback,
                )

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['images_dir', 'annotations_dir', 'output_dir', 'annotation_format'],
                    'exists': ['images_dir', 'annotations_dir'],
                    'dirs': ['images_dir', 'annotations_dir'],
                },
                start_message='Starting augmentation...',
                queued_message='Augmentation task queued',
                success_message='Augmentation completed',
                work_fn=_work,
            )

        return run_with_error_handling(_handle)

    return bp
