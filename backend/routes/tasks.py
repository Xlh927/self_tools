from flask import Blueprint, jsonify

from routes.utils import error_response


def create_tasks_blueprint(task_manager):
    bp = Blueprint('tasks', __name__)

    @bp.route('/api/progress/<task_id>')
    def get_progress(task_id):
        task = task_manager.get_task(task_id)
        if not task:
            return error_response('Task not found', status=404, code='ERR_TASK_NOT_FOUND')
        return jsonify(task)

    @bp.route('/api/task/<task_id>/pause', methods=['POST'])
    def pause_task(task_id):
        if task_manager.pause_task(task_id):
            return jsonify({'success': True, 'message': 'Task paused'})
        return error_response('Task not found or not controllable', status=404, code='ERR_TASK_NOT_FOUND')

    @bp.route('/api/task/<task_id>/resume', methods=['POST'])
    def resume_task(task_id):
        if task_manager.resume_task(task_id):
            return jsonify({'success': True, 'message': 'Task resumed'})
        return error_response('Task not found or not controllable', status=404, code='ERR_TASK_NOT_FOUND')

    @bp.route('/api/task/<task_id>/stop', methods=['POST'])
    def stop_task(task_id):
        if task_manager.stop_task(task_id):
            return jsonify({'success': True, 'message': 'Task cancellation requested'})
        return error_response('Task not found or not cancellable', status=404, code='ERR_TASK_NOT_FOUND')

    @bp.route('/api/stop-task/<task_id>', methods=['POST'])
    def stop_task_legacy(task_id):
        if task_manager.stop_task(task_id):
            return jsonify({'success': True, 'message': 'Task cancellation requested'})
        return error_response('Task not found or not cancellable', status=404, code='ERR_TASK_NOT_FOUND')

    return bp
