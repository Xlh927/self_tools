from flask import Blueprint

from modules.cv_tools import ImageDeduplicator
from routes.utils import (
    ValidationError,
    error_response,
    finish_task_from_result,
    handle_validation_error,
    parse_json_request,
    success_response,
    task_queued_response,
)


def create_dedup_blueprint(task_manager):
    bp = Blueprint('dedup', __name__)

    @bp.route('/api/find-duplicates', methods=['POST'])
    def find_duplicates():
        try:
            data = parse_json_request(
                required=['folder_path'],
                exists=['folder_path'],
                dirs=['folder_path'],
                defaults={
                    'hash_algorithm': 'average',
                    'use_md5': False,
                    'similarity_threshold': 5,
                    'max_retries': 1,
                },
                coerce={'similarity_threshold': int, 'max_retries': int},
            )

            def run_deduplication(task_id, cancel_event, pause_event):
                deduplicator = ImageDeduplicator()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                duplicates = deduplicator.find_duplicates(
                    folder_path=data['folder_path'],
                    hash_algorithm=data.get('hash_algorithm', 'average'),
                    use_md5=data.get('use_md5', False),
                    similarity_threshold=data.get('similarity_threshold', 5),
                    progress_callback=progress_callback
                )

                report = deduplicator.get_duplicate_report(duplicates)
                finish_task_from_result(
                    task_manager,
                    task_id,
                    {'success': True, 'report': report},
                    'Scan completed',
                )

            task_id = task_manager.start_task(
                message='Scanning for duplicates...',
                run_fn=run_deduplication,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Dedup scan task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/remove-duplicates', methods=['POST'])
    def remove_duplicates():
        try:
            data = parse_json_request(
                required=['folder_path'],
                exists=['folder_path'],
                defaults={
                    'hash_algorithm': 'average',
                    'use_md5': False,
                    'similarity_threshold': 5,
                    'keep_strategy': 'first',
                    'dry_run': True,
                },
                coerce={'similarity_threshold': int},
            )
            deduplicator = ImageDeduplicator()

            if data.get('duplicates'):
                duplicates = data['duplicates']
            else:
                duplicates = deduplicator.find_duplicates(
                    folder_path=data['folder_path'],
                    hash_algorithm=data.get('hash_algorithm', 'average'),
                    use_md5=data.get('use_md5', False),
                    similarity_threshold=data.get('similarity_threshold', 5),
                )

            result = deduplicator.remove_duplicates(
                duplicates=duplicates,
                keep_strategy=data.get('keep_strategy', 'first'),
                dry_run=data.get('dry_run', True)
            )
            merged = {'success': True, **result}
            return success_response(merged, message='Duplicate removal done')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
