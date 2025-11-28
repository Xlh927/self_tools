import os
import shutil
from pathlib import Path

class ImageMatcher:
    def __init__(self):
        pass

    def match_and_copy(self, source_dir, reference_dir, output_dir, dry_run=False):
        """
        Find images in source_dir that have the same stem as files in reference_dir
        and copy them to output_dir.
        """
        source_path = Path(source_dir)
        reference_path = Path(reference_dir)
        output_path = Path(output_dir)

        if not source_path.exists():
            return {'success': False, 'error': f'Source directory not found: {source_dir}'}
        if not reference_path.exists():
            return {'success': False, 'error': f'Reference directory not found: {reference_dir}'}
        
        if not dry_run:
            output_path.mkdir(parents=True, exist_ok=True)

        # Get reference stems
        # We consider any file in reference dir as a potential match target
        reference_stems = {f.stem for f in reference_path.iterdir() if f.is_file()}

        matched_count = 0
        copied_files = []
        errors = []

        # Iterate source files
        for file_path in source_path.iterdir():
            if not file_path.is_file():
                continue
            
            # Check if stem exists in reference
            if file_path.stem in reference_stems:
                matched_count += 1
                dest_path = output_path / file_path.name
                
                try:
                    if not dry_run:
                        shutil.copy2(file_path, dest_path)
                    copied_files.append(str(file_path.name))
                except Exception as e:
                    errors.append(f"Failed to copy {file_path.name}: {str(e)}")

        return {
            'success': True,
            'total_scanned': sum(1 for _ in source_path.iterdir() if _.is_file()),
            'reference_count': len(reference_stems),
            'matched_count': matched_count,
            'copied_files': copied_files,
            'errors': errors,
            'dry_run': dry_run
        }
