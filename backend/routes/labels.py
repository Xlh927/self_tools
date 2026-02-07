from flask import Blueprint

from modules.cv_tools import LabelModifier
from routes.utils import (
    error_response,
    queue_json_task,
    parse_json_request,
    run_with_error_handling,
    success_response,
)


def create_labels_blueprint(task_manager):
    bp = Blueprint('labels', __name__)

    @bp.route('/api/scan-yolo-classes', methods=['POST'])
    def scan_yolo_classes():
        def _handle():
            data = parse_json_request(required=['label_dir'], exists=['label_dir'], dirs=['label_dir'])
            modifier = LabelModifier()
            result = modifier.scan_classes(data['label_dir'])
            if result.get('success'):
                return success_response(result, message='YOLO classes scanned')
            return error_response(result.get('error', 'Scan failed'), code='ERR_CLASS_SCAN_FAILED')
        return run_with_error_handling(_handle)

    @bp.route('/api/modify-labels', methods=['POST'])
    def modify_labels():
        def _handle():
            def _work(data, _task_id, _cancel_event, _pause_event, progress_callback):
                modifier = LabelModifier()
                return modifier.modify_labels(
                    label_dir=data['label_dir'],
                    class_mapping=data['class_mapping'],
                    overwrite=data.get('overwrite', False),
                    output_dir=data.get('output_dir'),
                    progress_callback=progress_callback,
                )

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['label_dir', 'class_mapping'],
                    'exists': ['label_dir'],
                    'dirs': ['label_dir'],
                    'defaults': {'overwrite': False},
                },
                start_message='Starting label modification...',
                queued_message='Label modification task queued',
                success_message='Modification completed',
                work_fn=_work,
            )

        return run_with_error_handling(_handle)

    return bp
