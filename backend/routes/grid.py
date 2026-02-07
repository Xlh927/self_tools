import json
from io import BytesIO

from flask import Blueprint, request
from PIL import Image

from modules.cv_tools import PaperGridGenerator
from routes.utils import error_response, success_response


def create_grid_blueprint():
    bp = Blueprint('grid', __name__)

    @bp.route('/api/generate-grid', methods=['POST'])
    def generate_grid():
        try:
            config_json = request.form.get('config')
            if not config_json:
                return error_response('Missing config', code='ERR_MISSING_FIELD')
            config = json.loads(config_json)

            cells = config.get('cells', [])
            if not cells:
                return error_response('Missing cells', code='ERR_MISSING_FIELD')

            temp_image_map = {}
            for key in request.files:
                if key.startswith('cell_'):
                    file = request.files[key]
                    img_data = file.read()
                    pil_img = Image.open(BytesIO(img_data))
                    temp_image_map[key] = pil_img

            for i, cell in enumerate(cells):
                file_key = f'cell_{i}'
                if file_key in temp_image_map:
                    cell['pil_image'] = temp_image_map[file_key]
                    cell['path'] = None

            generator = PaperGridGenerator()
            result = generator.generate_grid(config)
            if result.get('success'):
                return success_response(result, message='Grid generated')
            return error_response(result.get('error', 'Grid generation failed'), code='ERR_GRID_GENERATION_FAILED')
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
