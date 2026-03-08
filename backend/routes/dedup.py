from flask import Blueprint

from modules.cv_tools import ImageDeduplicator
from routes.utils import (
    error_response,
    queue_json_task,
    parse_json_request,
    run_with_error_handling,
    success_response,
)


def create_dedup_blueprint(task_manager):
    bp = Blueprint('dedup', __name__)

    @bp.route('/api/find-duplicates', methods=['POST'])
    def find_duplicates():
        def _handle():
            def _work(data, _task_id, _cancel_event, _pause_event, progress_callback):
                deduplicator = ImageDeduplicator()
                duplicates = deduplicator.find_duplicates(
                    folder_path=data['folder_path'],
                    hash_algorithm=data.get('hash_algorithm', 'average'),
                    use_md5=data.get('use_md5', False),
                    similarity_threshold=data.get('similarity_threshold', 5),
                    progress_callback=progress_callback,
                )
                report = deduplicator.get_duplicate_report(duplicates)
                return {'success': True, 'report': report}

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['folder_path'],
                    'exists': ['folder_path'],
                    'dirs': ['folder_path'],
                    'defaults': {
                        'hash_algorithm': 'average',
                        'use_md5': False,
                        'similarity_threshold': 5,
                    },
                    'coerce': {'similarity_threshold': int},
                },
                start_message='Scanning for duplicates...',
                queued_message='Dedup scan task queued',
                success_message='Scan completed',
                work_fn=_work,
            )

        return run_with_error_handling(_handle)

    @bp.route('/api/remove-duplicates', methods=['POST'])
    def remove_duplicates():
        def _handle():
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
        return run_with_error_handling(_handle)

    return bp
