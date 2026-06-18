"""
ui/tabs/monitor_tab.py
Monitor tab: live scrolling NMEA sentence display with selectable filters.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QCheckBox, QLabel, QSpinBox, QFrame,
    QLineEdit
)
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
from PySide6.QtCore import Qt, QDateTime
from collections import deque

from config.app_config import AppConfig


# Colour scheme for each message type
COLOURS = {
    "sent":     "#4fc3f7",   # Light blue
    "received": "#a5d6a7",   # Light green
    "parsed":   "#fff176",   # Yellow
    "error":    "#ef9a9a",   # Light red
}


class MonitorTab(QWidget):

    def __init__(self, config: AppConfig, engine, parent=None):
        super().__init__(parent)
        self._config = config
        self._engine = engine
        self._paused = False
        self._pending: deque = deque(maxlen=2000)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ---- Filter bar ----
        filter_row = QHBoxLayout()

        self._cb_sent = QCheckBox("Sent")
        self._cb_sent.setChecked(self._config.monitor.show_sent)
        self._cb_sent.setStyleSheet(f"color: {COLOURS['sent']};")
        filter_row.addWidget(self._cb_sent)

        self._cb_received = QCheckBox("Received")
        self._cb_received.setChecked(self._config.monitor.show_received)
        self._cb_received.setStyleSheet(f"color: {COLOURS['received']};")
        filter_row.addWidget(self._cb_received)

        self._cb_parsed = QCheckBox("Parsed Fields")
        self._cb_parsed.setChecked(self._config.monitor.show_parsed)
        self._cb_parsed.setStyleSheet(f"color: {COLOURS['parsed']};")
        filter_row.addWidget(self._cb_parsed)

        self._cb_errors = QCheckBox("Errors")
        self._cb_errors.setChecked(self._config.monitor.show_errors)
        self._cb_errors.setStyleSheet(f"color: {COLOURS['error']};")
        filter_row.addWidget(self._cb_errors)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        filter_row.addWidget(sep)

        filter_row.addWidget(QLabel("Filter:"))
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("e.g. GGA, COM3, error...")
        self._filter_edit.setMinimumWidth(160)
        filter_row.addWidget(self._filter_edit)

        filter_row.addStretch()

        filter_row.addWidget(QLabel("Max lines:"))
        self._max_lines_spin = QSpinBox()
        self._max_lines_spin.setRange(50, 5000)
        self._max_lines_spin.setValue(self._config.monitor.max_lines)
        self._max_lines_spin.setSingleStep(100)
        filter_row.addWidget(self._max_lines_spin)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        filter_row.addWidget(sep2)

        self._pause_btn = QPushButton("⏸ Pause")
        self._pause_btn.setCheckable(True)
        self._pause_btn.toggled.connect(self._on_pause_toggled)
        filter_row.addWidget(self._pause_btn)

        self._clear_btn = QPushButton("🗑 Clear")
        self._clear_btn.clicked.connect(self._clear)
        filter_row.addWidget(self._clear_btn)

        self._save_btn = QPushButton("💾 Save Log")
        self._save_btn.clicked.connect(self._save_log)
        filter_row.addWidget(self._save_btn)

        layout.addLayout(filter_row)

        # Save filter settings back to config when changed
        self._cb_sent.toggled.connect(
            lambda v: setattr(self._config.monitor, "show_sent", v))
        self._cb_received.toggled.connect(
            lambda v: setattr(self._config.monitor, "show_received", v))
        self._cb_parsed.toggled.connect(
            lambda v: setattr(self._config.monitor, "show_parsed", v))
        self._cb_errors.toggled.connect(
            lambda v: setattr(self._config.monitor, "show_errors", v))
        self._max_lines_spin.valueChanged.connect(
            lambda v: setattr(self._config.monitor, "max_lines", v))

        # ---- Log display ----
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._log.setFont(font)
        self._log.setMaximumBlockCount(self._max_lines_spin.value())
        self._max_lines_spin.valueChanged.connect(self._log.setMaximumBlockCount)
        layout.addWidget(self._log)

        # ---- Stats bar ----
        stats_row = QHBoxLayout()
        self._stats_sent = QLabel("Sent: 0")
        self._stats_recv = QLabel("Received: 0")
        self._stats_err = QLabel("Errors: 0")
        stats_row.addWidget(self._stats_sent)
        stats_row.addWidget(QLabel("|"))
        stats_row.addWidget(self._stats_recv)
        stats_row.addWidget(QLabel("|"))
        stats_row.addWidget(self._stats_err)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        self._count_sent = 0
        self._count_recv = 0
        self._count_err = 0

    # -----------------------------------------------------------------------
    # Engine signal handlers (called on main thread via Qt signals)
    # -----------------------------------------------------------------------

    def on_sentence_sent(self, output_id: str, raw: str) -> None:
        if not self._cb_sent.isChecked():
            return
        self._count_sent += 1
        self._stats_sent.setText(f"Sent: {self._count_sent}")
        self._append(f"[TX] [{output_id}]  {raw}", "sent")

    def on_sentence_received(self, source_id: str, raw: str) -> None:
        if not self._cb_received.isChecked():
            return
        self._count_recv += 1
        self._stats_recv.setText(f"Received: {self._count_recv}")
        self._append(f"[RX] [{source_id}]  {raw}", "received")

    def on_sentence_parsed(self, source_id: str, sentence_id: str, parsed: dict) -> None:
        if not self._cb_parsed.isChecked():
            return
        fields_str = "  ".join(f"{k}={v}" for k, v in parsed.items() if v)
        self._append(
            f"[PARSED] {sentence_id} from [{source_id}]:  {fields_str}", "parsed"
        )

    def on_error(self, source_id: str, msg: str) -> None:
        if not self._cb_errors.isChecked():
            return
        self._count_err += 1
        self._stats_err.setText(f"Errors: {self._count_err}")
        self._append(f"[ERROR] [{source_id}]  {msg}", "error")

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _append(self, text: str, msg_type: str) -> None:
        # Apply text filter
        filter_text = self._filter_edit.text().lower().strip()
        if filter_text and filter_text not in text.lower():
            return

        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        line = f"{timestamp}  {text}"

        if self._paused:
            self._pending.append((line, msg_type))
            return

        self._write_line(line, msg_type)

    def _write_line(self, line: str, msg_type: str) -> None:
        colour = COLOURS.get(msg_type, "#ffffff")
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(colour))

        cursor = self._log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(line + "\n", fmt)

        # Auto-scroll to bottom
        scrollbar = self._log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_pause_toggled(self, checked: bool) -> None:
        self._paused = checked
        self._pause_btn.setText("▶ Resume" if checked else "⏸ Pause")

        if not checked:
            # Flush pending lines
            while self._pending:
                line, msg_type = self._pending.popleft()
                self._write_line(line, msg_type)

    def _clear(self) -> None:
        self._log.clear()
        self._pending.clear()
        self._count_sent = 0
        self._count_recv = 0
        self._count_err = 0
        self._stats_sent.setText("Sent: 0")
        self._stats_recv.setText("Received: 0")
        self._stats_err.setText("Errors: 0")

    def _save_log(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Monitor Log", "nmea_log.txt", "Text Files (*.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._log.toPlainText())
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Save Failed", str(e))
