from flask import Blueprint

from modules.cv_tools import LabelModifier
from routes.utils import (
    ValidationError,
    error_response,
    handle_validation_error,
    parse_json_request,
    success_response,
    task_queued_response,
)


def create_labels_blueprint(task_manager):
    bp = Blueprint('labels', __name__)

    @bp.route('/api/scan-yolo-classes', methods=['POST'])
    def scan_yolo_classes():
        try:
            data = parse_json_request(required=['label_dir'], exists=['label_dir'], dirs=['label_dir'])
            modifier = LabelModifier()
            result = modifier.scan_classes(data['label_dir'])
            if result.get('success'):
                return success_response(result, message='YOLO classes scanned')
            return error_response(result.get('error', 'Scan failed'), code='ERR_CLASS_SCAN_FAILED')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/modify-labels', methods=['POST'])
    def modify_labels():
        try:
            data = parse_json_request(
                required=['label_dir', 'class_mapping'],
                exists=['label_dir'],
                dirs=['label_dir'],
                defaults={'overwrite': False, 'max_retries': 1},
                coerce={'max_retries': int},
            )

            def run_modification(task_id, cancel_event, pause_event):
                modifier = LabelModifier()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = modifier.modify_labels(
                    label_dir=data['label_dir'],
                    class_mapping=data['class_mapping'],
                    overwrite=data.get('overwrite', False),
                    output_dir=data.get('output_dir'),
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
                run_fn=run_modification,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Label modification task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
