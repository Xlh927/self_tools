import os

class LabelModifier:
    def __init__(self):
        pass

    def scan_classes(self, label_dir):
        """
        Scan a directory for all unique YOLO class IDs and count samples.
        
        Args:
            label_dir (str): Path to the directory containing YOLO label files.
            
        Returns:
            dict: {'success': bool, 'classes': [{'id': int, 'count': int}], 'error': str}
        """
        if not os.path.exists(label_dir):
            return {'success': False, 'error': f'Label directory not found: {label_dir}'}
            
        class_counts = {}
        
        try:
            for file_name in os.listdir(label_dir):
                if not file_name.endswith(".txt"):
                    continue
                    
                label_path = os.path.join(label_dir, file_name)
                try:
                    with open(label_path, "r") as f:
                        for line in f:
                            parts = line.strip().split()
                            if parts:
                                try:
                                    class_id = int(parts[0])
                                    class_counts[class_id] = class_counts.get(class_id, 0) + 1
                                except ValueError:
                                    continue
                except Exception:
                    continue
                    
            # Convert to list of dicts sorted by class ID
            classes_list = [{'id': class_id, 'count': count} 
                           for class_id, count in sorted(class_counts.items())]
            
            return {
                'success': True,
                'classes': classes_list
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def modify_labels(self, label_dir, class_mapping, overwrite=False, output_dir=None):
        """
        Modify YOLO labels in a directory by mapping old class IDs to new ones.
        
        Args:
            label_dir (str): Path to the directory containing YOLO label files.
            class_mapping (dict): Dictionary mapping old_class_id (int) to new_class_id (int).
            overwrite (bool): If True, overwrite original files. If False, save to output_dir.
            output_dir (str): Directory to save modified files if overwrite is False.
            
        Returns:
            dict: A summary of the operation.
        """
        if not os.path.exists(label_dir):
            return {'success': False, 'error': f'Label directory not found: {label_dir}'}

        if not overwrite:
            if not output_dir:
                return {'success': False, 'error': 'Output directory is required when overwrite is False'}
            os.makedirs(output_dir, exist_ok=True)

        processed_count = 0
        modified_count = 0
        error_count = 0
        
        # Ensure mapping keys/values are integers
        try:
            mapping = {int(k): int(v) for k, v in class_mapping.items()}
        except ValueError:
             return {'success': False, 'error': 'Class mapping keys and values must be integers'}
        
        try:
            for file_name in os.listdir(label_dir):
                if not file_name.endswith(".txt"):
                    continue
                
                label_path = os.path.join(label_dir, file_name)
                save_path = label_path if overwrite else os.path.join(output_dir, file_name)
                
                try:
                    with open(label_path, "r") as f:
                        lines = f.readlines()

                    new_lines = []
                    changed = False

                    for line in lines:
                        parts = line.strip().split()
                        if not parts:
                            continue
                        
                        try:
                            class_id = int(parts[0])
                            if class_id in mapping:
                                parts[0] = str(mapping[class_id])
                                changed = True
                            new_lines.append(" ".join(parts))
                        except ValueError:
                            # Skip lines that don't start with an integer (malformed lines)
                            new_lines.append(line.strip())
                            continue

                    # If changed, write the new content
                    # If not changed, we still need to write the file if we are not overwriting (copying)
                    if changed or not overwrite:
                        with open(save_path, "w") as f:
                            f.write("\n".join(new_lines) + "\n")
                    
                    processed_count += 1
                    if changed:
                        modified_count += 1
                        
                except Exception as e:
                    print(f"Error processing file {file_name}: {e}")
                    error_count += 1
                    
            return {
                'success': True,
                'processed': processed_count,
                'modified': modified_count,
                'errors': error_count
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
