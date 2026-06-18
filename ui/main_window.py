"""
ui/main_window.py
Main application window with tabbed interface and system tray support.
"""

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QMenuBar, QMenu, QMessageBox, QSystemTrayIcon
)
from PySide6.QtGui import QIcon, QAction, QCloseEvent
from PySide6.QtCore import Qt, QTimer

from config.app_config import AppConfig
from core.engine import NmeaEngine
from ui.tabs.connections_tab import ConnectionsTab
from ui.tabs.sentences_tab import SentencesTab
from ui.tabs.fields_tab import FieldsTab
from ui.tabs.monitor_tab import MonitorTab


class MainWindow(QMainWindow):

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._engine = NmeaEngine(config)
        self._tray_icon: QSystemTrayIcon | None = None

        self._setup_window()
        self._setup_menu()
        self._setup_tabs()
        self._setup_status_bar()
        self._setup_tray()
        self._connect_engine_signals()

        # Auto-start engine if any connections are enabled
        if any(c.enabled for c in config.com_ports) or \
           any(u.enabled for u in config.udp_endpoints):
            self._engine.start()

    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle("NMEA Tool")
        self.resize(self._config.window_width, self._config.window_height)
        self.move(self._config.window_x, self._config.window_y)

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        save_action = QAction("&Save Configuration", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Engine menu
        engine_menu = menu_bar.addMenu("&Engine")

        self._start_action = QAction("&Start", self)
        self._start_action.triggered.connect(self._start_engine)
        engine_menu.addAction(self._start_action)

        self._stop_action = QAction("S&top", self)
        self._stop_action.triggered.connect(self._stop_engine)
        engine_menu.addAction(self._stop_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        dark_action = QAction("&Dark Mode", self, checkable=True)
        dark_action.setChecked(self._config.theme == "dark")
        dark_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(dark_action)
        self._dark_action = dark_action

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        quick_start_action = QAction("&Quick Start Guide", self)
        quick_start_action.setShortcut("F1")
        quick_start_action.triggered.connect(self._show_quick_start)
        help_menu.addAction(quick_start_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_tabs(self) -> None:
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)

        self._connections_tab = ConnectionsTab(self._config, self._engine)
        self._sentences_tab = SentencesTab(self._config, self._engine)
        self._fields_tab = FieldsTab(self._config, self._engine)
        self._monitor_tab = MonitorTab(self._config, self._engine)

        self._tabs.addTab(self._connections_tab, "🔌  Connections")
        self._tabs.addTab(self._sentences_tab,   "📋  Sentences")
        self._tabs.addTab(self._fields_tab,       "✏️   Fields")
        self._tabs.addTab(self._monitor_tab,      "📡  Monitor")

        self.setCentralWidget(self._tabs)

    def _setup_status_bar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

    def _setup_tray(self) -> None:
        """Set up system tray icon and menu."""
        # Use a default system icon — replace with custom icon path as needed
        icon = self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon
        )

        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_icon.setToolTip("NMEA Tool")

        tray_menu = QMenu()

        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        start_action = QAction("Start Engine", self)
        start_action.triggered.connect(self._start_engine)
        tray_menu.addAction(start_action)

        stop_action = QAction("Stop Engine", self)
        stop_action.triggered.connect(self._stop_engine)
        tray_menu.addAction(stop_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _connect_engine_signals(self) -> None:
        self._engine.sentence_sent.connect(self._monitor_tab.on_sentence_sent)
        self._engine.sentence_received.connect(self._monitor_tab.on_sentence_received)
        self._engine.sentence_parsed.connect(self._monitor_tab.on_sentence_parsed)
        self._engine.error_occurred.connect(self._monitor_tab.on_error)
        self._engine.error_occurred.connect(self._on_engine_error)
        self._engine.com_status_changed.connect(self._connections_tab.on_com_status_changed)
        self._engine.udp_status_changed.connect(self._connections_tab.on_udp_status_changed)
        self._sentences_tab.sentences_changed.connect(self._fields_tab.refresh)
        self._connections_tab.connections_changed.connect(self._sentences_tab._refresh_output_list)

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------

    def _save_config(self) -> None:
        self._config.window_width = self.width()
        self._config.window_height = self.height()
        self._config.window_x = self.x()
        self._config.window_y = self.y()
        self._config.save()
        self._status_bar.showMessage("Configuration saved.", 3000)

    def _start_engine(self) -> None:
        self._engine.start()
        self._status_bar.showMessage("Engine started.", 3000)

    def _stop_engine(self) -> None:
        self._engine.stop()
        self._status_bar.showMessage("Engine stopped.", 3000)

    def _toggle_theme(self, checked: bool) -> None:
        from PySide6.QtWidgets import QApplication
        from utils.theme import apply_theme
        self._config.theme = "dark" if checked else "light"
        apply_theme(QApplication.instance(), self._config.theme)

    def _show_quick_start(self) -> None:
        from ui.dialogs.quick_start_dialog import QuickStartDialog
        dlg = QuickStartDialog(parent=self)
        dlg.show()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About NMEA Tool",
            "<h3>NMEA Tool</h3>"
            "<p>Bidirectional NMEA 0183 simulator and monitor.</p>"
            "<p>Supports COM ports (USB-serial) and UDP endpoints.</p>"
            "<p>Full standard sentence set + custom sentences.</p>"
        )

    def _on_engine_error(self, source: str, msg: str) -> None:
        self._status_bar.showMessage(f"Error [{source}]: {msg}", 5000)

    # -----------------------------------------------------------------------
    # Tray
    # -----------------------------------------------------------------------

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self) -> None:
        self._engine.stop()
        self._save_config()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    # -----------------------------------------------------------------------
    # Window events
    # -----------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimize to tray instead of closing."""
        event.ignore()
        self.hide()
        if self._tray_icon:
            self._tray_icon.showMessage(
                "NMEA Tool",
                "Running in background. Double-click to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
