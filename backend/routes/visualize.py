from flask import Blueprint, jsonify, request

from modules.cv_tools import AnnotationVisualizer
from routes.utils import get_json_body, require_value, require_values, error_response


def create_visualize_blueprint(task_manager):
    bp = Blueprint('visualize', __name__)

    @bp.route('/api/detect-classes', methods=['POST'])
    def detect_classes():
        try:
            data = get_json_body()
            ok, resp = require_value(data, 'annotations_dir', 'Missing annotations_dir')
            if not ok:
                return resp

            visualizer = AnnotationVisualizer()
            result = visualizer.detect_classes(
                annotations_dir=data['annotations_dir'],
                annotation_format=data.get('annotation_format')
            )

            return jsonify(result)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/visualize', methods=['POST'])
    def visualize_annotations():
        try:
            data = get_json_body()
            ok, resp = require_values(data, [
                ('images_dir', 'Missing images_dir'),
                ('annotations_dir', 'Missing annotations_dir'),
                ('output_dir', 'Missing output_dir'),
            ])
            if not ok:
                return resp

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
                run_fn=run_visualization
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
