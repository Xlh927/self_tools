from flask import Blueprint
from modules.cv_tools.pair_extractor import extract_pairs, validate_paths
from routes.utils import ValidationError, parse_json_request, queue_json_task, run_with_error_handling


def create_extract_blueprint(task_manager):
    bp = Blueprint('extract', __name__)

    @bp.route('/api/extract-pairs', methods=['POST'])
    def extract():
        def handle():
            data = parse_json_request(required=['source_dir', 'output_dir'])
            if not isinstance(data.get('dry_run', True), bool):
                raise ValidationError('dry_run 必须为布尔值')
            if not isinstance(data.get('split_by_ratio', False), bool):
                raise ValidationError('split_by_ratio 必须为布尔值')
            try:
                validate_paths(data['source_dir'], data['output_dir'])
            except (ValueError, TypeError) as exc:
                raise ValidationError(str(exc)) from exc

            def work(data, _task_id, _cancel, _pause, progress):
                return extract_pairs(data['source_dir'], data['output_dir'],
                                     data.get('dry_run', True), progress,
                                     split_by_ratio=data.get('split_by_ratio', False))

            return queue_json_task(task_manager,
                parse_kwargs={'required': ['source_dir', 'output_dir'], 'defaults': {'dry_run': True, 'split_by_ratio': False}},
                start_message='正在扫描图片/XML 配对...', queued_message='配对提取任务已排队',
                success_message='配对提取完成', work_fn=work)
        return run_with_error_handling(handle)
    return bp
