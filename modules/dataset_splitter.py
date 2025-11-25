"""
Dataset Splitter
Split datasets into train/val/test sets with support for VOC and YOLO formats
"""

import os
import shutil
import random
from pathlib import Path
from typing import Dict, List, Tuple


class DatasetSplitter:
    """Split datasets into train/val/test sets"""
    
    def __init__(self):
        self.supported_image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
    def scan_dataset(self, input_dir: str, format_type: str) -> Tuple[List[str], List[str]]:
        """
        Scan directory and separate labeled and unlabeled images
        
        Args:
            input_dir: Directory containing images and annotations
            format_type: 'voc' or 'yolo'
            
        Returns:
            (labeled_images, unlabeled_images) - lists of image basenames (without extension)
        """
        input_path = Path(input_dir)
        
        # Find all images
        image_files = []
        for ext in self.supported_image_extensions:
            image_files.extend(input_path.glob(f'*{ext}'))
            image_files.extend(input_path.glob(f'*{ext.upper()}'))
        
        # Get basenames
        image_basenames = {img.stem for img in image_files}
        
        # Find annotations
        annotation_ext = '.xml' if format_type == 'voc' else '.txt'
        annotation_files = list(input_path.glob(f'*{annotation_ext}'))
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
        test_count = total - train_count - val_count  # Remaining goes to test
        
        return train_count, val_count, test_count
    
    def copy_files(self, basenames: List[str], input_dir: str, output_dir: str, 
                   split_name: str, format_type: str):
        """
        Copy image and annotation files to output directory
        
        Args:
            basenames: List of file basenames (without extension)
            input_dir: Source directory
            output_dir: Destination directory
            split_name: 'train', 'val', or 'test'
            format_type: 'voc' or 'yolo'
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir) / split_name
        
        # Create output directories
        images_dir = output_path / 'images'
        labels_dir = output_path / 'labels'
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        
        annotation_ext = '.xml' if format_type == 'voc' else '.txt'
        
        for basename in basenames:
            # Find and copy image
            image_file = None
            for ext in self.supported_image_extensions:
                potential_file = input_path / f'{basename}{ext}'
                if potential_file.exists():
                    image_file = potential_file
                    break
                potential_file = input_path / f'{basename}{ext.upper()}'
                if potential_file.exists():
                    image_file = potential_file
                    break
            
            if image_file:
                shutil.copy2(image_file, images_dir / image_file.name)
            
            # Copy annotation
            annotation_file = input_path / f'{basename}{annotation_ext}'
            if annotation_file.exists():
                shutil.copy2(annotation_file, labels_dir / annotation_file.name)
    
    def copy_background_files(self, basenames: List[str], input_dir: str, output_dir: str):
        """
        Copy unlabeled images to background folder
        
        Args:
            basenames: List of file basenames (without extension)
            input_dir: Source directory
            output_dir: Destination directory
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir) / 'background' / 'images'
        output_path.mkdir(parents=True, exist_ok=True)
        
        for basename in basenames:
            # Find and copy image
            for ext in self.supported_image_extensions:
                image_file = input_path / f'{basename}{ext}'
                if image_file.exists():
                    shutil.copy2(image_file, output_path / image_file.name)
                    break
                image_file = input_path / f'{basename}{ext.upper()}'
                if image_file.exists():
                    shutil.copy2(image_file, output_path / image_file.name)
                    break
    
    def split_dataset(self, config: Dict) -> Dict:
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
        
        Returns:
            Result dictionary with statistics
        """
        try:
            format_type = config['format']
            input_dir = config['input_dir']
            output_dir = config['output_dir']
            train_ratio = config.get('train_ratio', 70)
            val_ratio = config.get('val_ratio', 20)
            test_ratio = config.get('test_ratio', 10)
            use_background = config.get('use_background', False)
            random_seed = config.get('random_seed', 42)
            
            # Validate input directory
            if not os.path.exists(input_dir):
                return {
                    'success': False,
                    'error': f'Input directory does not exist: {input_dir}'
                }
            
            # Scan dataset
            labeled, unlabeled = self.scan_dataset(input_dir, format_type)
            
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
            self.copy_files(train_images, input_dir, output_dir, 'train', format_type)
            self.copy_files(val_images, input_dir, output_dir, 'val', format_type)
            
            if test_count > 0:
                self.copy_files(test_images, input_dir, output_dir, 'test', format_type)
            
            # Handle background images
            background_count = 0
            if use_background and len(unlabeled) > 0:
                self.copy_background_files(unlabeled, input_dir, output_dir)
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
