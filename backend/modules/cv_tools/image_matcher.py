import os
import shutil
from pathlib import Path

class ImageMatcher:
    def __init__(self):
        pass

    def match_and_copy(self, source_dir, reference_dir, output_dir, copy_intersection=True, copy_difference=False, dry_run=False, progress_callback=None):
        """
        Find images in source_dir that have the same stem as files in reference_dir.
        
        Args:
            source_dir: Directory containing source images
            reference_dir: Directory containing reference files (to match by filename)
            output_dir: Base directory for output
            copy_intersection: Whether to copy matched files (default: True)
            copy_difference: Whether to copy unmatched files (default: False)
            dry_run: If True, do not actually copy files
        """
        source_path = Path(source_dir)
        reference_path = Path(reference_dir)
        output_path = Path(output_dir)

        if not source_path.exists():
            return {'success': False, 'error': f'Source directory not found: {source_dir}'}
        if not reference_path.exists():
            return {'success': False, 'error': f'Reference directory not found: {reference_dir}'}
        
        # Define subdirectories
        intersection_dir = output_path / 'intersection'
        difference_dir = output_path / 'difference'

        if not dry_run:
            if copy_intersection:
                intersection_dir.mkdir(parents=True, exist_ok=True)
            if copy_difference:
                difference_dir.mkdir(parents=True, exist_ok=True)

        # Get reference stems
        reference_stems = {f.stem for f in reference_path.iterdir() if f.is_file()}

        stats = {
            'total_scanned': 0,
            'matched_count': 0,
            'unmatched_count': 0,
            'copied_intersection': [],
            'copied_difference': [],
            'errors': []
        }

        # Iterate source files
        source_files = [p for p in source_path.iterdir() if p.is_file() and not p.name.startswith('.')]
        total_files = len(source_files)
        for file_path in source_files:
            
            stats['total_scanned'] += 1
            
            # Check if stem exists in reference
            is_match = file_path.stem in reference_stems
            
            if is_match:
                stats['matched_count'] += 1
                if copy_intersection:
                    dest_path = intersection_dir / file_path.name
                    try:
                        if not dry_run:
                            shutil.copy2(file_path, dest_path)
                        stats['copied_intersection'].append(str(file_path.name))
                    except Exception as e:
                        stats['errors'].append(f"Failed to copy intersection {file_path.name}: {str(e)}")
            else:
                stats['unmatched_count'] += 1
                if copy_difference:
                    dest_path = difference_dir / file_path.name
                    try:
                        if not dry_run:
                            shutil.copy2(file_path, dest_path)
                        stats['copied_difference'].append(str(file_path.name))
                    except Exception as e:
                        stats['errors'].append(f"Failed to copy difference {file_path.name}: {str(e)}")
            
            if progress_callback:
                progress_callback(stats['total_scanned'], total_files, f"Processed {file_path.name}")

        return {
            'success': True,
            'total_scanned': stats['total_scanned'],
            'reference_count': len(reference_stems),
            'matched_count': stats['matched_count'],
            'unmatched_count': stats['unmatched_count'],
            'copied_intersection_count': len(stats['copied_intersection']),
            'copied_difference_count': len(stats['copied_difference']),
            'errors': stats['errors'],
            'dry_run': dry_run,
            'output_dir': str(output_path)
        }
