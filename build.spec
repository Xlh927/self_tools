# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# 获取项目根目录
root_dir = Path.cwd()

# 收集所有需要的数据文件（避免打入 node_modules 等开发依赖）
datas = []

def add_data(src: Path, dst: str):
    if src.exists():
        datas.append((str(src), dst))

add_data(root_dir / 'frontend' / 'index.html', 'frontend')
add_data(root_dir / 'frontend' / 'image-viewer.html', 'frontend')
add_data(root_dir / 'frontend' / 'cv-tools.html', 'frontend')
add_data(root_dir / 'frontend' / 'assets', 'frontend/assets')
add_data(root_dir / 'frontend' / 'src' / 'styles', 'frontend/src/styles')
add_data(root_dir / 'frontend' / 'dist', 'frontend/dist')
add_data(root_dir / 'backend' / 'modules', 'backend/modules')

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
