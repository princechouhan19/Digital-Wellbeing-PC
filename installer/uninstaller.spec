# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

icon = os.path.abspath('assets/icon.ico') if os.path.exists('assets/icon.ico') else (os.path.abspath('assets/icons/app_icon.ico') if os.path.exists('assets/icons/app_icon.ico') else None)
version_file = os.path.abspath(os.path.join(SPECPATH, 'uninstaller_version_info.txt')) if os.path.exists(os.path.join(SPECPATH, 'uninstaller_version_info.txt')) else None

datas = []
if os.path.exists('assets/icons/app_icon.png'):
    datas.append((os.path.abspath('assets/icons/app_icon.png'), 'assets/icons'))
if os.path.exists('assets/icons/app_icon.ico'):
    datas.append((os.path.abspath('assets/icons/app_icon.ico'), 'assets/icons'))
if os.path.exists('assets/icon.ico'):
    datas.append((os.path.abspath('assets/icon.ico'), 'assets'))

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
    [os.path.abspath(os.path.join(SPECPATH, 'uninstaller_app.py'))],
    pathex=[os.path.abspath(SPECPATH)],
    binaries=[], datas=datas, hiddenimports=['branding'],
    hookspath=[], runtime_hooks=[], excludes=excludes, noarchive=False,
)

# Strip out unnecessary heavy binaries (e.g. 20MB software opengl, QML, network, pdf)
UNWANTED_BINARIES = {
    'opengl32sw.dll', 'qt6quick.dll', 'qt6qml.dll', 'qt6pdf.dll',
    'qt6opengl.dll', 'qt6network.dll', 'qt6virtualkeyboard.dll',
    'qt6qmlmodels.dll', 'qt6qmlmeta.dll', 'libcrypto-3.dll', 'libssl-3.dll',
    'qtiff.dll', 'qwebp.dll', 'qdirect2d.dll', 'qopensslbackend.dll',
    'qschannelbackend.dll', 'd3dcompiler_47.dll', 'opengl32.dll'
}
a.binaries = [x for x in a.binaries if os.path.basename(x[0]).lower() not in UNWANTED_BINARIES]
a.datas = [x for x in a.datas if not any(k in x[0].lower() for k in ['translations', 'qml', 'qtquick'])]

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    [], name='Uninstall Digital Wellbeing', console=False, disable_windowed_traceback=False,
    icon=icon, version=version_file, upx=False,
)
