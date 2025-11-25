"""
Image Sliding Window Cropper
Crops large images using sliding window technique
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image


class ImageCropper:
    """Handles sliding window cropping of large images"""
    
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
    def crop_image_sliding_window(
        self,
        image_path: str,
        output_dir: str,
        window_width: int = 1024,
        window_height: int = 1024,
        overlap_x: int = 512,
        overlap_y: int = 512
    ) -> Dict:
        """
        Crop a single image using sliding window
        
        Args:
            image_path: Path to input image
            output_dir: Directory to save cropped images
            window_width: Width of cropping window
            window_height: Height of cropping window
            overlap_x: Horizontal overlap between windows
            overlap_y: Vertical overlap between windows
            
        Returns:
            Dictionary with cropping results
        """
        try:
            # Validate image path
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': f'Image not found: {image_path}'
                }
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Open image
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            # Get image name without extension
            image_name = Path(image_path).stem
            image_ext = Path(image_path).suffix
            
            # Calculate stride (step size)
            stride_x = window_width - overlap_x
            stride_y = window_height - overlap_y
            
            if stride_x <= 0 or stride_y <= 0:
                return {
                    'success': False,
                    'error': 'Overlap must be less than window size'
                }
            
            # Generate crops
            crops = []
            crop_count = 0
            
            y = 0
            row = 0
            while y < img_height:
                x = 0
                col = 0
                
                # Adjust y to not exceed image bounds
                y_end = min(y + window_height, img_height)
                y_start = max(0, y_end - window_height) if y_end == img_height else y
                
                while x < img_width:
                    # Adjust x to not exceed image bounds
                    x_end = min(x + window_width, img_width)
                    x_start = max(0, x_end - window_width) if x_end == img_width else x
                    
                    # Crop image
                    crop = img.crop((x_start, y_start, x_end, y_end))
                    
                    # Generate output filename
                    output_filename = f"{image_name}_r{row}_c{col}_x{x_start}_y{y_start}{image_ext}"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Save crop
                    crop.save(output_path)
                    
                    crops.append({
                        'filename': output_filename,
                        'x': x_start,
                        'y': y_start,
                        'width': x_end - x_start,
                        'height': y_end - y_start
                    })
                    
                    crop_count += 1
                    col += 1
                    
                    # Move to next column
                    x += stride_x
                    if x >= img_width:
                        break
                
                row += 1
                # Move to next row
                y += stride_y
                if y >= img_height:
                    break
            
            return {
                'success': True,
                'image': image_name,
                'original_size': {'width': img_width, 'height': img_height},
                'window_size': {'width': window_width, 'height': window_height},
                'overlap': {'x': overlap_x, 'y': overlap_y},
                'crops_count': crop_count,
                'crops': crops
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def crop_folder_sliding_window(
        self,
        input_dir: str,
        output_dir: str,
        window_width: int = 1024,
        window_height: int = 1024,
        overlap_x: int = 512,
        overlap_y: int = 512
    ) -> Dict:
        """
        Crop all images in a folder using sliding window
        
        Args:
            input_dir: Directory containing input images
            output_dir: Directory to save cropped images
            window_width: Width of cropping window
            window_height: Height of cropping window
            overlap_x: Horizontal overlap between windows
            overlap_y: Vertical overlap between windows
            
        Returns:
            Dictionary with cropping results
        """
        try:
            # Validate input directory
            if not os.path.exists(input_dir):
                return {
                    'success': False,
                    'error': f'Input directory not found: {input_dir}'
                }
            
            # Get all image files
            image_files = []
            for ext in self.supported_formats:
                image_files.extend(Path(input_dir).glob(f'*{ext}'))
                image_files.extend(Path(input_dir).glob(f'*{ext.upper()}'))
            
            if not image_files:
                return {
                    'success': False,
                    'error': f'No images found in {input_dir}'
                }
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Process each image
            results = []
            total_crops = 0
            processed_count = 0
            failed_count = 0
            errors = []
            
            for image_file in image_files:
                result = self.crop_image_sliding_window(
                    image_path=str(image_file),
                    output_dir=output_dir,
                    window_width=window_width,
                    window_height=window_height,
                    overlap_x=overlap_x,
                    overlap_y=overlap_y
                )
                
                if result['success']:
                    results.append(result)
                    total_crops += result['crops_count']
                    processed_count += 1
                else:
                    failed_count += 1
                    errors.append(f"{image_file.name}: {result['error']}")
            
            return {
                'success': True,
                'processed': processed_count,
                'failed': failed_count,
                'total_images': len(image_files),
                'total_crops': total_crops,
                'window_size': {'width': window_width, 'height': window_height},
                'overlap': {'x': overlap_x, 'y': overlap_y},
                'results': results,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
