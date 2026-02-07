from typing import Optional


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
