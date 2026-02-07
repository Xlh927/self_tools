from pathlib import Path
from flask import Blueprint

from modules.cv_tools import AnnotationVisualizer, DatasetConverter
from routes.utils import (
    ValidationError,
    error_response,
    handle_validation_error,
    parse_json_request,
    success_response,
    task_queued_response,
)


def create_convert_blueprint(task_manager):
    bp = Blueprint('convert', __name__)

    @bp.route('/api/convert', methods=['POST'])
    def convert():
        try:
            data = parse_json_request(
                required=['conversion_type', 'annotations_dir', 'images_dir', 'output_dir'],
                exists=['annotations_dir', 'images_dir'],
                dirs=['annotations_dir', 'images_dir'],
                defaults={'classes_file': '', 'max_retries': 1},
                coerce={'max_retries': int},
            )

            conversion_type = data['conversion_type']
            annotations_dir = data['annotations_dir']
            images_dir = data['images_dir']
            output_dir = data['output_dir']
            classes_file = data.get('classes_file', '')
            custom_classes = data.get('custom_classes')
            selected_classes = data.get('selected_classes')

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

                    if selected_classes and result.get('success') and result.get('classes'):
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
                    raise ValidationError(f'Invalid conversion type: {conversion_type}', code='ERR_INVALID_FIELD', status=400)

                task_manager.finish_task(
                    task_id,
                    status='completed',
                    message='Conversion completed',
                    result=result
                )

            task_id = task_manager.start_task(
                message='Starting conversion...',
                run_fn=run_conversion,
                max_retries=data.get('max_retries', 1),
            )
            return task_queued_response(task_id, message='Conversion task queued')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/scan-classes', methods=['POST'])
    def scan_classes():
        try:
            data = parse_json_request(required=['annotations_dir'], exists=['annotations_dir'], dirs=['annotations_dir'])
            annotations_dir = data['annotations_dir']
            is_yolo_format = data.get('is_yolo_format', False)

            visualizer = AnnotationVisualizer()
            annotation_format = 'yolo' if is_yolo_format else 'voc'
            result = visualizer.detect_classes(annotations_dir, annotation_format)

            if result.get('success'):
                classes_list = [{'name': cls, 'count': 0} for cls in result.get('classes', [])]
                return success_response({'classes': classes_list}, message='Classes scanned')
            return error_response(result.get('error', 'Class scan failed'), code='ERR_CLASS_SCAN_FAILED')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/scan-voc-classes', methods=['POST'])
    def scan_voc_classes():
        try:
            data = parse_json_request(required=['annotations_dir'], exists=['annotations_dir'], dirs=['annotations_dir'])
            converter = DatasetConverter()
            result = converter.scan_voc_classes(data['annotations_dir'])
            if result.get('success'):
                return success_response(result, message='VOC classes scanned')
            return error_response(result.get('error', 'VOC class scan failed'), code='ERR_CLASS_SCAN_FAILED')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    @bp.route('/api/load-classes', methods=['POST'])
    def load_classes():
        try:
            data = parse_json_request(required=['classes_file'], exists=['classes_file'], files=['classes_file'])
            classes = []
            with open(data['classes_file'], 'r', encoding='utf-8') as f:
                classes = [line.strip() for line in f if line.strip()]
            classes_list = [{'name': cls, 'count': 0} for cls in classes]
            return success_response({'classes': classes_list}, message='Classes loaded')
        except ValidationError as e:
            return handle_validation_error(e)
        except Exception as e:
            return error_response(str(e), status=500, code='ERR_INTERNAL')

    return bp
