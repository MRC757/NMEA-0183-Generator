"""
ui/tabs/connections_tab.py
Connections tab: add/remove/configure COM ports and UDP endpoints.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QComboBox, QSpinBox,
    QLineEdit, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from config.app_config import AppConfig, ComPortConfig, UdpEndpointConfig


class ConnectionsTab(QWidget):

    def __init__(self, config: AppConfig, engine, parent=None):
        super().__init__(parent)
        self._config = config
        self._engine = engine
        self._setup_ui()
        self._load_from_config()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- COM Ports ---
        com_group = QGroupBox("COM Ports (USB-to-Serial)")
        com_layout = QVBoxLayout(com_group)

        self._com_table = QTableWidget(0, 6)
        self._com_table.setHorizontalHeaderLabels(
            ["Enabled", "Port", "Baud Rate", "Parity", "Stop Bits", "Label"]
        )
        self._com_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        self._com_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        com_layout.addWidget(self._com_table)

        com_btn_row = QHBoxLayout()
        self._com_add_btn = QPushButton("+ Add COM Port")
        self._com_add_btn.clicked.connect(self._add_com_port)
        self._com_remove_btn = QPushButton("− Remove Selected")
        self._com_remove_btn.clicked.connect(self._remove_com_port)
        self._com_refresh_btn = QPushButton("↻ Refresh Ports")
        self._com_refresh_btn.clicked.connect(self._refresh_com_ports)
        com_btn_row.addWidget(self._com_add_btn)
        com_btn_row.addWidget(self._com_remove_btn)
        com_btn_row.addWidget(self._com_refresh_btn)
        com_btn_row.addStretch()
        com_layout.addLayout(com_btn_row)
        layout.addWidget(com_group)

        # --- UDP Endpoints ---
        udp_group = QGroupBox("UDP Endpoints (Perle / Network)")
        udp_layout = QVBoxLayout(udp_group)

        self._udp_table = QTableWidget(0, 7)
        self._udp_table.setHorizontalHeaderLabels(
            ["Enabled", "Host / IP", "Remote Port", "Local Port", "Send", "Receive", "Label"]
        )
        self._udp_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._udp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        udp_layout.addWidget(self._udp_table)

        udp_btn_row = QHBoxLayout()
        self._udp_add_btn = QPushButton("+ Add UDP Endpoint")
        self._udp_add_btn.clicked.connect(self._add_udp_endpoint)
        self._udp_remove_btn = QPushButton("− Remove Selected")
        self._udp_remove_btn.clicked.connect(self._remove_udp_endpoint)
        udp_btn_row.addWidget(self._udp_add_btn)
        udp_btn_row.addWidget(self._udp_remove_btn)
        udp_btn_row.addStretch()
        udp_layout.addLayout(udp_btn_row)
        layout.addWidget(udp_group)

        # Apply / status row
        apply_row = QHBoxLayout()
        self._apply_btn = QPushButton("Apply Changes")
        self._apply_btn.setFixedHeight(36)
        self._apply_btn.clicked.connect(self._apply_changes)
        self._status_label = QLabel("")
        apply_row.addStretch()
        apply_row.addWidget(self._status_label)
        apply_row.addWidget(self._apply_btn)
        layout.addLayout(apply_row)

    # -----------------------------------------------------------------------
    # COM port table
    # -----------------------------------------------------------------------

    def _load_from_config(self) -> None:
        self._com_table.setRowCount(0)
        for cp in self._config.com_ports:
            self._add_com_row(cp)

        self._udp_table.setRowCount(0)
        for udp in self._config.udp_endpoints:
            self._add_udp_row(udp)

    def _add_com_port(self) -> None:
        cp = ComPortConfig()
        self._config.com_ports.append(cp)
        self._add_com_row(cp)

    def _add_com_row(self, cp: ComPortConfig) -> None:
        row = self._com_table.rowCount()
        self._com_table.insertRow(row)

        enabled_cb = QCheckBox()
        enabled_cb.setChecked(cp.enabled)
        enabled_cb.setStyleSheet("margin-left: 10px;")
        self._com_table.setCellWidget(row, 0, enabled_cb)

        available_ports = self._engine.available_com_ports()
        port_combo = QComboBox()
        port_combo.setEditable(True)
        port_combo.addItems(available_ports or ["COM1", "COM2", "COM3", "COM4"])
        port_combo.setCurrentText(cp.port)
        self._com_table.setCellWidget(row, 1, port_combo)

        baud_combo = QComboBox()
        baud_combo.addItems(["4800", "9600", "19200", "38400", "57600", "115200"])
        baud_combo.setCurrentText(str(cp.baudrate))
        self._com_table.setCellWidget(row, 2, baud_combo)

        parity_combo = QComboBox()
        parity_combo.addItems(["N - None", "E - Even", "O - Odd", "M - Mark", "S - Space"])
        parity_map = {"N": 0, "E": 1, "O": 2, "M": 3, "S": 4}
        parity_combo.setCurrentIndex(parity_map.get(cp.parity, 0))
        self._com_table.setCellWidget(row, 3, parity_combo)

        stop_combo = QComboBox()
        stop_combo.addItems(["1", "1.5", "2"])
        stop_combo.setCurrentText(str(cp.stopbits))
        self._com_table.setCellWidget(row, 4, stop_combo)

        label_edit = QLineEdit(cp.label)
        self._com_table.setCellWidget(row, 5, label_edit)

    def _remove_com_port(self) -> None:
        rows = sorted(set(i.row() for i in self._com_table.selectedItems()), reverse=True)
        for row in rows:
            self._com_table.removeRow(row)
            if row < len(self._config.com_ports):
                self._config.com_ports.pop(row)

    def _refresh_com_ports(self) -> None:
        ports = self._engine.available_com_ports()
        for row in range(self._com_table.rowCount()):
            combo = self._com_table.cellWidget(row, 1)
            if isinstance(combo, QComboBox):
                current = combo.currentText()
                combo.clear()
                combo.addItems(ports or ["COM1"])
                combo.setCurrentText(current)

    # -----------------------------------------------------------------------
    # UDP endpoint table
    # -----------------------------------------------------------------------

    def _add_udp_endpoint(self) -> None:
        udp = UdpEndpointConfig()
        self._config.udp_endpoints.append(udp)
        self._add_udp_row(udp)

    def _add_udp_row(self, udp: UdpEndpointConfig) -> None:
        row = self._udp_table.rowCount()
        self._udp_table.insertRow(row)

        enabled_cb = QCheckBox()
        enabled_cb.setChecked(udp.enabled)
        enabled_cb.setStyleSheet("margin-left: 10px;")
        self._udp_table.setCellWidget(row, 0, enabled_cb)

        host_edit = QLineEdit(udp.host)
        self._udp_table.setCellWidget(row, 1, host_edit)

        port_spin = QSpinBox()
        port_spin.setRange(1, 65535)
        port_spin.setValue(udp.port)
        self._udp_table.setCellWidget(row, 2, port_spin)

        local_port_spin = QSpinBox()
        local_port_spin.setRange(0, 65535)
        local_port_spin.setValue(udp.local_port)
        local_port_spin.setSpecialValueText("auto")  # 0 displays as "auto"
        local_port_spin.setToolTip(
            "Local source port for outgoing UDP packets.\n"
            "Set to match the remote port so Perle devices always see\n"
            "the same source port across restarts.\n"
            "0 = let the OS pick an ephemeral port."
        )
        self._udp_table.setCellWidget(row, 3, local_port_spin)

        send_cb = QCheckBox()
        send_cb.setChecked(udp.send)
        send_cb.setStyleSheet("margin-left: 10px;")
        self._udp_table.setCellWidget(row, 4, send_cb)

        recv_cb = QCheckBox()
        recv_cb.setChecked(udp.receive)
        recv_cb.setStyleSheet("margin-left: 10px;")
        self._udp_table.setCellWidget(row, 5, recv_cb)

        label_edit = QLineEdit(udp.label)
        self._udp_table.setCellWidget(row, 6, label_edit)

    def _remove_udp_endpoint(self) -> None:
        rows = sorted(set(i.row() for i in self._udp_table.selectedItems()), reverse=True)
        for row in rows:
            self._udp_table.removeRow(row)
            if row < len(self._config.udp_endpoints):
                self._config.udp_endpoints.pop(row)

    # -----------------------------------------------------------------------
    # Apply
    # -----------------------------------------------------------------------

    def _apply_changes(self) -> None:
        """Read table values back into config and restart the engine."""
        parity_keys = ["N", "E", "O", "M", "S"]

        # COM ports
        com_ports = []
        for row in range(self._com_table.rowCount()):
            enabled = self._com_table.cellWidget(row, 0).isChecked()
            port = self._com_table.cellWidget(row, 1).currentText()
            baud = int(self._com_table.cellWidget(row, 2).currentText())
            parity_idx = self._com_table.cellWidget(row, 3).currentIndex()
            parity = parity_keys[parity_idx]
            stop = float(self._com_table.cellWidget(row, 4).currentText())
            label = self._com_table.cellWidget(row, 5).text()
            com_ports.append(ComPortConfig(
                port=port, baudrate=baud, parity=parity,
                stopbits=stop, enabled=enabled, label=label
            ))
        self._config.com_ports = com_ports

        # UDP endpoints
        udp_endpoints = []
        for row in range(self._udp_table.rowCount()):
            enabled    = self._udp_table.cellWidget(row, 0).isChecked()
            host       = self._udp_table.cellWidget(row, 1).text()
            port       = self._udp_table.cellWidget(row, 2).value()
            local_port = self._udp_table.cellWidget(row, 3).value()
            send       = self._udp_table.cellWidget(row, 4).isChecked()
            recv       = self._udp_table.cellWidget(row, 5).isChecked()
            label      = self._udp_table.cellWidget(row, 6).text()
            udp_endpoints.append(UdpEndpointConfig(
                host=host, port=port, local_port=local_port,
                enabled=enabled, send=send, receive=recv, label=label
            ))
        self._config.udp_endpoints = udp_endpoints

        # Restart engine with new config
        self._engine.stop()
        self._engine.reload_config(self._config)
        self._engine.start()

        self._status_label.setText("✓ Applied")
        _schedule_label_clear(self._status_label)

    # -----------------------------------------------------------------------
    # Engine status slots
    # -----------------------------------------------------------------------

    def on_com_status_changed(self, port_name: str, status) -> None:
        color = QColor("#2ecc71") if status.connected else QColor("#e74c3c")
        for row in range(self._com_table.rowCount()):
            combo = self._com_table.cellWidget(row, 1)
            if combo and combo.currentText() == port_name:
                for col in range(self._com_table.columnCount()):
                    item = self._com_table.item(row, col)
                    if not item:
                        item = QTableWidgetItem()
                        self._com_table.setItem(row, col, item)
                    item.setBackground(color)

    def on_udp_status_changed(self, endpoint_id: str, status) -> None:
        color = QColor("#2ecc71") if status.active else QColor("#e74c3c")
        for row in range(self._udp_table.rowCount()):
            host = self._udp_table.cellWidget(row, 1)
            port = self._udp_table.cellWidget(row, 2)
            if host and port:
                from core.udp_manager import UdpManager
                eid = UdpManager.make_endpoint_id(host.text(), port.value())
                if eid == endpoint_id:
                    for col in range(self._udp_table.columnCount()):
                        item = self._udp_table.item(row, col)
                        if not item:
                            item = QTableWidgetItem()
                            self._udp_table.setItem(row, col, item)
                        item.setBackground(color)


def _schedule_label_clear(label: "QLabel") -> None:
    QTimer.singleShot(3000, lambda: label.setText(""))
