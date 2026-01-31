from pathlib import Path
from flask import Blueprint, jsonify, request

from modules.cv_tools import DatasetConverter, AnnotationVisualizer
from routes.utils import get_json_body, require_values, require_value, require_exists, error_response


def create_convert_blueprint(task_manager):
    bp = Blueprint('convert', __name__)

    @bp.route('/api/convert', methods=['POST'])
    def convert():
        try:
            data = get_json_body()
            ok, resp = require_values(data, [
                ('conversion_type', 'Missing required field: conversion_type'),
                ('annotations_dir', 'Missing required field: annotations_dir'),
                ('images_dir', 'Missing required field: images_dir'),
                ('output_dir', 'Missing required field: output_dir'),
            ])
            if not ok:
                return resp

            conversion_type = data['conversion_type']
            annotations_dir = data['annotations_dir']
            images_dir = data['images_dir']
            output_dir = data['output_dir']
            classes_file = data.get('classes_file', '')
            custom_classes = data.get('custom_classes')
            selected_classes = data.get('selected_classes')

            ok, resp = require_exists(annotations_dir, f'Annotations directory does not exist: {annotations_dir}')
            if not ok:
                return resp
            ok, resp = require_exists(images_dir, f'Images directory does not exist: {images_dir}')
            if not ok:
                return resp

            def run_conversion(task_id, cancel_event, pause_event):
                converter = DatasetConverter(classes_file if classes_file else None)
                progress_callback = task_manager.make_progress_callback(task_id, cancel_event, pause_event)

                if conversion_type == 'voc_to_yolo':
                    custom_class_mapping = data.get('custom_class_mapping')
                    result = converter.voc_to_yolo(
                        voc_xml_dir=annotations_dir,
                        images_dir=images_dir,
                        output_dir=output_dir,
                        classes_file=classes_file if classes_file else None,
                        custom_class_mapping=custom_class_mapping,
                        progress_callback=progress_callback
                    )

                    if selected_classes and result['success'] and result['classes']:
                        filtered_classes = [result['classes'][i] for i in selected_classes if i < len(result['classes'])]
                        class_map = {old_idx: new_idx for new_idx, old_idx in enumerate(selected_classes)}

                        output_files = [p for p in Path(output_dir).glob('*.txt') if p.name != 'classes.txt']
                        for txt_file in output_files:
                            filtered_lines = []
                            with open(txt_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    parts = line.strip().split()
                                    if not parts:
                                        continue
                                    try:
                                        class_id = int(parts[0])
                                    except ValueError:
                                        continue
                                    if class_id in selected_classes:
                                        parts[0] = str(class_map[class_id])
                                        filtered_lines.append(' '.join(parts))
                            with open(txt_file, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(filtered_lines))

                        classes_output = Path(output_dir) / 'classes.txt'
                        with open(classes_output, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(filtered_classes))
                        result['classes'] = filtered_classes

                elif conversion_type == 'yolo_to_voc':
                    result = converter.yolo_to_voc(
                        yolo_txt_dir=annotations_dir,
                        images_dir=images_dir,
                        output_dir=output_dir,
                        classes_file=classes_file if classes_file else None,
                        custom_classes=custom_classes,
                        progress_callback=progress_callback
                    )
                else:
                    raise ValueError(f'Invalid conversion type: {conversion_type}')

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Conversion completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting conversion...',
                run_fn=run_conversion
            )

            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'started'
            })

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/scan-classes', methods=['POST'])
    def scan_classes():
        try:
            data = get_json_body()
            annotations_dir = data.get('annotations_dir')
            is_yolo_format = data.get('is_yolo_format', False)

            ok, resp = require_value(data, 'annotations_dir', 'Missing annotations_dir')
            if not ok:
                return resp

            ok, resp = require_exists(annotations_dir, f'Directory not found: {annotations_dir}')
            if not ok:
                return resp

            visualizer = AnnotationVisualizer()
            annotation_format = 'yolo' if is_yolo_format else 'voc'

            result = visualizer.detect_classes(annotations_dir, annotation_format)

            if result['success']:
                classes_list = []
                for cls in result['classes']:
                    classes_list.append({'name': cls, 'count': 0})

                return jsonify({
                    'success': True,
                    'classes': classes_list
                })
            return jsonify(result)

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/scan-voc-classes', methods=['POST'])
    def scan_voc_classes():
        try:
            data = get_json_body()
            annotations_dir = data.get('annotations_dir')

            ok, resp = require_value(data, 'annotations_dir', 'Missing annotations_dir')
            if not ok:
                return resp
            ok, resp = require_exists(annotations_dir, f'Directory not found: {annotations_dir}')
            if not ok:
                return resp

            converter = DatasetConverter()
            result = converter.scan_voc_classes(annotations_dir)

            return jsonify(result)

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/load-classes', methods=['POST'])
    def load_classes():
        try:
            data = get_json_body()
            classes_file = data.get('classes_file')

            ok, resp = require_value(data, 'classes_file', 'Missing classes_file')
            if not ok:
                return resp
            ok, resp = require_exists(classes_file, f'File not found: {classes_file}')
            if not ok:
                return resp

            classes = []
            with open(classes_file, 'r', encoding='utf-8') as f:
                classes = [line.strip() for line in f if line.strip()]

            classes_list = []
            for cls in classes:
                classes_list.append({'name': cls, 'count': 0})

            return jsonify({
                'success': True,
                'classes': classes_list
            })

        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
