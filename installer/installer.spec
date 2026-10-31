# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

payload = Path(os.environ.get('DW_PAYLOAD') or
               os.path.join(SPECPATH, '..', 'build', 'installer_payload')).resolve()
if not payload.is_dir():
    raise SystemExit('Payload not found: %s\nRun installer/build_installer.ps1 first.' % payload)

datas = []
for p in sorted(payload.rglob('*')):
    if p.is_file():
        rel_parent = p.relative_to(payload).parent
        dest_dir = str(Path('payload') / rel_parent)
        datas.append((str(p), dest_dir))

if os.path.exists('assets/icons/app_icon.png'):
    datas.append((os.path.abspath('assets/icons/app_icon.png'), 'assets/icons'))
if os.path.exists('assets/icons/app_icon.ico'):
    datas.append((os.path.abspath('assets/icons/app_icon.ico'), 'assets/icons'))
if os.path.exists('assets/icon.ico'):
    datas.append((os.path.abspath('assets/icon.ico'), 'assets'))
if os.path.exists('version.json'):
    datas.append((os.path.abspath('version.json'), '.'))

icon = os.path.abspath('assets/icon.ico') if os.path.exists('assets/icon.ico') else (os.path.abspath('assets/icons/app_icon.ico') if os.path.exists('assets/icons/app_icon.ico') else None)
version_file = os.path.abspath(os.path.join(SPECPATH, 'installer_version_info.txt')) if os.path.exists(os.path.join(SPECPATH, 'installer_version_info.txt')) else None

excludes = [
    'tkinter', 'unittest', 'test', 'distutils',
    'PySide6.QtNetwork', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf',
    'PySide6.QtPdfWidgets', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
    'PySide6.QtVirtualKeyboard', 'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets', 'PySide6.QtDesigner', 'PySide6.QtHelp',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtPositioning',
    'PySide6.QtPrintSupport', 'PySide6.QtRemoteObjects', 'PySide6.QtSensors',
    'PySide6.QtSerialPort', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtXml',
    'PySide6.QtSpatialAudio', 'numpy', 'pyqtgraph', 'PIL', 'psutil',
    'comtypes', 'uiautomation', 'winrt', 'matplotlib', 'pandas', 'scipy',
    'sqlite3', 'ssl', '_ssl', 'email', 'http', 'xml', 'xmlrpc', 'multiprocessing'
]

a = Analysis(
    [os.path.abspath(os.path.join(SPECPATH, 'installer_app.py'))],
    pathex=[os.path.abspath(SPECPATH)],
    binaries=[], datas=datas, hiddenimports=['branding', 'win32com.client'],
    hookspath=[], runtime_hooks=[], excludes=excludes, noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    [], name='Digital Wellbeing Setup', console=False, disable_windowed_traceback=False,
    icon=icon, version=version_file, upx=False,
)
