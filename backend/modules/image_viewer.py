import os
import hashlib
import shutil
import tempfile
from PIL import Image
from typing import List, Dict, Optional
import mimetypes

class ShortcutConfig:
    def __init__(self, data: Optional[dict] = None):
        if data is None:
            self.next = "ArrowDown"
            self.prev = "ArrowUp"
            self.clear = "c"
            self.classes = {
                "1": "zhengbao",
                "2": "wubao"
            }
            self.class_colors = {
                "zhengbao": "#28a745",  # Green
                "wubao": "#dc3545",     # Red
                "3": "#ffc107",         # Yellow
                "4": "#007bff"          # Blue
            }
        else:
            self.next = data.get('next', "ArrowDown")
            self.prev = data.get('prev', "ArrowUp")
            self.clear = data.get('clear', "c")
            self.classes = data.get('classes', {})
            self.class_colors = data.get('class_colors', {})

    def to_dict(self):
        return {
            "next": self.next,
            "prev": self.prev,
            "clear": self.clear,
            "classes": self.classes,
            "class_colors": self.class_colors
        }

class AppConfig:
    def __init__(self, data: Optional[dict] = None):
        if data is None:
            self.shortcuts = ShortcutConfig()
        else:
            self.shortcuts = ShortcutConfig(data.get('shortcuts'))

    def to_dict(self):
        return {
            "shortcuts": self.shortcuts.to_dict()
        }

class ImageViewerManager:
    def __init__(self):
        self.config = AppConfig()
        self.thumbnail_cache_dir = os.path.join(tempfile.gettempdir(), "image_viewer_thumbnails")
        os.makedirs(self.thumbnail_cache_dir, exist_ok=True)

    def get_config(self):
        return self.config.to_dict()

    def update_config(self, data):
        self.config = AppConfig(data)
        return self.config.to_dict()

    def classify_image(self, image_path, class_name):
        if not os.path.exists(image_path):
            return {"success": False, "error": "Image not found"}
        
        image_dir = os.path.dirname(image_path)
        parent_dir = os.path.dirname(image_dir)
        target_dir = os.path.join(parent_dir, class_name)
        filename = os.path.basename(image_path)
        
        # Remove from other folders
        valid_class_names = set(self.config.shortcuts.classes.values())
        if os.path.exists(parent_dir):
            for entry in os.scandir(parent_dir):
                if entry.is_dir() and entry.name != class_name and entry.name != os.path.basename(image_dir):
                    if entry.name in valid_class_names:
                        potential_old_path = os.path.join(entry.path, filename)
                        if os.path.exists(potential_old_path):
                            try:
                                os.remove(potential_old_path)
                            except Exception as e:
                                print(f"Warning: Failed to remove old classification: {e}")
        
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
            except OSError as e:
                return {"success": False, "error": f"Failed to create directory: {e}"}

        target_path = os.path.join(target_dir, filename)

        try:
            shutil.copy2(image_path, target_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to copy image: {e}"}

        return {"success": True, "status": "success", "target_path": target_path, "class_name": class_name}

    def unclassify_image(self, image_path, class_name):
        image_dir = os.path.dirname(image_path)
        parent_dir = os.path.dirname(image_dir)
        target_dir = os.path.join(parent_dir, class_name)
        filename = os.path.basename(image_path)
        target_path = os.path.join(target_dir, filename)
        
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception as e:
                return {"success": False, "error": f"Failed to delete file: {e}"}
                
        return {"success": True, "status": "success", "detail": "Classification removed"}

    def list_images(self, path, sort="name_desc"):
        if not os.path.exists(path):
            return {"success": False, "error": "Directory not found"}
        if not os.path.isdir(path):
            return {"success": False, "error": "Path is not a directory"}

        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.ico'}
        images = []
        try:
            for entry in os.scandir(path):
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in image_extensions:
                    images.append(entry.name)
        except PermissionError:
            return {"success": False, "error": "Permission denied"}

        # Sort
        if sort == "name_asc":
            images.sort(key=lambda x: x.lower())
        elif sort == "name_desc":
            images.sort(key=lambda x: x.lower(), reverse=True)
        elif sort == "date_asc":
            images.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)))
        elif sort == "date_desc":
            images.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
        else:
            images.sort(key=lambda x: x.lower(), reverse=True)
        
        classifications = {}
        parent_dir = os.path.dirname(path)
        valid_class_names = set(self.config.shortcuts.classes.values())
        
        if os.path.exists(parent_dir):
            try:
                for entry in os.scandir(parent_dir):
                    if entry.is_dir() and entry.path != path:
                        if entry.name in valid_class_names:
                            class_name = entry.name
                            for image_filename in images:
                                classified_image_path = os.path.join(entry.path, image_filename)
                                if os.path.exists(classified_image_path):
                                    classifications[image_filename] = class_name
            except PermissionError:
                pass
        
        return {
            "success": True, 
            "images": images, 
            "path": path, 
            "classifications": classifications, 
            "sort": sort
        }

    def generate_cache_key(self, file_path, size):
        try:
            mtime = os.path.getmtime(file_path)
            cache_input = f"{file_path}_{mtime}_{size}"
            return hashlib.md5(cache_input.encode()).hexdigest()
        except:
            return hashlib.md5(file_path.encode()).hexdigest()

    def get_thumbnail_path(self, image_path, size=300):
        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            return None
        
        cache_key = self.generate_cache_key(image_path, size)
        thumbnail_path = os.path.join(self.thumbnail_cache_dir, f"{cache_key}.jpg")

        if os.path.exists(thumbnail_path):
            return thumbnail_path

        try:
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                img.save(thumbnail_path, "JPEG", quality=85, optimize=True)
            
            return thumbnail_path
        except Exception:
            return None

    def clear_thumbnails(self):
        try:
            deleted_count = 0
            if os.path.exists(self.thumbnail_cache_dir):
                for filename in os.listdir(self.thumbnail_cache_dir):
                    file_path = os.path.join(self.thumbnail_cache_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_count += 1
            return {"success": True, "deleted": deleted_count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_thumbnail_stats(self):
        try:
            count = 0
            total_size = 0
            if os.path.exists(self.thumbnail_cache_dir):
                for filename in os.listdir(self.thumbnail_cache_dir):
                    file_path = os.path.join(self.thumbnail_cache_dir, filename)
                    if os.path.isfile(file_path):
                        count += 1
                        total_size += os.path.getsize(file_path)
            
            return {
                "success": True,
                "cache_dir": self.thumbnail_cache_dir,
                "count": count,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

viewer_manager = ImageViewerManager()
