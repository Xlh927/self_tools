"""
Image Deduplicator Module
Detects and removes duplicate images using perceptual hashing algorithms.
"""

import os
import hashlib
from PIL import Image
import imagehash
from collections import defaultdict
from typing import List, Dict, Tuple, Optional


class ImageDeduplicator:
    """
    Image deduplication using perceptual hashing.
    Supports multiple hash algorithms: average, perceptual, difference, wavelet.
    """

    def __init__(self, hash_size: int = 8):
        """
        Initialize the ImageDeduplicator.
        
        Args:
            hash_size: Hash size for perceptual hashing (default: 8)
        """
        self.hash_size = hash_size
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}

    def calculate_hash(self, image_path: str, hash_algorithm: str = 'average') -> Optional[str]:
        """
        Calculate perceptual hash for an image.
        
        Args:
            image_path: Path to the image file
            hash_algorithm: Hash algorithm to use ('average', 'perceptual', 'difference', 'wavelet')
            
        Returns:
            Hash string or None if error occurs
        """
        try:
            img = Image.open(image_path)
            
            if hash_algorithm == 'average':
                img_hash = imagehash.average_hash(img, hash_size=self.hash_size)
            elif hash_algorithm == 'perceptual':
                img_hash = imagehash.phash(img, hash_size=self.hash_size)
            elif hash_algorithm == 'difference':
                img_hash = imagehash.dhash(img, hash_size=self.hash_size)
            elif hash_algorithm == 'wavelet':
                img_hash = imagehash.whash(img, hash_size=self.hash_size)
            else:
                raise ValueError(f"Unsupported hash algorithm: {hash_algorithm}")
            
            return str(img_hash)
        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
            return None

    def calculate_md5(self, file_path: str) -> Optional[str]:
        """
        Calculate MD5 hash for exact duplicate detection.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash string or None if error occurs
        """
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"Error calculating MD5 for {file_path}: {str(e)}")
            return None

    def find_duplicates(self, 
                       folder_path: str, 
                       hash_algorithm: str = 'average',
                       use_md5: bool = False,
                       similarity_threshold: int = 5) -> Dict[str, List[str]]:
        """
        Find duplicate images in a folder.
        
        Args:
            folder_path: Path to the folder containing images
            hash_algorithm: Hash algorithm to use for perceptual hashing
            use_md5: If True, use MD5 for exact duplicates; if False, use perceptual hashing
            similarity_threshold: Maximum hamming distance for considering images as duplicates (for perceptual hash)
            
        Returns:
            Dictionary mapping hash values to list of image paths with that hash
        """
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder not found: {folder_path}")
        
        hash_map = defaultdict(list)
        processed = 0
        errors = 0
        
        print(f"🔍 Scanning folder: {folder_path}")
        print(f"Algorithm: {'MD5 (exact)' if use_md5 else f'{hash_algorithm} hash (similarity)'}")
        
        # Walk through all files in the folder
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                
                # Check if file is a supported image format
                if ext not in self.supported_formats:
                    continue
                
                # Calculate hash
                if use_md5:
                    file_hash = self.calculate_md5(file_path)
                else:
                    file_hash = self.calculate_hash(file_path, hash_algorithm)
                
                if file_hash:
                    hash_map[file_hash].append(file_path)
                    processed += 1
                else:
                    errors += 1
                
                if processed % 100 == 0:
                    print(f"Processed {processed} images...")
        
        print(f"✅ Processed {processed} images, {errors} errors")
        
        # Filter for duplicates only
        duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}
        
        # For perceptual hashing, also check for similar hashes
        if not use_md5 and similarity_threshold > 0:
            duplicates = self._find_similar_hashes(hash_map, similarity_threshold)
        
        return duplicates

    def _find_similar_hashes(self, hash_map: Dict[str, List[str]], threshold: int) -> Dict[str, List[str]]:
        """
        Find groups of similar hashes based on Hamming distance threshold.
        
        Args:
            hash_map: Dictionary of hash to file paths
            threshold: Maximum Hamming distance to consider as duplicate
            
        Returns:
            Dictionary of grouped similar images
        """
        hashes = list(hash_map.keys())
        groups = []
        used = set()
        
        for i, hash1 in enumerate(hashes):
            if hash1 in used:
                continue
            
            group = hash_map[hash1].copy()
            used.add(hash1)
            
            for j in range(i + 1, len(hashes)):
                hash2 = hashes[j]
                if hash2 in used:
                    continue
                
                # Calculate Hamming distance
                distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
                
                if distance <= threshold:
                    group.extend(hash_map[hash2])
                    used.add(hash2)
            
            if len(group) > 1:
                groups.append(group)
        
        # Convert to dictionary format
        result = {}
        for idx, group in enumerate(groups):
            result[f"group_{idx}"] = group
        
        return result

    def remove_duplicates(self, 
                         duplicates: Dict[str, List[str]], 
                         keep_strategy: str = 'first',
                         dry_run: bool = True) -> Dict[str, any]:
        """
        Remove duplicate images.
        
        Args:
            duplicates: Dictionary of duplicate groups from find_duplicates()
            keep_strategy: Strategy for keeping images ('first', 'last', 'smallest', 'largest')
            dry_run: If True, only simulate removal without actually deleting files
            
        Returns:
            Dictionary with statistics about removed files
        """
        removed_files = []
        kept_files = []
        total_space_saved = 0
        
        for group_id, image_paths in duplicates.items():
            if len(image_paths) <= 1:
                continue
            
            # Determine which file to keep
            keep_file = self._select_file_to_keep(image_paths, keep_strategy)
            kept_files.append(keep_file)
            
            # Remove the rest
            for file_path in image_paths:
                if file_path != keep_file:
                    file_size = os.path.getsize(file_path)
                    total_space_saved += file_size
                    
                    if not dry_run:
                        try:
                            os.remove(file_path)
                            removed_files.append(file_path)
                            print(f"🗑️  Deleted: {file_path}")
                        except Exception as e:
                            print(f"❌ Error deleting {file_path}: {str(e)}")
                    else:
                        removed_files.append(file_path)
                        print(f"[DRY RUN] Would delete: {file_path}")
        
        return {
            'removed_count': len(removed_files),
            'kept_count': len(kept_files),
            'removed_files': removed_files,
            'kept_files': kept_files,
            'space_saved_bytes': total_space_saved,
            'space_saved_mb': round(total_space_saved / (1024 * 1024), 2),
            'dry_run': dry_run
        }

    def _select_file_to_keep(self, file_paths: List[str], strategy: str) -> str:
        """
        Select which file to keep based on strategy.
        
        Args:
            file_paths: List of duplicate file paths
            strategy: Selection strategy
            
        Returns:
            Path of the file to keep
        """
        if strategy == 'first':
            return file_paths[0]
        elif strategy == 'last':
            return file_paths[-1]
        elif strategy == 'smallest':
            return min(file_paths, key=lambda x: os.path.getsize(x))
        elif strategy == 'largest':
            return max(file_paths, key=lambda x: os.path.getsize(x))
        else:
            return file_paths[0]

    def get_duplicate_report(self, duplicates: Dict[str, List[str]]) -> Dict[str, any]:
        """
        Generate a detailed report about duplicates found.
        
        Args:
            duplicates: Dictionary of duplicate groups
            
        Returns:
            Dictionary with statistics
        """
        total_duplicates = sum(len(paths) - 1 for paths in duplicates.values())
        total_files = sum(len(paths) for paths in duplicates.values())
        potential_space_saved = 0
        
        for paths in duplicates.values():
            if len(paths) > 1:
                # Calculate space that would be saved by keeping only one
                sizes = [os.path.getsize(p) for p in paths]
                potential_space_saved += sum(sizes) - min(sizes)
        
        return {
            'duplicate_groups': len(duplicates),
            'total_duplicate_files': total_duplicates,
            'total_files_in_groups': total_files,
            'potential_space_saved_bytes': potential_space_saved,
            'potential_space_saved_mb': round(potential_space_saved / (1024 * 1024), 2),
            'groups': [
                {
                    'id': group_id,
                    'count': len(paths),
                    'files': [
                        {
                            'path': p,
                            'size_bytes': os.path.getsize(p),
                            'size_mb': round(os.path.getsize(p) / (1024 * 1024), 2)
                        } for p in paths
                    ]
                } for group_id, paths in duplicates.items()
            ]
        }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python image_deduplicator.py <folder_path> [--hash-algorithm=average] [--use-md5] [--remove] [--keep=first]")
        sys.exit(1)
    
    folder = sys.argv[1]
    hash_algo = 'average'
    use_md5 = False
    do_remove = False
    keep_strategy = 'first'
    
    # Parse arguments
    for arg in sys.argv[2:]:
        if arg.startswith('--hash-algorithm='):
            hash_algo = arg.split('=')[1]
        elif arg == '--use-md5':
            use_md5 = True
        elif arg == '--remove':
            do_remove = True
        elif arg.startswith('--keep='):
            keep_strategy = arg.split('=')[1]
    
    deduplicator = ImageDeduplicator()
    
    # Find duplicates
    print("\n" + "="*60)
    duplicates = deduplicator.find_duplicates(folder, hash_algorithm=hash_algo, use_md5=use_md5)
    
    # Generate report
    report = deduplicator.get_duplicate_report(duplicates)
    
    print("\n" + "="*60)
    print("📊 DUPLICATE DETECTION REPORT")
    print("="*60)
    print(f"Duplicate groups found: {report['duplicate_groups']}")
    print(f"Total duplicate files: {report['total_duplicate_files']}")
    print(f"Potential space savings: {report['potential_space_saved_mb']} MB")
    print("="*60)
    
    # Remove duplicates if requested
    if do_remove:
        print("\n⚠️  REMOVING DUPLICATES...")
        result = deduplicator.remove_duplicates(duplicates, keep_strategy=keep_strategy, dry_run=False)
        print(f"\n✅ Removed {result['removed_count']} files")
        print(f"💾 Space saved: {result['space_saved_mb']} MB")
    else:
        print("\n💡 Run with --remove flag to delete duplicates")
        print("💡 Use --keep=first|last|smallest|largest to choose which file to keep")
