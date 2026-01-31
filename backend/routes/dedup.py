from flask import Blueprint, jsonify, request

from modules.cv_tools import ImageDeduplicator
from routes.utils import get_json_body, require_value, require_exists, require_dir, error_response


def create_dedup_blueprint(task_manager):
    bp = Blueprint('dedup', __name__)

    @bp.route('/api/find-duplicates', methods=['POST'])
    def find_duplicates():
        try:
            data = get_json_body()
            ok, resp = require_value(data, 'folder_path', 'Missing required field: folder_path')
            if not ok:
                return resp

            folder_path = data['folder_path']
            hash_algorithm = data.get('hash_algorithm', 'average')
            use_md5 = data.get('use_md5', False)
            similarity_threshold = int(data.get('similarity_threshold', 5))

            ok, resp = require_exists(folder_path, f'Folder does not exist: {folder_path}')
            if not ok:
                return resp
            ok, resp = require_dir(folder_path, f'Path is not a directory: {folder_path}')
            if not ok:
                return resp

            def run_deduplication(task_id, cancel_event, pause_event):
                deduplicator = ImageDeduplicator()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                duplicates = deduplicator.find_duplicates(
                    folder_path=folder_path,
                    hash_algorithm=hash_algorithm,
                    use_md5=use_md5,
                    similarity_threshold=similarity_threshold,
                    progress_callback=progress_callback
                )

                report = deduplicator.get_duplicate_report(duplicates)

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Scan completed',
                    result={'report': report}
                )

            task_id = task_manager.start_task(
                message='Scanning for duplicates...',
                run_fn=run_deduplication
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/remove-duplicates', methods=['POST'])
    def remove_duplicates():
        try:
            data = get_json_body()
            ok, resp = require_value(data, 'folder_path', 'Missing required field: folder_path')
            if not ok:
                return resp

            folder_path = data['folder_path']
            hash_algorithm = data.get('hash_algorithm', 'average')
            use_md5 = data.get('use_md5', False)
            similarity_threshold = int(data.get('similarity_threshold', 5))
            keep_strategy = data.get('keep_strategy', 'first')
            dry_run = data.get('dry_run', True)

            ok, resp = require_exists(folder_path, f'Folder does not exist: {folder_path}')
            if not ok:
                return resp

            deduplicator = ImageDeduplicator()

            if 'duplicates' in data and data['duplicates']:
                duplicates = data['duplicates']
            else:
                duplicates = deduplicator.find_duplicates(
                    folder_path=folder_path,
                    hash_algorithm=hash_algorithm,
                    use_md5=use_md5,
                    similarity_threshold=similarity_threshold
                )

            result = deduplicator.remove_duplicates(
                duplicates=duplicates,
                keep_strategy=keep_strategy,
                dry_run=dry_run
            )

            return jsonify({
                'success': True,
                **result
            })

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
