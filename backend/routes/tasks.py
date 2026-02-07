import json
import time

from flask import Blueprint, Response, stream_with_context

from routes.utils import (
    error_response,
    parse_args_request,
    success_response,
    ValidationError,
    handle_validation_error,
)


def create_tasks_blueprint(task_manager):
    bp = Blueprint('tasks', __name__)
    terminal_statuses = {'completed', 'error', 'stopped', 'cancelled'}

    @bp.route('/api/progress/<task_id>')
    def get_progress(task_id):
        task = task_manager.get_task(task_id)
        if not task:
            return error_response('Task not found', status=404, code='ERR_TASK_NOT_FOUND')
        return success_response(task, message='Task fetched')

    @bp.route('/api/task/<task_id>/stream')
    def stream_progress(task_id):
        task = task_manager.get_task(task_id)
        if not task:
            return error_response('Task not found', status=404, code='ERR_TASK_NOT_FOUND')

        interval_seconds = 0.5

        def generate():
            last_payload = None
            last_ping_at = time.time()
            while True:
                current = task_manager.get_task(task_id)
                if not current:
                    payload = {
                        'task_id': task_id,
                        'status': 'error',
                        'error': 'Task not found',
                        'error_code': 'ERR_TASK_NOT_FOUND',
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break

                if current != last_payload:
                    yield f"data: {json.dumps(current, ensure_ascii=False)}\n\n"
                    last_payload = current
                    last_ping_at = time.time()
                elif time.time() - last_ping_at >= 15:
                    # Keep-alive comment for proxies and browsers.
                    yield ': keep-alive\n\n'
                    last_ping_at = time.time()

                if current.get('status') in terminal_statuses:
                    break

                time.sleep(interval_seconds)

        response = Response(stream_with_context(generate()), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['X-Accel-Buffering'] = 'no'
        return response

    @bp.route('/api/tasks')
    def list_tasks():
        try:
            args = parse_args_request(defaults={'limit': '100'})
            try:
                limit = int(args.get('limit', 100))
            except Exception:
                raise ValidationError('Invalid limit', code='ERR_INVALID_FIELD', status=400)
            status = args.get('status')
            tasks = task_manager.list_tasks(limit=limit, status=status)
            return success_response({'tasks': tasks}, message='Task list fetched')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/task/<task_id>/history')
    def task_history(task_id):
        try:
            args = parse_args_request(defaults={'limit': '200'})
            try:
                limit = int(args.get('limit', 200))
            except Exception:
                raise ValidationError('Invalid limit', code='ERR_INVALID_FIELD', status=400)
            if not task_manager.get_task(task_id):
                return error_response('Task not found', status=404, code='ERR_TASK_NOT_FOUND')
            events = task_manager.get_task_events(task_id, limit=limit)
            return success_response({'task_id': task_id, 'events': events}, message='Task history fetched')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/task/<task_id>/pause', methods=['POST'])
    def pause_task(task_id):
        if task_manager.pause_task(task_id):
            task = task_manager.get_task(task_id)
            return success_response(task, message='Task paused')
        return error_response('Task not found or not controllable', status=404, code='ERR_TASK_NOT_FOUND')

    @bp.route('/api/task/<task_id>/resume', methods=['POST'])
    def resume_task(task_id):
        if task_manager.resume_task(task_id):
            task = task_manager.get_task(task_id)
            return success_response(task, message='Task resumed')
        return error_response('Task not found or not controllable', status=404, code='ERR_TASK_NOT_FOUND')

    @bp.route('/api/task/<task_id>/stop', methods=['POST'])
    def stop_task(task_id):
        if task_manager.stop_task(task_id):
            task = task_manager.get_task(task_id)
            return success_response(task, message='Task cancellation requested')
        return error_response('Task not found or not cancellable', status=404, code='ERR_TASK_NOT_FOUND')

    @bp.route('/api/task/<task_id>/retry', methods=['POST'])
    def retry_task(task_id):
        if task_manager.retry_task_now(task_id):
            task = task_manager.get_task(task_id)
            return success_response(task, message='Task retry queued')
        return error_response('Task not retryable', status=400, code='ERR_TASK_NOT_RETRYABLE')

    @bp.route('/api/stop-task/<task_id>', methods=['POST'])
    def stop_task_legacy(task_id):
        if task_manager.stop_task(task_id):
            task = task_manager.get_task(task_id)
            return success_response(task, message='Task cancellation requested')
        return error_response('Task not found or not cancellable', status=404, code='ERR_TASK_NOT_FOUND')

    return bp
