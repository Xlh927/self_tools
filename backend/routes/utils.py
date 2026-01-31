import os
from flask import jsonify, request


def error_response(message, status=400, code='ERR_BAD_REQUEST'):
    return jsonify({'success': False, 'error': message, 'error_code': code}), status


def get_json_body():
    return request.get_json(silent=True) or {}


def require_value(data, key, message, status=400, code='ERR_MISSING_FIELD'):
    if key not in data or not data[key]:
        return False, error_response(message, status=status, code=code)
    return True, None


def require_values(data, required, code='ERR_MISSING_FIELD'):
    """
    required: list of tuples (key, message)
    """
    for key, message in required:
        ok, resp = require_value(data, key, message, code=code)
        if not ok:
            return False, resp
    return True, None


def require_exists(path, message, status=400, code='ERR_PATH_NOT_FOUND'):
    if not os.path.exists(path):
        return False, error_response(message, status=status, code=code)
    return True, None


def require_dir(path, message, status=400, code='ERR_NOT_A_DIRECTORY'):
    if not os.path.isdir(path):
        return False, error_response(message, status=status, code=code)
    return True, None
