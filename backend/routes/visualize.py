from flask import Blueprint

from modules.cv_tools import AnnotationVisualizer
from routes.utils import (
    error_response,
    queue_json_task,
    parse_json_request,
    run_with_error_handling,
    success_response,
)


def create_visualize_blueprint(task_manager):
    bp = Blueprint('visualize', __name__)

    @bp.route('/api/detect-classes', methods=['POST'])
    def detect_classes():
        def _handle():
            data = parse_json_request(required=['annotations_dir'], exists=['annotations_dir'], dirs=['annotations_dir'])

            visualizer = AnnotationVisualizer()
            result = visualizer.detect_classes(
                annotations_dir=data['annotations_dir'],
                annotation_format=data.get('annotation_format')
            )
            if result.get('success'):
                return success_response(result, message='Classes detected')
            return error_response(result.get('error', 'Class detection failed'), code='ERR_CLASS_SCAN_FAILED')
        return run_with_error_handling(_handle)

    @bp.route('/api/visualize', methods=['POST'])
    def visualize_annotations():
        def _handle():
            def _work(data, _task_id, cancel_event, _pause_event, progress_callback):
                visualizer = AnnotationVisualizer()
                return visualizer.visualize(
                    data,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event,
                )

            def _finalize(task_manager, task_id, result):
                cancelled = isinstance(result, dict) and not result.get('success') and result.get('error') == 'Operation cancelled by user'
                if cancelled:
                    task_manager.finish_task(
                        task_id,
                        status='cancelled',
                        message='Visualization cancelled',
                        result=result,
                        error_code='ERR_TASK_CANCELLED',
                    )
                    return
                if isinstance(result, dict) and not result.get('success'):
                    error_message = result.get('error') or 'Visualization failed'
                    task_manager.finish_task(
                        task_id,
                        status='error',
                        message=error_message,
                        result=result,
                        error=error_message,
                        error_code=result.get('error_code') or 'ERR_TASK_FAILED',
                    )
                    return
                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Visualization completed',
                    result=result,
                )

            return queue_json_task(
                task_manager,
                parse_kwargs={
                    'required': ['images_dir', 'annotations_dir', 'output_dir'],
                    'exists': ['images_dir', 'annotations_dir'],
                    'dirs': ['images_dir', 'annotations_dir'],
                },
                start_message='Starting visualization...',
                queued_message='Visualization task queued',
                success_message='Visualization completed',
                work_fn=_work,
                finalize_fn=_finalize,
            )

        return run_with_error_handling(_handle)

    return bp
