"""
focus.py — Externalized QSS for the Focus suite.

Kept separate from FocusTimerWidget so theme changes have one reviewable
surface and the widget file stays focused on behavior.
"""
from __future__ import annotations

from PySide6.QtGui import QColor

from ui import design_system as ds
from ui.theme import ThemeManager


def build_focus_stylesheet(tm: ThemeManager, mode_color: str, is_dark: bool) -> str:
    return f"""
            QFrame#focus_suite_root {{
                background: transparent;
                border: none;
            }}
            QFrame#focus_section_card {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.CARD_RADIUS}px;
            }}
            QFrame#apple_inset_card {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 16px;
            }}
            QLabel#section_eyebrow {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.4px;
            }}
            QLabel#focus_section_sub {{
                font-size: 12px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QLabel#protection_title {{
                font-size: 13px;
                font-weight: 600;
                color: {tm.color('text_main')};
            }}
            QLabel#card_header_title {{
                font-size: 14px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.2px;
            }}
            QLabel#list_subtitle {{
                font-size: 12px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QLabel#rules_count {{
                font-size: 12px;
                font-weight: 600;
                color: {tm.color('accent_tint_text')};
            }}
            QLabel#bridge_status_text {{
                font-size: 11px;
                font-weight: 500;
                color: {tm.color('text_muted')};
            }}
            QLabel#bridge_status_text[state="on"] {{
                color: #30D158;
            }}
            QFrame#guardrail_footer {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
            }}
            QLabel#guardrail_footer_text {{
                color: {tm.color('text_muted')};
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton#text_link_btn {{
                background: transparent;
                border: none;
                color: {tm.color('text_muted')};
                font-size: 11px;
                font-weight: 600;
                padding: 3px 6px;
            }}
            QPushButton#text_link_btn:hover {{
                color: {tm.color('text_main')};
            }}
            QPushButton#guardrail_tab {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: {ds.BUTTON_RADIUS}px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
                padding: 5px 13px;
            }}
            QPushButton#guardrail_tab:hover {{
                color: {tm.color('text_main')};
                background: {tm.color('surface_hover')};
            }}
            QPushButton#guardrail_tab:checked {{
                color: {mode_color};
                background: {tm.color('accent_tint_bg')};
                border: 1px solid {tm.color('accent_tint_border')};
                font-weight: 700;
            }}
            QLabel#mini_eyebrow {{
                font-size: 10px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.2px;
            }}
            
            /* Segmented Controls */
            QFrame#segmented_capsule {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.RADIUS['md']}px;
            }}
            QPushButton#preset_chip {{
                background: transparent;
                border: none;
                border-radius: {ds.BUTTON_RADIUS}px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
                padding: 5px 12px;
            }}
            QPushButton#preset_chip:hover {{
                color: {tm.color('text_main')};
                background: {tm.color('surface_hover')};
            }}
            QPushButton#preset_chip:checked {{
                background: {tm.color('surface_elevated')};
                color: {mode_color};
                font-weight: 700;
                border: 1px solid {tm.color('border')};
            }}
            QPushButton#stepper_btn {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.BUTTON_RADIUS}px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
                padding: 5px 10px;
            }}
            QPushButton#stepper_btn:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
                border-color: {tm.color('border_hover')};
            }}
            
            /* Action Pills */
            QPushButton#action_pill_btn {{
                background-color: rgba(10, 132, 255, 0.12);
                border: 1px solid rgba(10, 132, 255, 0.28);
                border-radius: {ds.BUTTON_RADIUS}px;
                color: #0A84FF;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 12px;
            }}
            QPushButton#action_pill_btn:hover {{
                background-color: rgba(10, 132, 255, 0.22);
            }}
            QPushButton#quick_add_chip {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.BUTTON_RADIUS}px;
                color: {tm.color('text_sub')};
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }}
            QPushButton#quick_add_chip:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
                border-color: {tm.color('accent')};
            }}
            QLineEdit#site_search_input {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.BUTTON_RADIUS}px;
                color: {tm.color('text_main')};
                font-size: 11px;
                padding: 4px 8px;
            }}
            QLineEdit#site_search_input:focus {{
                border-color: {tm.color('accent')};
            }}
            QLabel#count_badge {{
                background: {tm.color('accent_tint_bg')};
                border: 1px solid {tm.color('accent_tint_border')};
                border-radius: 7px;
                color: {tm.color('accent_tint_text')};
                font-size: 10px;
                font-weight: 700;
                padding: 2px 7px;
            }}
            
            /* Primary Buttons */
            QPushButton#primary_start_btn {{
                background-color: {mode_color};
                border: none;
                border-radius: {ds.BUTTON_RADIUS_PILL}px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.3px;
                padding: 10px 22px;
            }}
            QPushButton#primary_start_btn:hover {{
                background-color: {QColor(mode_color).lighter(112).name() if is_dark else QColor(mode_color).darker(108).name()};
            }}
            QPushButton#secondary_pill_btn {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.BUTTON_RADIUS_PILL}px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 10px 18px;
            }}
            QPushButton#secondary_pill_btn:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            
            /* Active Cockpit Styling */
            QFrame#active_focus_pill {{
                background: rgba(175, 82, 222, 0.14);
                border: 1px solid rgba(175, 82, 222, 0.32);
                border-radius: 12px;
            }}
            QLabel#active_pill_text {{
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.5px;
                color: {mode_color};
            }}
            QLabel#active_mode_title {{
                font-size: 14px;
                font-weight: 700;
                color: {tm.color('text_sub')};
                letter-spacing: 2px;
            }}
            QLabel#active_apps_text {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_main')};
            }}
            QPushButton#active_stop_btn {{
                background: rgba(255, 69, 58, 0.12);
                border: 1px solid rgba(255, 69, 58, 0.38);
                border-radius: {ds.BUTTON_RADIUS_PILL}px;
                color: #FF453A;
                font-size: 13px;
                font-weight: 700;
                padding: 11px 26px;
            }}
            QPushButton#active_stop_btn:hover {{
                background: rgba(255, 69, 58, 0.22);
                border-color: #FF453A;
                color: #FFFFFF;
            }}
"""
