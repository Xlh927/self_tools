import os
from flask import Blueprint, jsonify, request, send_file

from modules.viewer import viewer_manager
from routes.utils import get_json_body, require_value, require_exists, error_response


def create_viewer_blueprint():
    bp = Blueprint('viewer', __name__, url_prefix='/api/viewer')

    @bp.route('/config', methods=['GET', 'POST'])
    def viewer_config():
        if request.method == 'POST':
            return jsonify(viewer_manager.update_config(request.get_json()))
        return jsonify(viewer_manager.get_config())

    @bp.route('/classify', methods=['POST'])
    def viewer_classify():
        data = get_json_body()
        ok, resp = require_value(data, 'image_path', 'Missing image_path')
        if not ok:
            return resp
        ok, resp = require_value(data, 'class_name', 'Missing class_name')
        if not ok:
            return resp
        result = viewer_manager.classify_image(data.get('image_path'), data.get('class_name'))
        return jsonify(result)

    @bp.route('/unclassify', methods=['POST'])
    def viewer_unclassify():
        data = get_json_body()
        ok, resp = require_value(data, 'image_path', 'Missing image_path')
        if not ok:
            return resp
        ok, resp = require_value(data, 'class_name', 'Missing class_name')
        if not ok:
            return resp
        result = viewer_manager.unclassify_image(data.get('image_path'), data.get('class_name'))
        return jsonify(result)

    @bp.route('/images')
    def viewer_list_images():
        path = request.args.get('path')
        if not path:
            return error_response('Missing path', code='ERR_MISSING_FIELD')
        sort = request.args.get('sort', 'name_desc')
        result = viewer_manager.list_images(path, sort)
        return jsonify(result)

    @bp.route('/image')
    def viewer_get_image():
        path = request.args.get('path')
        if not path:
            return error_response('Missing path', status=400, code='ERR_MISSING_FIELD')
        ok, resp = require_exists(path, 'Image not found', status=404, code='ERR_PATH_NOT_FOUND')
        if not ok:
            return resp
        return send_file(path)

    @bp.route('/thumbnail')
    def viewer_get_thumbnail():
        path = request.args.get('path')
        if not path:
            return error_response('Missing path', status=400, code='ERR_MISSING_FIELD')
        size = int(request.args.get('size', 300))
        thumb_path = viewer_manager.get_thumbnail_path(path, size)
        if not thumb_path:
            return error_response('Thumbnail failed', status=500, code='ERR_THUMBNAIL_FAILED')
        return send_file(thumb_path, mimetype='image/jpeg')

    @bp.route('/thumbnails', methods=['DELETE'])
    def viewer_clear_thumbnails():
        return jsonify(viewer_manager.clear_thumbnails())

    @bp.route('/thumbnail-stats')
    def viewer_get_thumbnail_stats():
        return jsonify(viewer_manager.get_thumbnail_stats())

    return bp
