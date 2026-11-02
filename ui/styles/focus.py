"""
focus.py — Externalized QSS for the Focus suite.

Kept separate from FocusTimerWidget so theme changes have one reviewable
surface and the widget file stays focused on behavior.
"""
from __future__ import annotations

from PySide6.QtGui import QColor

from ui import design_system as ds
from ui.theme import ThemeManager


def build_focus_stylesheet(
    tm: ThemeManager,
    mode_color: str,
    is_dark: bool,
    liquid_glass: bool = True,
) -> str:
    """Builds the comprehensive QSS stylesheet for the Focus page.
    Supports authentic Apple Liquid Glass aesthetic (VisionOS / macOS Sequoia glassmorphism,
    specular refractive edges, vibrant neon accents) and clean solid dark/light fallback.
    """
    if liquid_glass and is_dark:
        # ── Authentic Apple Liquid Glass Theme (Dark Glassmorphism) ───────────
        card_bg = "rgba(24, 24, 30, 0.78)"
        card_border = "1px solid rgba(255, 255, 255, 0.14)"
        card_border_top = "1px solid rgba(255, 255, 255, 0.28)"
        inset_bg = "rgba(255, 255, 255, 0.04)"
        inset_border = "1px solid rgba(255, 255, 255, 0.08)"
        capsule_bg = "rgba(255, 255, 255, 0.05)"
        capsule_border = "1px solid rgba(255, 255, 255, 0.12)"
        chip_checked_bg = "rgba(255, 255, 255, 0.14)"
        chip_checked_border = "1px solid rgba(255, 255, 255, 0.24)"
        sec_btn_bg = "rgba(255, 255, 255, 0.06)"
        sec_btn_border = "1px solid rgba(255, 255, 255, 0.14)"
        sec_btn_hover = "rgba(255, 255, 255, 0.12)"
        start_btn_bg = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {QColor(mode_color).lighter(118).name()}, stop:1 {mode_color})"
        start_btn_border = "1px solid rgba(255, 255, 255, 0.35)"
        stepper_bg = "rgba(255, 255, 255, 0.06)"
        stepper_border = "1px solid rgba(255, 255, 255, 0.12)"
    elif liquid_glass and not is_dark:
        # ── Apple Liquid Glass Theme (Light Frost Glass) ──────────────────────
        card_bg = "rgba(255, 255, 255, 0.78)"
        card_border = "1px solid rgba(0, 0, 0, 0.08)"
        card_border_top = "1px solid rgba(255, 255, 255, 0.85)"
        inset_bg = "rgba(0, 0, 0, 0.03)"
        inset_border = "1px solid rgba(0, 0, 0, 0.06)"
        capsule_bg = "rgba(0, 0, 0, 0.04)"
        capsule_border = "1px solid rgba(0, 0, 0, 0.08)"
        chip_checked_bg = "rgba(255, 255, 255, 0.90)"
        chip_checked_border = f"1px solid {mode_color}"
        sec_btn_bg = "rgba(0, 0, 0, 0.04)"
        sec_btn_border = "1px solid rgba(0, 0, 0, 0.10)"
        sec_btn_hover = "rgba(0, 0, 0, 0.08)"
        start_btn_bg = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {mode_color}, stop:1 {QColor(mode_color).darker(108).name()})"
        start_btn_border = "1px solid rgba(255, 255, 255, 0.40)"
        stepper_bg = "rgba(0, 0, 0, 0.04)"
        stepper_border = "1px solid rgba(0, 0, 0, 0.08)"
    else:
        # ── Classic Solid Theme (Standard Fallback) ───────────────────────────
        card_bg = tm.color('surface')
        card_border = f"1px solid {tm.color('border')}"
        card_border_top = card_border
        inset_bg = tm.color('surface_secondary')
        inset_border = f"1px solid {tm.color('border')}"
        capsule_bg = tm.color('surface')
        capsule_border = f"1px solid {tm.color('border')}"
        chip_checked_bg = tm.color('surface_elevated')
        chip_checked_border = f"1px solid {tm.color('border')}"
        sec_btn_bg = tm.color('surface')
        sec_btn_border = f"1px solid {tm.color('border')}"
        sec_btn_hover = tm.color('card_hover')
        start_btn_bg = mode_color
        start_btn_border = "none"
        stepper_bg = tm.color('surface')
        stepper_border = f"1px solid {tm.color('border')}"

    return f"""
            QFrame#focus_suite_root {{
                background: transparent;
                border: none;
            }}
            QFrame#focus_section_card {{
                background-color: {card_bg};
                border: {card_border};
                border-top: {card_border_top};
                border-radius: {ds.CARD_RADIUS}px;
            }}
            QFrame#apple_inset_card {{
                background-color: {inset_bg};
                border: {inset_border};
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
                background: {inset_bg};
                border: {inset_border};
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
                background-color: {capsule_bg};
                border: {capsule_border};
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
                background: {chip_checked_bg};
                color: {mode_color};
                font-weight: 700;
                border: {chip_checked_border};
            }}
            QPushButton#stepper_btn {{
                background: {stepper_bg};
                border: {stepper_border};
                border-radius: {ds.BUTTON_RADIUS}px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
                padding: 5px 10px;
            }}
            QPushButton#stepper_btn:hover {{
                background: {sec_btn_hover};
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
                background-color: {inset_bg};
                border: {inset_border};
                border-radius: {ds.BUTTON_RADIUS}px;
                color: {tm.color('text_sub')};
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }}
            QPushButton#quick_add_chip:hover {{
                background-color: {sec_btn_hover};
                color: {tm.color('text_main')};
                border-color: {tm.color('accent')};
            }}
            QLineEdit#site_search_input {{
                background-color: {inset_bg};
                border: {inset_border};
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
                background: {start_btn_bg};
                border: {start_btn_border};
                border-radius: 999px;
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
                background-color: {sec_btn_bg};
                border: {sec_btn_border};
                border-radius: {ds.BUTTON_RADIUS_PILL}px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 10px 18px;
            }}
            QPushButton#secondary_pill_btn:hover {{
                background-color: {sec_btn_hover};
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
