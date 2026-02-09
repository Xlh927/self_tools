import os
import shutil
import concurrent.futures
from pathlib import Path

try:
    from parallelism_config import get_executor_plan
except Exception:  # pragma: no cover - import path differs by runtime entrypoint
    from backend.parallelism_config import get_executor_plan


class ImageMatcher:
    def __init__(self):
        pass

    @staticmethod
    def _process_source_file_task(
        file_path_str,
        reference_stems,
        intersection_dir_str,
        difference_dir_str,
        copy_intersection,
        copy_difference,
        dry_run
    ):
        file_path = Path(file_path_str)
        intersection_dir = Path(intersection_dir_str) if intersection_dir_str else None
        difference_dir = Path(difference_dir_str) if difference_dir_str else None

        result = {
            'matched': False,
            'copied_intersection': None,
            'copied_difference': None,
            'error': None,
            'file_name': file_path.name,
        }

        is_match = file_path.stem in reference_stems
        result['matched'] = is_match

        try:
            if is_match and copy_intersection:
                dest_path = intersection_dir / file_path.name
                if not dry_run:
                    shutil.copy2(file_path, dest_path)
                result['copied_intersection'] = file_path.name
            elif (not is_match) and copy_difference:
                dest_path = difference_dir / file_path.name
                if not dry_run:
                    shutil.copy2(file_path, dest_path)
                result['copied_difference'] = file_path.name
        except Exception as e:
            scope = "intersection" if is_match else "difference"
            result['error'] = f"Failed to copy {scope} {file_path.name}: {str(e)}"

        return result

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
        plan = get_executor_plan(total_files, workload='io', prefer_process=False)
        if plan.kind == 'serial':
            for file_path in source_files:
                result = self._process_source_file_task(
                    str(file_path),
                    reference_stems,
                    str(intersection_dir) if copy_intersection else None,
                    str(difference_dir) if copy_difference else None,
                    copy_intersection,
                    copy_difference,
                    dry_run,
                )
                stats['total_scanned'] += 1
                if result['matched']:
                    stats['matched_count'] += 1
                else:
                    stats['unmatched_count'] += 1
                if result['copied_intersection']:
                    stats['copied_intersection'].append(result['copied_intersection'])
                if result['copied_difference']:
                    stats['copied_difference'].append(result['copied_difference'])
                if result['error']:
                    stats['errors'].append(result['error'])

                if progress_callback:
                    progress_callback(stats['total_scanned'], total_files, f"Processed {file_path.name}")
        else:
            executor_cls = (
                concurrent.futures.ProcessPoolExecutor
                if plan.kind == 'process'
                else concurrent.futures.ThreadPoolExecutor
            )
            with executor_cls(max_workers=plan.workers) as executor:
                future_to_file = {
                    executor.submit(
                        self._process_source_file_task,
                        str(file_path),
                        reference_stems,
                        str(intersection_dir) if copy_intersection else None,
                        str(difference_dir) if copy_difference else None,
                        copy_intersection,
                        copy_difference,
                        dry_run,
                    ): file_path
                    for file_path in source_files
                }
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    result = future.result()
                    stats['total_scanned'] += 1
                    if result['matched']:
                        stats['matched_count'] += 1
                    else:
                        stats['unmatched_count'] += 1
                    if result['copied_intersection']:
                        stats['copied_intersection'].append(result['copied_intersection'])
                    if result['copied_difference']:
                        stats['copied_difference'].append(result['copied_difference'])
                    if result['error']:
                        stats['errors'].append(result['error'])

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
