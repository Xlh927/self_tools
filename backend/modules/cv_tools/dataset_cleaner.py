"""
Dataset Cleaner
Identify and move images without corresponding YOLO annotations to a background folder.
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
    """Clean datasets by moving unlabeled images to backgrounds"""
    
    def __init__(self):
        self.supported_image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']

    @staticmethod
    def _move_single_image_task(img_path_str: str, output_dir: str) -> Dict:
        img_path = Path(img_path_str)
        dest_path = Path(output_dir) / img_path.name
        try:
            # Avoid overwrite by suffixing duplicate names.
            if dest_path.exists():
                base = dest_path.stem
                ext = dest_path.suffix
                counter = 1
                while (Path(output_dir) / f"{base}_{counter}{ext}").exists():
                    counter += 1
                dest_path = Path(output_dir) / f"{base}_{counter}{ext}"

            shutil.move(str(img_path), str(dest_path))
            return {"success": True, "image_name": img_path.name}
        except Exception as e:
            return {"success": False, "image_name": img_path.name, "error": str(e)}
    
    def scan_dataset(self, images_dir: str, labels_dir: str) -> Tuple[List[Path], List[Path]]:
        """
        Scan directory and separate labeled and unlabeled images
        
        Args:
            images_dir: Directory containing images
            labels_dir: Directory containing annotations
            
        Returns:
            (labeled_images, unlabeled_images) - lists of image Path objects
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
        
        # Find annotations
        label_files = list(labels_path.glob('*.txt'))
        label_basenames = {lbl.stem for lbl in label_files}
        
        # Separate labeled and unlabeled
        labeled_stems = set(image_map.keys()) & label_basenames
        unlabeled_stems = set(image_map.keys()) - label_basenames
        
        labeled_images = [image_map[stem] for stem in labeled_stems]
        unlabeled_images = [image_map[stem] for stem in unlabeled_stems]
        
        return labeled_images, unlabeled_images

    def clean(self, images_dir: str, labels_dir: str, output_dir: str, dry_run: bool = False, progress_callback=None) -> Dict:
        """
        Move unlabeled images to output_dir
        
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
            
            labeled, unlabeled = self.scan_dataset(images_dir, labels_dir)
            
            total_count = len(labeled) + len(unlabeled)
            move_count = 0
            
            if not dry_run and len(unlabeled) > 0:
                os.makedirs(output_dir, exist_ok=True)
                total_unlabeled = len(unlabeled)
                plan = get_executor_plan(total_unlabeled, workload='io', prefer_process=False)
                if plan.kind == 'serial':
                    for img_path in unlabeled:
                        result = self._move_single_image_task(str(img_path), output_dir)
                        if result.get('success'):
                            move_count += 1
                        if progress_callback:
                            progress_callback(move_count, total_unlabeled, f"Moving {img_path.name}...")
                else:
                    executor_cls = (
                        concurrent.futures.ProcessPoolExecutor
                        if plan.kind == 'process'
                        else concurrent.futures.ThreadPoolExecutor
                    )
                    completed = 0
                    with executor_cls(max_workers=plan.workers) as executor:
                        future_to_img = {
                            executor.submit(self._move_single_image_task, str(img_path), output_dir): img_path
                            for img_path in unlabeled
                        }
                        for future in concurrent.futures.as_completed(future_to_img):
                            img_path = future_to_img[future]
                            completed += 1
                            result = future.result()
                            if result.get('success'):
                                move_count += 1
                            if progress_callback:
                                progress_callback(completed, total_unlabeled, f"Moving {img_path.name}...")
            else:
                move_count = len(unlabeled)
            
            return {
                'success': True,
                'total_count': total_count,
                'labeled_count': len(labeled),
                'unlabeled_count': len(unlabeled),
                'moved_count': move_count if not dry_run else 0,
                'dry_run': dry_run,
                'output_dir': output_dir
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
