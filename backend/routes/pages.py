from flask import Blueprint, render_template, request


def create_pages_blueprint():
    bp = Blueprint('pages', __name__)

    @bp.route('/')
    def dashboard():
        return render_template('index.html')

    @bp.route('/cv-tools')
    def cv_tools():
        return render_template('cv-tools.html')

    @bp.route('/image-viewer')
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
