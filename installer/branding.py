"""Shared branding assets and helpers for Digital Wellbeing Setup."""
import base64, sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath

def get_logo_pixmap(size=None, rounded_radius=None):
    pix = None
    search_paths = []
    if getattr(sys, '_MEIPASS', None):
        search_paths.append(Path(sys._MEIPASS) / 'assets' / 'icons' / 'app_icon.png')
        search_paths.append(Path(sys._MEIPASS) / 'payload' / 'assets' / 'icons' / 'app_icon.png')
        search_paths.append(Path(sys._MEIPASS) / 'assets' / 'icons' / 'app_icon.ico')
    search_paths.extend([
        Path(__file__).resolve().parent.parent / 'assets' / 'icons' / 'app_icon.png',
        Path(__file__).resolve().parent.parent / 'assets' / 'icons' / 'app_icon.ico',
        Path(__file__).resolve().parent.parent / 'assets' / 'icon.ico',
        Path(__file__).resolve().parent / 'payload' / 'assets' / 'icons' / 'app_icon.png',
        Path(sys.executable).resolve().parent / 'assets' / 'icons' / 'app_icon.png',
    ])
    for p in search_paths:
        if p.is_file():
            loaded = QPixmap(str(p))
            if not loaded.isNull():
                pix = loaded
                break

    if size and pix and not pix.isNull():
        scaled = pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if rounded_radius is None:
            rounded_radius = max(4, int(size * 0.20))
        if rounded_radius > 0:
            out = QPixmap(scaled.size())
            out.fill(Qt.transparent)
            painter = QPainter(out)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, scaled.width(), scaled.height(), rounded_radius, rounded_radius)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            return out
        return scaled
    return pix

def get_app_icon():
    ico_paths = []
    if getattr(sys, '_MEIPASS', None):
        ico_paths.append(Path(sys._MEIPASS) / 'assets' / 'icons' / 'app_icon.ico')
        ico_paths.append(Path(sys._MEIPASS) / 'payload' / 'assets' / 'icons' / 'app_icon.ico')
    ico_paths.extend([
        Path(__file__).resolve().parent.parent / 'assets' / 'icons' / 'app_icon.ico',
        Path(__file__).resolve().parent.parent / 'assets' / 'icon.ico',
        Path(__file__).resolve().parent / 'payload' / 'assets' / 'icons' / 'app_icon.ico',
        Path(sys.executable).resolve().parent / 'assets' / 'icons' / 'app_icon.ico',
    ])
    for ip in ico_paths:
        if ip.is_file():
            ico = QIcon(str(ip))
            if not ico.isNull():
                return ico
    ico = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        px = get_logo_pixmap(s)
        if px and not px.isNull():
            ico.addPixmap(px)
    return ico
