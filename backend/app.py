"""
Flask Web Application for Image Processing Tools
Splits routes into blueprints under backend/routes.
"""

import os
import sys
from flask import Flask

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from task_manager import TaskManager
from routes.tasks import create_tasks_blueprint
from routes.pages import create_pages_blueprint
from routes.viewer import create_viewer_blueprint
from routes.visualize import create_visualize_blueprint
from routes.match import create_match_blueprint
from routes.convert import create_convert_blueprint
from routes.crop import create_crop_blueprint
from routes.generate import create_generate_blueprint
from routes.split import create_split_blueprint
from routes.clean import create_clean_blueprint
from routes.dedup import create_dedup_blueprint
from routes.labels import create_labels_blueprint
from routes.augment import create_augment_blueprint
from routes.grid import create_grid_blueprint
from routes.upload import create_upload_blueprint


app = Flask(
    __name__,
    template_folder='../frontend',
    static_folder='../frontend',
    static_url_path=''
)
task_manager = TaskManager()


# Enable CORS for development
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# Register blueprints
app.register_blueprint(create_tasks_blueprint(task_manager))
app.register_blueprint(create_pages_blueprint())
app.register_blueprint(create_viewer_blueprint())
app.register_blueprint(create_visualize_blueprint(task_manager))
app.register_blueprint(create_match_blueprint(task_manager))
app.register_blueprint(create_convert_blueprint(task_manager))
app.register_blueprint(create_crop_blueprint(task_manager))
app.register_blueprint(create_generate_blueprint(task_manager))
app.register_blueprint(create_split_blueprint(task_manager))
app.register_blueprint(create_clean_blueprint(task_manager))
app.register_blueprint(create_dedup_blueprint(task_manager))
app.register_blueprint(create_labels_blueprint(task_manager))
app.register_blueprint(create_augment_blueprint(task_manager))
app.register_blueprint(create_grid_blueprint())
app.register_blueprint(create_upload_blueprint())


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
