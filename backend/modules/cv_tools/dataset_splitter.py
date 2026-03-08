"""
Dataset Splitter
Split datasets into train/val/test sets with support for VOC and YOLO formats
"""

import os
import shutil
import random
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from parallelism_config import get_executor_plan
except Exception:  # pragma: no cover - import path differs by runtime entrypoint
    from backend.parallelism_config import get_executor_plan


class DatasetSplitter:
    """Split datasets into train/val/test sets"""
    
    def __init__(self):
        self.supported_image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']

    @staticmethod
    def _find_image_file(images_path: Path, basename: str, supported_extensions: List[str]) -> Path:
        for ext in supported_extensions:
            lower = images_path / f'{basename}{ext}'
            if lower.exists():
                return lower
            upper = images_path / f'{basename}{ext.upper()}'
            if upper.exists():
                return upper
        return None

    @staticmethod
    def _copy_single_sample_task(
        basename: str,
        images_dir: str,
        annotations_dir: str,
        output_images_dir: str,
        output_labels_dir: str,
        annotation_ext: str,
        supported_extensions: List[str],
    ) -> None:
        images_path = Path(images_dir)
        annotations_path = Path(annotations_dir)
        output_images_path = Path(output_images_dir)
        output_labels_path = Path(output_labels_dir)

        image_file = DatasetSplitter._find_image_file(images_path, basename, supported_extensions)
        if image_file:
            shutil.copy2(image_file, output_images_path / image_file.name)

        annotation_file = annotations_path / f'{basename}{annotation_ext}'
        if annotation_file.exists():
            shutil.copy2(annotation_file, output_labels_path / annotation_file.name)

    @staticmethod
    def _copy_single_background_task(
        basename: str,
        images_dir: str,
        background_output_dir: str,
        supported_extensions: List[str],
    ) -> None:
        images_path = Path(images_dir)
        output_path = Path(background_output_dir)
        image_file = DatasetSplitter._find_image_file(images_path, basename, supported_extensions)
        if image_file:
            shutil.copy2(image_file, output_path / image_file.name)
    
    def scan_dataset(self, images_dir: str, annotations_dir: str, format_type: str) -> Tuple[List[str], List[str]]:
        """
        Scan directory and separate labeled and unlabeled images
        
        Args:
            images_dir: Directory containing images
            annotations_dir: Directory containing annotations
            format_type: 'voc' or 'yolo'
            
        Returns:
            (labeled_images, unlabeled_images) - lists of image basenames (without extension)
        """
        images_path = Path(images_dir)
        annotations_path = Path(annotations_dir)
        
        # Find all images
        image_files = []
        for ext in self.supported_image_extensions:
            image_files.extend(images_path.glob(f'*{ext}'))
            image_files.extend(images_path.glob(f'*{ext.upper()}'))
        
        # Get basenames
        image_basenames = {img.stem for img in image_files}
        
        # Find annotations
        annotation_ext = '.xml' if format_type == 'voc' else '.txt'
        annotation_files = list(annotations_path.glob(f'*{annotation_ext}'))
        annotation_basenames = {ann.stem for ann in annotation_files}
        
        # Separate labeled and unlabeled
        labeled = list(image_basenames & annotation_basenames)
        unlabeled = list(image_basenames - annotation_basenames)
        
        return labeled, unlabeled
    
    def calculate_split_counts(self, total: int, train_ratio: float, val_ratio: float, 
                               test_ratio: float) -> Tuple[int, int, int]:
        """
        Calculate split counts based on ratios
        
        Args:
            total: Total number of items
            train_ratio: Train percentage (0-100)
            val_ratio: Val percentage (0-100)
            test_ratio: Test percentage (0-100)
            
        Returns:
            (train_count, val_count, test_count)
        """
        train_count = int(total * train_ratio / 100)
        val_count = int(total * val_ratio / 100)
        test_count = int(total * test_ratio / 100)
        
        remainder = total - (train_count + val_count + test_count)
        
        # Add remainder to the largest split to respect ratios as much as possible
        if remainder > 0:
            ratios = {'train': train_ratio, 'val': val_ratio, 'test': test_ratio}
            # Find key with max value
            max_split = max(ratios, key=ratios.get)
            
            if max_split == 'train':
                train_count += remainder
            elif max_split == 'val':
                val_count += remainder
            else:
                test_count += remainder
        
        return train_count, val_count, test_count
    
    def copy_files(self, basenames: List[str], images_dir: str, annotations_dir: str, 
                   output_dir: str, split_name: str, format_type: str, progress_callback=None, offset=0, total=0):
        """
        Copy image and annotation files to output directory
        
        Args:
            basenames: List of file basenames (without extension)
            images_dir: Source images directory
            annotations_dir: Source annotations directory
            output_dir: Destination directory
            split_name: 'train', 'val', or 'test'
            format_type: 'voc' or 'yolo'
        """
        images_path = Path(images_dir)
        annotations_path = Path(annotations_dir)
        output_path = Path(output_dir) / split_name
        
        # Create output directories
        images_dir = output_path / 'images'
        labels_dir = output_path / 'labels'
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        
        annotation_ext = '.xml' if format_type == 'voc' else '.txt'
        plan = get_executor_plan(len(basenames), workload='io', prefer_process=False)
        if plan.kind == 'serial':
            for idx, basename in enumerate(basenames, start=1):
                self._copy_single_sample_task(
                    basename,
                    str(images_path),
                    str(annotations_path),
                    str(images_dir),
                    str(labels_dir),
                    annotation_ext,
                    self.supported_image_extensions,
                )
                if progress_callback:
                    progress_callback(offset + idx, total, f"Copying {split_name} files...")
        else:
            executor_cls = (
                concurrent.futures.ProcessPoolExecutor
                if plan.kind == 'process'
                else concurrent.futures.ThreadPoolExecutor
            )
            completed = 0
            with executor_cls(max_workers=plan.workers) as executor:
                future_to_base = {
                    executor.submit(
                        self._copy_single_sample_task,
                        basename,
                        str(images_path),
                        str(annotations_path),
                        str(images_dir),
                        str(labels_dir),
                        annotation_ext,
                        self.supported_image_extensions,
                    ): basename
                    for basename in basenames
                }
                for future in concurrent.futures.as_completed(future_to_base):
                    # Preserve previous behavior: any file-level exception fails split.
                    future.result()
                    completed += 1
                    if progress_callback:
                        progress_callback(offset + completed, total, f"Copying {split_name} files...")
    
    def copy_background_files(self, basenames: List[str], images_dir: str, output_dir: str):
        """
        Copy unlabeled images to background folder
        
        Args:
            basenames: List of file basenames (without extension)
            images_dir: Source images directory
            output_dir: Destination directory
        """
        images_path = Path(images_dir)
        output_path = Path(output_dir) / 'background' / 'images'
        output_path.mkdir(parents=True, exist_ok=True)

        plan = get_executor_plan(len(basenames), workload='io', prefer_process=False)
        if plan.kind == 'serial':
            for basename in basenames:
                self._copy_single_background_task(
                    basename,
                    str(images_path),
                    str(output_path),
                    self.supported_image_extensions,
                )
        else:
            executor_cls = (
                concurrent.futures.ProcessPoolExecutor
                if plan.kind == 'process'
                else concurrent.futures.ThreadPoolExecutor
            )
            with executor_cls(max_workers=plan.workers) as executor:
                futures = [
                    executor.submit(
                        self._copy_single_background_task,
                        basename,
                        str(images_path),
                        str(output_path),
                        self.supported_image_extensions,
                    )
                    for basename in basenames
                ]
                for future in concurrent.futures.as_completed(futures):
                    future.result()
    
    def split_dataset(self, config: Dict, progress_callback=None) -> Dict:
        """
        Split dataset into train/val/test sets
        
        Args:
            config: Configuration dictionary with keys:
                - format: 'voc' or 'yolo'
                - input_dir: Input directory path
                - output_dir: Output directory path
                - train_ratio: Train percentage (0-100)
                - val_ratio: Val percentage (0-100)
                - test_ratio: Test percentage (0-100)
                - use_background: Whether to move unlabeled to background
                - random_seed: Random seed for reproducibility
            progress_callback: Optional function(current, total, message)
        
        Returns:
            Result dictionary with statistics
        """
        try:
            annotation_format = config['format']
            images_dir = config['images_dir']
            annotations_dir = config['annotations_dir']
            output_dir = config['output_dir']
            train_ratio = config.get('train_ratio', 70)
            val_ratio = config.get('val_ratio', 20)
            test_ratio = config.get('test_ratio', 10)
            use_background = config.get('use_background', False)
            random_seed = config.get('random_seed', 42)

            # Validate ratios
            ratios = [train_ratio, val_ratio, test_ratio]
            if any(r < 0 for r in ratios):
                return {
                    'success': False,
                    'error': 'Split ratios must be non-negative'
                }
            if abs(sum(ratios) - 100) > 1e-6:
                return {
                    'success': False,
                    'error': 'Split ratios must sum to 100'
                }
            
            # Validate input directory
            if not os.path.exists(images_dir):
                return {
                    'success': False,
                    'error': f'Images directory does not exist: {images_dir}'
                }
            if not os.path.exists(annotations_dir):
                return {
                    'success': False,
                    'error': f'Annotations directory does not exist: {annotations_dir}'
                }
            
            # Scan dataset
            labeled, unlabeled = self.scan_dataset(images_dir, annotations_dir, annotation_format)
            
            total_images = len(labeled) + len(unlabeled)
            
            if total_images == 0:
                return {
                    'success': False,
                    'error': 'No images found in input directory'
                }
            
            if len(labeled) == 0:
                return {
                    'success': False,
                    'error': 'No labeled images found. Please check annotation files.'
                }
            
            # Shuffle labeled images with seed
            random.seed(random_seed)
            random.shuffle(labeled)
            
            # Calculate split counts
            train_count, val_count, test_count = self.calculate_split_counts(
                len(labeled), train_ratio, val_ratio, test_ratio
            )
            
            # Split labeled images
            train_images = labeled[:train_count]
            val_images = labeled[train_count:train_count + val_count]
            test_images = labeled[train_count + val_count:]
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Copy files
            total_work = len(labeled)
            current_work = 0
            
            self.copy_files(train_images, images_dir, annotations_dir, output_dir, 'train', annotation_format, progress_callback, current_work, total_work)
            current_work += len(train_images)
            
            self.copy_files(val_images, images_dir, annotations_dir, output_dir, 'val', annotation_format, progress_callback, current_work, total_work)
            current_work += len(val_images)
            
            if test_count > 0:
                self.copy_files(test_images, images_dir, annotations_dir, output_dir, 'test', annotation_format, progress_callback, current_work, total_work)
                current_work += len(test_images)
            
            # Handle background images
            background_count = 0
            if use_background and len(unlabeled) > 0:
                self.copy_background_files(unlabeled, images_dir, output_dir)
                background_count = len(unlabeled)
            
            return {
                'success': True,
                'total_images': total_images,
                'labeled_images': len(labeled),
                'unlabeled_images': len(unlabeled),
                'train_count': len(train_images),
                'val_count': len(val_images),
                'test_count': len(test_images),
                'background_count': background_count,
                'output_structure': {
                    'train': len(train_images) > 0,
                    'val': len(val_images) > 0,
                    'test': len(test_images) > 0,
                    'background': background_count > 0
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
