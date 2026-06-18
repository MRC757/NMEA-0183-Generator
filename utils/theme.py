"""
utils/theme.py
Light and dark theme support for PySide6.
No external theming libraries required.
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply 'light' or 'dark' theme to the application."""
    if theme == "dark":
        _apply_dark(app)
    else:
        _apply_light(app)


def _apply_dark(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()

    dark_bg      = QColor(30, 30, 30)
    mid_bg       = QColor(45, 45, 45)
    light_bg     = QColor(60, 60, 60)
    text_color   = QColor(220, 220, 220)
    accent       = QColor(0, 120, 215)      # Windows blue
    disabled     = QColor(120, 120, 120)
    border       = QColor(80, 80, 80)

    palette.setColor(QPalette.Window,          dark_bg)
    palette.setColor(QPalette.WindowText,      text_color)
    palette.setColor(QPalette.Base,            mid_bg)
    palette.setColor(QPalette.AlternateBase,   light_bg)
    palette.setColor(QPalette.ToolTipBase,     mid_bg)
    palette.setColor(QPalette.ToolTipText,     text_color)
    palette.setColor(QPalette.Text,            text_color)
    palette.setColor(QPalette.Button,          mid_bg)
    palette.setColor(QPalette.ButtonText,      text_color)
    palette.setColor(QPalette.BrightText,      Qt.red)
    palette.setColor(QPalette.Link,            accent)
    palette.setColor(QPalette.Highlight,       accent)
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Text,       disabled)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, disabled)
    palette.setColor(QPalette.Mid,             border)

    app.setPalette(palette)


def _apply_light(app: QApplication) -> None:
    """Restore system default light palette."""
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
