from flask import Blueprint

from modules.cv_tools import ImageMatcher
from routes.utils import (
    queue_json_task,
    run_with_error_handling,
)


def create_match_blueprint(task_manager):
    bp = Blueprint('match', __name__)

    @bp.route('/api/match', methods=['POST'])
    def match_images():
        def _handle():
            def _work(data, _task_id, _cancel_event, _pause_event, progress_callback):
                matcher = ImageMatcher()
                return matcher.match_and_copy(
                    source_dir=data['source_dir'],
                    reference_dir=data['reference_dir'],
                    output_dir=data['output_dir'],
                    copy_intersection=data.get('copy_intersection', True),
                    copy_difference=data.get('copy_difference', False),
                    dry_run=data.get('dry_run', False),
                    progress_callback=progress_callback,
                )

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['source_dir', 'reference_dir', 'output_dir'],
                    'exists': ['source_dir', 'reference_dir'],
                    'dirs': ['source_dir', 'reference_dir'],
                    'defaults': {'copy_intersection': True, 'copy_difference': False, 'dry_run': False},
                },
                start_message='Starting matching...',
                queued_message='Matching task queued',
                success_message='Matching completed',
                work_fn=_work,
            )

        return run_with_error_handling(_handle)

    return bp
