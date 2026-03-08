#!/usr/bin/env python3
"""
Self Tools - CV dataset tooling platform
Main entry point for the packaged application
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from backend.app import app


def open_browser():
    """在服务器启动后打开浏览器"""
    time.sleep(1.5)  # 等待服务器启动
    webbrowser.open('http://127.0.0.1:8080')


def main():
    """主函数"""
    print("=" * 60)
    print("Self Tools - CV 数据集工具平台")
    print("=" * 60)
    print("\n正在启动服务器...")
    print("服务器地址: http://127.0.0.1:8080")
    print("\n按 Ctrl+C 停止服务器\n")
    
    # 在新线程中打开浏览器
    threading.Thread(target=open_browser, daemon=True).start()
    
    # 启动 Flask 应用
    try:
        app.run(host='127.0.0.1', port=8080, debug=False)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        sys.exit(0)


if __name__ == '__main__':
    main()
