"""
NMEA Tool - Main Entry Point
Launches the PySide6 GUI application.
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from config.app_config import AppConfig
from utils.theme import apply_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NMEA Tool")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("YourOrg")

    # Load saved config
    config = AppConfig.load()

    # Apply saved theme (light or dark)
    apply_theme(app, config.theme)

    # Launch main window
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
