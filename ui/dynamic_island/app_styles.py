"""
app_styles.py — Precision QSS styling for Dynamic Island.
Cloned and refined from https://github.com/rajsriv/dynamic-island-for-windows
"""
from __future__ import annotations


def get_stylesheet(accent_color: str = "#00A0FF") -> str:
    return f"""
    QWidget#IslandWidget {{
        background-color: transparent;
        border: none;
    }}
    
    QLabel {{
        color: white;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter Display', 'Inter', 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    }}
    
    QLabel#TitleLabel {{
        font-size: 13px;
        font-weight: 600;
        color: #FFFFFF;
    }}
    
    QLabel#SubtitleLabel {{
        font-size: 11px;
        color: #A0A0A0;
    }}
    
    QLabel#compact_time_digits {{
        font-size: 12px;
        font-weight: 600;
        color: #FFFFFF;
        letter-spacing: 0.2px;
    }}

    QLabel#compact_battery_digits {{
        font-size: 11px;
        font-weight: 600;
        color: #FFFFFF;
        letter-spacing: 0.1px;
    }}

    QLabel#compact_title {{
        font-size: 12px;
        font-weight: 600;
        color: #FFFFFF;
        max-width: 140px;
        max-height: 22px;
    }}

    QLabel#basics_title {{
        font-size: 13px;
        font-weight: 700;
        color: #E5E7EB;
        letter-spacing: 0.5px;
    }}

    QLabel#exp_media_title {{
        font-size: 13px;
        font-weight: 700;
        color: #FFFFFF;
    }}

    QLabel#exp_media_artist {{
        font-size: 11px;
        font-weight: 500;
        color: #9CA3AF;
    }}

    QLabel#exp_time_remain {{
        font-size: 11px;
        font-weight: 600;
        color: #A1A1AA;
        padding-right: 2px;
    }}

    QLabel#idle_clock {{
        font-size: 12px;
        font-weight: 600;
        color: #F3F4F6;
    }}

    QLabel#idle_battery {{
        font-size: 11px;
        font-weight: 500;
        color: #9CA3AF;
    }}

    QLabel#vol_label {{
        font-size: 12px;
        font-weight: 600;
        color: #FFFFFF;
    }}

    QLabel#vol_percent {{
        font-size: 11px;
        font-weight: 600;
        color: #9CA3AF;
    }}

    QLabel#exp_task_title {{
        font-size: 13px;
        font-weight: 700;
        color: #FFFFFF;
    }}

    QLabel#priority_tag {{
        font-size: 10px;
        font-weight: 700;
        color: {accent_color};
        background: rgba(255, 255, 255, 12);
        padding: 1px 6px;
        border-radius: 4px;
    }}

    QLabel#notch_target_label, QLabel#notch_next_task {{
        font-size: 10px;
        color: #9CA3AF;
    }}
    
    QLabel#IconLabel {{
        background-color: transparent;
        font-size: 16px;
    }}
    
    QPushButton#MediaButton {{
        background-color: transparent;
        color: white;
        border-radius: 14px;
        border: none;
        width: 28px;
        height: 28px;
        padding: 2px;
    }}
    
    QPushButton#MediaButton:hover {{
        background-color: rgba(255, 255, 255, 30);
    }}
    
    QPushButton#MediaButton:pressed {{
        background-color: rgba(255, 255, 255, 50);
    }}
    
    QLabel#PerfLabel {{
        font-size: 11px;
        color: #CCCCCC;
        font-weight: 600;
    }}

    QPushButton#ActionButton {{
        background-color: rgba(255, 255, 255, 15);
        color: white;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 10);
    }}
    
    QPushButton#ActionButton:hover {{
        background-color: rgba(255, 255, 255, 35);
        border: 1px solid rgba(255, 255, 255, 40);
    }}

    QPushButton#ActionButton:pressed {{
        background-color: rgba(255, 255, 255, 50);
    }}

    QPushButton#ControlBall {{
        background-color: #000000;
        color: white;
        border-radius: 20px;
        border: 1.2px solid rgba(255, 255, 255, 40);
        width: 40px;
        height: 40px;
        font-size: 18px;
    }}

    QPushButton#ControlBall:hover {{
        background-color: rgba(40, 40, 40, 255);
        border: 1.5px solid rgba(255, 255, 255, 80);
    }}

    QPushButton#NavButton {{
        background-color: transparent;
        color: #888;
        border: none;
        font-size: 16px;
        padding: 0px 5px;
    }}

    QPushButton#NavButton:hover {{
        color: white;
    }}

    QProgressBar {{
        background-color: #222222;
        border-radius: 2px;
        border: none;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00FF80, stop:1 #80FF00);
        border-radius: 2px;
    }}

    QListWidget {{
        background: transparent;
        border: none;
    }}
    QListWidget::item {{
        background: rgba(255, 255, 255, 10);
        border-radius: 10px;
        padding: 8px 10px;
        margin-bottom: 4px;
        color: white;
    }}
    QListWidget::item:selected {{
        border: 1px solid {accent_color};
        background: rgba(255, 255, 255, 20);
    }}

    QLineEdit, QComboBox {{
        background-color: rgba(255, 255, 255, 12);
        border: 1px solid rgba(255, 255, 255, 15);
        border-radius: 8px;
        color: white;
        padding: 8px 10px;
        font-size: 12px;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 1px solid {accent_color};
    }}

    QPushButton#DialogBtn {{
        background-color: rgba(255, 255, 255, 10);
        color: white;
        border: 1px solid rgba(255, 255, 255, 15);
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 600;
        font-size: 12px;
    }}
    QPushButton#DialogBtn:hover {{
        background-color: rgba(255, 255, 255, 20);
    }}
    """
