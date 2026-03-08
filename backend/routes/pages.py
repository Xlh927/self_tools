import os
from flask import Blueprint, render_template, request, Response


def create_pages_blueprint():
    bp = Blueprint('pages', __name__)

    @bp.route('/')
    def dashboard():
        return render_template('index.html')

    @bp.route('/cv-tools')
    def cv_tools():
        dist_template = os.path.join('dist', 'cv-tools.html')
        frontend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dist_path = os.path.join(frontend_root, 'frontend', 'dist', 'cv-tools.html')
        if os.path.exists(dist_path):
            return render_template(dist_template)
        return Response(
            (
                "Frontend bundle not found. Build it on a machine with Node.js via "
                "`./start.sh --bootstrap` or `npm --prefix frontend run build`, "
                "or use a runtime bundle created by `./scripts/build_runtime_bundle.sh`."
            ),
            status=503,
            mimetype='text/plain',
        )

    @bp.route('/image-viewer')
    @bp.route('/viewer')
    def image_viewer():
        return render_template('image-viewer.html')

    @bp.route('/legacy')
    def legacy():
        return render_template('index.html')

    @bp.route('/converter')
    def converter_page():
        tool_id = request.args.get('tool_id', 'legacy')
        return render_template('converter.html', tool_id=tool_id)

    @bp.route('/cropper')
    def cropper_page():
        tool_id = request.args.get('tool_id', 'legacy')
        return render_template('cropper.html', tool_id=tool_id)

    @bp.route('/generator')
    def generator_page():
        tool_id = request.args.get('tool_id', 'legacy')
        return render_template('generator.html', tool_id=tool_id)

    @bp.route('/splitter')
    def splitter_page():
        tool_id = request.args.get('tool_id', 'legacy')
        return render_template('splitter.html', tool_id=tool_id)

    @bp.route('/deduplicator')
    def deduplicator_page():
        tool_id = request.args.get('tool_id', 'legacy')
        return render_template('deduplicator.html', tool_id=tool_id)

    @bp.route('/matcher')
    def matcher_page():
        tool_id = request.args.get('tool_id', 'legacy')
        return render_template('matcher.html', tool_id=tool_id)

    @bp.route('/visualizer')
    def visualizer_page():
        tool_id = request.args.get('tool_id', 'legacy')
        return render_template('visualizer.html', tool_id=tool_id)

    return bp
