from flask import Blueprint, request, send_file

from modules.viewer import viewer_manager
from routes.utils import (
    ValidationError,
    error_response,
    handle_validation_error,
    parse_args_request,
    parse_json_request,
    success_response,
)


def create_viewer_blueprint():
    bp = Blueprint('viewer', __name__, url_prefix='/api/viewer')

    @bp.route('/config', methods=['GET', 'POST'])
    def viewer_config():
        try:
            if request.method == 'POST':
                data = parse_json_request()
                updated = viewer_manager.update_config(data)
                return success_response(updated, message='Viewer config updated')
            return success_response(viewer_manager.get_config(), message='Viewer config fetched')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/classify', methods=['POST'])
    def viewer_classify():
        try:
            data = parse_json_request(required=['image_path', 'class_name'])
            result = viewer_manager.classify_image(data.get('image_path'), data.get('class_name'))
            if result.get('success'):
                return success_response(result, message='Image classified')
            return error_response(result.get('error', 'Classification failed'), code='ERR_VIEWER_CLASSIFY_FAILED')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/unclassify', methods=['POST'])
    def viewer_unclassify():
        try:
            data = parse_json_request(required=['image_path', 'class_name'])
            result = viewer_manager.unclassify_image(data.get('image_path'), data.get('class_name'))
            if result.get('success'):
                return success_response(result, message='Classification removed')
            return error_response(result.get('error', 'Unclassify failed'), code='ERR_VIEWER_UNCLASSIFY_FAILED')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/images')
    def viewer_list_images():
        try:
            args = parse_args_request(required=['path'], defaults={'sort': 'name_desc'})
            result = viewer_manager.list_images(args['path'], args.get('sort', 'name_desc'))
            if result.get('success'):
                return success_response(result, message='Images listed')
            return error_response(result.get('error', 'List images failed'), code='ERR_VIEWER_LIST_FAILED')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/image')
    def viewer_get_image():
        try:
            args = parse_args_request(required=['path'])
            path = args['path']
            if not path:
                raise ValidationError('Missing path', code='ERR_MISSING_FIELD')
            return send_file(path)
        except ValidationError as e:
            return handle_validation_error(e)
        except FileNotFoundError:
            return error_response('Image not found', status=404, code='ERR_PATH_NOT_FOUND')
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/thumbnail')
    def viewer_get_thumbnail():
        try:
            args = parse_args_request(required=['path'], defaults={'size': '300'})
            path = args['path']
            size = int(args.get('size', '300'))
            thumb_path = viewer_manager.get_thumbnail_path(path, size)
            if not thumb_path:
                return error_response('Thumbnail failed', status=500, code='ERR_THUMBNAIL_FAILED')
            return send_file(thumb_path, mimetype='image/jpeg')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/thumbnails', methods=['DELETE'])
    def viewer_clear_thumbnails():
        result = viewer_manager.clear_thumbnails()
        if result.get('success'):
            return success_response(result, message='Thumbnail cache cleared')
        return error_response(result.get('error', 'Clear thumbnails failed'), code='ERR_THUMBNAIL_CLEAR_FAILED')

    @bp.route('/thumbnail-stats')
    def viewer_get_thumbnail_stats():
        result = viewer_manager.get_thumbnail_stats()
        if result.get('success'):
            return success_response(result, message='Thumbnail stats fetched')
        return error_response(result.get('error', 'Get thumbnail stats failed'), code='ERR_THUMBNAIL_STATS_FAILED')

    return bp
