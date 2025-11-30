#!/usr/bin/env python3
"""
Self Tools - 数据集格式转换和图像处理工具集
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
    webbrowser.open('http://127.0.0.1:5000')


def main():
    """主函数"""
    print("=" * 60)
    print("Self Tools - 数据集格式转换和图像处理工具集")
    print("=" * 60)
    print("\n正在启动服务器...")
    print("服务器地址: http://127.0.0.1:5000")
    print("\n按 Ctrl+C 停止服务器\n")
    
    # 在新线程中打开浏览器
    threading.Thread(target=open_browser, daemon=True).start()
    
    # 启动 Flask 应用
    try:
        app.run(host='127.0.0.1', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        sys.exit(0)


if __name__ == '__main__':
    main()
