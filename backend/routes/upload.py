import os
from flask import Blueprint, request

from routes.utils import error_response, success_response


def create_upload_blueprint():
    bp = Blueprint('upload', __name__)

    @bp.route('/api/upload', methods=['POST'])
    def upload_file():
        try:
            if 'file' not in request.files:
                return error_response('No file part', code='ERR_MISSING_FIELD')

            file = request.files['file']
            if file.filename == '':
                return error_response('No selected file', code='ERR_MISSING_FIELD')

            upload_dir = os.path.join(os.getcwd(), 'temp_uploads')
            os.makedirs(upload_dir, exist_ok=True)

            filename = file.filename
            filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in '._-']).strip()
            if not filename:
                filename = 'uploaded_image.png'

            filepath = os.path.join(upload_dir, filename)
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(filepath):
                filepath = os.path.join(upload_dir, f"{base}_{counter}{ext}")
                counter += 1

            file.save(filepath)
            return success_response(
                {'path': filepath, 'filename': os.path.basename(filepath)},
                message='File uploaded',
                status=201,
            )
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
