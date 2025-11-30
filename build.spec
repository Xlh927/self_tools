# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# 获取项目根目录
root_dir = Path.cwd()

# 收集所有需要的数据文件
datas = [
    (str(root_dir / 'frontend'), 'frontend'),  # 前端文件
    (str(root_dir / 'backend' / 'modules'), 'backend/modules'),  # 后端模块
]

# 收集所有需要的隐藏导入
hiddenimports = [
    'flask',
    'PIL',
    'shapely',
    'imagehash',
    'xml.etree.ElementTree',
    'json',
    'uuid',
    'threading',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='self_tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
