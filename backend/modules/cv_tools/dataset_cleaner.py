"""
Dataset Cleaner
Identify and move images without corresponding YOLO annotations to a background folder.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

class DatasetCleaner:
    """Clean datasets by moving unlabeled images to backgrounds"""
    
    def __init__(self):
        self.supported_image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
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
                for img_path in unlabeled:
                    dest_path = Path(output_dir) / img_path.name
                    # Ensure we don't overwrite if file already exists in dest (append suffix if needed)
                    if dest_path.exists():
                        base = dest_path.stem
                        ext = dest_path.suffix
                        counter = 1
                        while (Path(output_dir) / f"{base}_{counter}{ext}").exists():
                            counter += 1
                        dest_path = Path(output_dir) / f"{base}_{counter}{ext}"
                    
                    shutil.move(str(img_path), str(dest_path))
                    move_count += 1
                    
                    if progress_callback:
                        progress_callback(move_count, len(unlabeled), f"Moving {img_path.name}...")
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
