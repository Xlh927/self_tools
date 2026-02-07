import os
from typing import Any, Dict, Iterable, Optional

from flask import jsonify, request


class ValidationError(Exception):
    def __init__(self, message: str, code: str = "ERR_BAD_REQUEST", status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def success_response(data: Optional[dict] = None, message: str = "OK", status: int = 200, flatten: bool = True):
    payload: Dict[str, Any] = {
        "success": True,
        "message": message,
        "data": data or {},
    }
    if flatten and isinstance(data, dict):
        payload.update(data)
    return jsonify(payload), status


def error_response(message, status=400, code="ERR_BAD_REQUEST", details: Optional[dict] = None):
    payload: Dict[str, Any] = {
        "success": False,
        "error": message,
        "message": message,
        "error_code": code,
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status


def get_json_body():
    return request.get_json(silent=True) or {}


def parse_json_request(
    *,
    required: Optional[Iterable[str]] = None,
    defaults: Optional[dict] = None,
    exists: Optional[Iterable[str]] = None,
    dirs: Optional[Iterable[str]] = None,
    files: Optional[Iterable[str]] = None,
    coerce: Optional[dict] = None,
) -> dict:
    data = get_json_body()
    required = list(required or [])
    defaults = dict(defaults or {})
    exists = list(exists or [])
    dirs = list(dirs or [])
    files = list(files or [])
    coerce = dict(coerce or {})

    for key, value in defaults.items():
        data.setdefault(key, value)

    for key in required:
        if key not in data or data[key] in (None, ""):
            raise ValidationError(f"Missing required field: {key}", code="ERR_MISSING_FIELD", status=400)

    for key, cast in coerce.items():
        if key in data and data[key] not in (None, ""):
            try:
                data[key] = cast(data[key])
            except Exception:
                raise ValidationError(f"Invalid value for {key}", code="ERR_INVALID_FIELD", status=400)

    for key in exists:
        value = data.get(key)
        if value in (None, ""):
            continue
        if not os.path.exists(value):
            raise ValidationError(f"Path does not exist: {value}", code="ERR_PATH_NOT_FOUND", status=400)

    for key in dirs:
        value = data.get(key)
        if value in (None, ""):
            continue
        if not os.path.isdir(value):
            raise ValidationError(f"Path is not a directory: {value}", code="ERR_NOT_A_DIRECTORY", status=400)

    for key in files:
        value = data.get(key)
        if value in (None, ""):
            continue
        if not os.path.isfile(value):
            raise ValidationError(f"Path is not a file: {value}", code="ERR_NOT_A_FILE", status=400)

    return data


def parse_args_request(*, required: Optional[Iterable[str]] = None, defaults: Optional[dict] = None) -> dict:
    data = dict(request.args)
    required = list(required or [])
    defaults = dict(defaults or {})
    for key, value in defaults.items():
        data.setdefault(key, value)
    for key in required:
        if key not in data or data[key] in (None, ""):
            raise ValidationError(f"Missing required field: {key}", code="ERR_MISSING_FIELD", status=400)
    return data


def task_queued_response(task_id: str, message: str = "Task queued"):
    return success_response(
        data={"task_id": task_id, "status": "queued"},
        message=message,
        status=202,
    )


def finish_task_from_result(
    task_manager,
    task_id: str,
    result: Any,
    success_message: str,
    *,
    fallback_error_code: str = "ERR_TASK_FAILED",
) -> None:
    if isinstance(result, dict) and result.get("success") is False:
        error_message = result.get("error") or "Task failed"
        task_manager.finish_task(
            task_id,
            status="error",
            message=error_message,
            result=result,
            error=error_message,
            error_code=result.get("error_code") or fallback_error_code,
        )
        return

    task_manager.finish_task(
        task_id,
        status="completed",
        message=success_message,
        result=result,
    )


def handle_validation_error(exc: ValidationError):
    return error_response(exc.message, status=exc.status, code=exc.code)


# Backward-compatible helpers
def require_value(data, key, message, status=400, code="ERR_MISSING_FIELD"):
    if key not in data or data[key] in (None, ""):
        return False, error_response(message, status=status, code=code)
    return True, None


def require_values(data, required, code="ERR_MISSING_FIELD"):
    for key, message in required:
        ok, resp = require_value(data, key, message, code=code)
        if not ok:
            return False, resp
    return True, None


def require_exists(path, message, status=400, code="ERR_PATH_NOT_FOUND"):
    if not os.path.exists(path):
        return False, error_response(message, status=status, code=code)
    return True, None


def require_dir(path, message, status=400, code="ERR_NOT_A_DIRECTORY"):
    if not os.path.isdir(path):
        return False, error_response(message, status=status, code=code)
    return True, None
