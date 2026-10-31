# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

datas = [
    ('assets', 'assets'),
    ('version.json', '.'),
]

hiddenimports = [
    'winrt.windows.security.credentials.ui',
    'winrt.windows.ui.notifications',
    'winrt.windows.data.xml.dom',
    'winrt.windows.media.control',
    'winrt.windows.storage.streams',
    'requests',
    'PIL',
    'qtawesome',
    'soundcard',
    'cffi',
    'pycaw',
    'uiautomation',
    'numpy',
    'pyqtgraph',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
    'psutil',
    'win32gui',
    'win32process',
    'win32api',
    'win32con',
    'win32event',
    'winerror',
]

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_path = os.path.abspath('assets/icons/app_icon.ico') if os.path.exists('assets/icons/app_icon.ico') else None
version_file = os.path.abspath('file_version_info.txt') if os.path.exists('file_version_info.txt') else None
manifest_file = os.path.abspath('app.manifest') if os.path.exists('app.manifest') else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DigitalWellbeing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    version=version_file,
    manifest=manifest_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DigitalWellbeing',
)
