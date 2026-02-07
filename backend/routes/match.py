from flask import Blueprint

from modules.cv_tools import ImageMatcher
from routes.utils import (
    ValidationError,
    error_response,
    handle_validation_error,
    parse_json_request,
    task_queued_response,
)


def create_match_blueprint(task_manager):
    bp = Blueprint('match', __name__)

    @bp.route('/api/match', methods=['POST'])
    def match_images():
        try:
            data = parse_json_request(
                required=['source_dir', 'reference_dir', 'output_dir'],
                exists=['source_dir', 'reference_dir'],
                dirs=['source_dir', 'reference_dir'],
                defaults={'copy_intersection': True, 'copy_difference': False, 'dry_run': False, 'max_retries': 1},
                coerce={'max_retries': int},
            )

            def run_matching(task_id, cancel_event, pause_event):
                matcher = ImageMatcher()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = matcher.match_and_copy(
                    source_dir=data['source_dir'],
                    reference_dir=data['reference_dir'],
                    output_dir=data['output_dir'],
                    copy_intersection=data.get('copy_intersection', True),
                    copy_difference=data.get('copy_difference', False),
                    dry_run=data.get('dry_run', False),
                    progress_callback=progress_callback
                )

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Matching completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting matching...',
                run_fn=run_matching,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Matching task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
