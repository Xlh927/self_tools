from flask import Blueprint, jsonify, request

from routes.utils import get_json_body, require_values, error_response

from modules.cv_tools import ImageMatcher


def create_match_blueprint(task_manager):
    bp = Blueprint('match', __name__)

    @bp.route('/api/match', methods=['POST'])
    def match_images():
        try:
            data = get_json_body()
            ok, resp = require_values(data, [
                ('source_dir', 'Missing source_dir'),
                ('reference_dir', 'Missing reference_dir'),
                ('output_dir', 'Missing output_dir'),
            ])
            if not ok:
                return resp

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
                run_fn=run_matching
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
