"""
Dataset Cleaner
Identify and move background images to a background folder.
Images are considered background when they have no corresponding YOLO label file
or the corresponding label file is empty.
"""

import os
import shutil
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from parallelism_config import get_executor_plan
except Exception:  # pragma: no cover - import path differs by runtime entrypoint
    from backend.parallelism_config import get_executor_plan


class DatasetCleaner:
    """Clean datasets by moving background images to backgrounds"""
    
    def __init__(self):
        self.supported_image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']

    @staticmethod
    def _unique_destination(output_dir: str, filename: str) -> Path:
        dest_path = Path(output_dir) / filename
        if not dest_path.exists():
            return dest_path

        base = dest_path.stem
        ext = dest_path.suffix
        counter = 1
        while (Path(output_dir) / f"{base}_{counter}{ext}").exists():
            counter += 1
        return Path(output_dir) / f"{base}_{counter}{ext}"

    @staticmethod
    def _move_single_background_task(img_path_str: str, labels_dir: str, output_dir: str) -> Dict:
        img_path = Path(img_path_str)
        label_path = Path(labels_dir) / f"{img_path.stem}.txt"
        label_moved = False
        try:
            shutil.move(str(img_path), str(DatasetCleaner._unique_destination(output_dir, img_path.name)))

            if label_path.exists() and label_path.stat().st_size == 0:
                shutil.move(str(label_path), str(DatasetCleaner._unique_destination(output_dir, label_path.name)))
                label_moved = True

            return {"success": True, "image_name": img_path.name, "label_moved": label_moved}
        except Exception as e:
            return {"success": False, "image_name": img_path.name, "error": str(e)}
    
    def scan_dataset(self, images_dir: str, labels_dir: str) -> Tuple[List[Path], List[Path]]:
        """
        Scan directory and separate labeled and background images
        
        Args:
            images_dir: Directory containing images
            labels_dir: Directory containing annotations
            
        Returns:
            (labeled_images, background_images) - lists of image Path objects.
            Background images either have no matching txt label or have an empty txt label.
        """
        images_path = Path(images_dir)
        labels_path = Path(labels_dir)
        
        # Find all images
        image_files = []
        for ext in self.supported_image_extensions:
            image_files.extend(images_path.glob(f'*{ext}'))
            image_files.extend(images_path.glob(f'*{ext.upper()}'))
        
        # Get image basenames (stem) for matching
        image_map = {img.stem: img for img in image_files}
        
        # Find non-empty annotations. Empty label files are treated as backgrounds.
        label_files = list(labels_path.glob('*.txt'))
        non_empty_label_basenames = {lbl.stem for lbl in label_files if lbl.stat().st_size > 0}
        
        # Separate labeled and background images
        labeled_stems = set(image_map.keys()) & non_empty_label_basenames
        background_stems = set(image_map.keys()) - non_empty_label_basenames
        
        labeled_images = [image_map[stem] for stem in labeled_stems]
        background_images = [image_map[stem] for stem in background_stems]
        
        return labeled_images, background_images

    def clean(self, images_dir: str, labels_dir: str, output_dir: str, dry_run: bool = False, progress_callback=None) -> Dict:
        """
        Move background images to output_dir
        
        Args:
            images_dir: Directory containing images
            labels_dir: Directory containing YOLO labels
            output_dir: Directory to move background images to
            dry_run: If True, don't actually move files
            progress_callback: Optional function(current, total, message)
            
        Returns:
            Result dictionary with statistics
        """
        try:
            if not os.path.exists(images_dir):
                return {'success': False, 'error': f'Images directory not found: {images_dir}'}
            if not os.path.exists(labels_dir):
                return {'success': False, 'error': f'Labels directory not found: {labels_dir}'}
            
            labeled, backgrounds = self.scan_dataset(images_dir, labels_dir)
            
            total_count = len(labeled) + len(backgrounds)
            move_count = 0
            
            if not dry_run and len(backgrounds) > 0:
                os.makedirs(output_dir, exist_ok=True)
                total_backgrounds = len(backgrounds)
                plan = get_executor_plan(total_backgrounds, workload='io', prefer_process=False)
                if plan.kind == 'serial':
                    for img_path in backgrounds:
                        result = self._move_single_background_task(str(img_path), labels_dir, output_dir)
                        if result.get('success'):
                            move_count += 1
                        if progress_callback:
                            progress_callback(move_count, total_backgrounds, f"Moving {img_path.name}...")
                else:
                    executor_cls = (
                        concurrent.futures.ProcessPoolExecutor
                        if plan.kind == 'process'
                        else concurrent.futures.ThreadPoolExecutor
                    )
                    completed = 0
                    with executor_cls(max_workers=plan.workers) as executor:
                        future_to_img = {
                            executor.submit(self._move_single_background_task, str(img_path), labels_dir, output_dir): img_path
                            for img_path in backgrounds
                        }
                        for future in concurrent.futures.as_completed(future_to_img):
                            img_path = future_to_img[future]
                            completed += 1
                            result = future.result()
                            if result.get('success'):
                                move_count += 1
                            if progress_callback:
                                progress_callback(completed, total_backgrounds, f"Moving {img_path.name}...")
            else:
                move_count = len(backgrounds)
            
            return {
                'success': True,
                'total_count': total_count,
                'labeled_count': len(labeled),
                'unlabeled_count': len(backgrounds),
                'background_count': len(backgrounds),
                'moved_count': move_count if not dry_run else 0,
                'dry_run': dry_run,
                'output_dir': output_dir
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
