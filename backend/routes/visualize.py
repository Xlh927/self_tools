from flask import Blueprint

from modules.cv_tools import AnnotationVisualizer
from routes.utils import (
    ValidationError,
    error_response,
    handle_validation_error,
    parse_json_request,
    success_response,
    task_queued_response,
)


def create_visualize_blueprint(task_manager):
    bp = Blueprint('visualize', __name__)

    @bp.route('/api/detect-classes', methods=['POST'])
    def detect_classes():
        try:
            data = parse_json_request(required=['annotations_dir'], exists=['annotations_dir'], dirs=['annotations_dir'])

            visualizer = AnnotationVisualizer()
            result = visualizer.detect_classes(
                annotations_dir=data['annotations_dir'],
                annotation_format=data.get('annotation_format')
            )
            if result.get('success'):
                return success_response(result, message='Classes detected')
            return error_response(result.get('error', 'Class detection failed'), code='ERR_CLASS_SCAN_FAILED')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/visualize', methods=['POST'])
    def visualize_annotations():
        try:
            data = parse_json_request(
                required=['images_dir', 'annotations_dir', 'output_dir'],
                exists=['images_dir', 'annotations_dir'],
                dirs=['images_dir', 'annotations_dir'],
                defaults={'max_retries': 1},
                coerce={'max_retries': int},
            )

            def run_visualization(task_id, cancel_event, pause_event):
                visualizer = AnnotationVisualizer()
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                result = visualizer.visualize(
                    data,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event
                )

                status = 'cancelled' if not result['success'] and result.get('error') == 'Operation cancelled by user' else 'completed'
                if not result['success'] and status != 'cancelled':
                    status = 'error'

                task_manager.finish_task(
                    task_id,
                    status=status,
                    message='Visualization completed' if status == 'completed' else f"Visualization {status}",
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting visualization...',
                run_fn=run_visualization,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Visualization task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
