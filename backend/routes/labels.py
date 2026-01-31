from flask import Blueprint, jsonify, request

from modules.cv_tools import LabelModifier
from routes.utils import get_json_body, require_value, error_response


def create_labels_blueprint(task_manager):
    bp = Blueprint('labels', __name__)

    @bp.route('/api/scan-yolo-classes', methods=['POST'])
    def scan_yolo_classes():
        try:
            data = get_json_body()
            label_dir = data.get('label_dir')

            ok, resp = require_value(data, 'label_dir', 'Missing label_dir')
            if not ok:
                return resp

            modifier = LabelModifier()
            result = modifier.scan_classes(label_dir)

            return jsonify(result)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/modify-labels', methods=['POST'])
    def modify_labels():
        try:
            data = get_json_body()

            ok, resp = require_value(data, 'label_dir', 'Missing label_dir')
            if not ok:
                return resp
            ok, resp = require_value(data, 'class_mapping', 'Missing class_mapping')
            if not ok:
                return resp

            label_dir = data['label_dir']
            class_mapping = data['class_mapping']
            overwrite = data.get('overwrite', False)
            output_dir = data.get('output_dir')

            def run_modification(task_id, cancel_event, pause_event):
                modifier = LabelModifier()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = modifier.modify_labels(
                    label_dir=label_dir,
                    class_mapping=class_mapping,
                    overwrite=overwrite,
                    output_dir=output_dir,
                    progress_callback=progress_callback
                )

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Modification completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting label modification...',
                run_fn=run_modification
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
