"""
ui/tabs/sentences_tab.py
Sentences tab: enable/disable NMEA sentences, set per-sentence rate,
assign outputs, and add custom sentences.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QDoubleSpinBox, QCheckBox,
    QLabel, QLineEdit, QComboBox, QGroupBox, QListWidget,
    QListWidgetItem, QAbstractItemView, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from typing import List

from config.app_config import AppConfig, NmeaSentenceConfig
from core.nmea_sentences import STANDARD_SENTENCES, SENTENCE_LOOKUP, CATEGORIES
from core.udp_manager import UdpManager


class SentencesTab(QWidget):

    sentences_changed = Signal()  # emitted when sentences are added or removed

    def __init__(self, config: AppConfig, engine, parent=None):
        super().__init__(parent)
        self._config = config
        self._engine = engine
        self._selected_cfg: NmeaSentenceConfig | None = None
        self._setup_ui()
        self._populate_sentence_tree()
        self._load_config_sentences()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: sentence library tree
        left = QGroupBox("Sentence Library")
        left_layout = QVBoxLayout(left)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search sentences...")
        self._search_box.textChanged.connect(self._filter_tree)
        left_layout.addWidget(self._search_box)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabel("Sentence Type")
        self._tree.setColumnCount(1)
        self._tree.itemClicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self._tree)

        add_btn = QPushButton("+ Add to Active")
        add_btn.clicked.connect(self._add_selected_sentence)
        left_layout.addWidget(add_btn)

        custom_btn = QPushButton("+ Add Custom Sentence")
        custom_btn.clicked.connect(self._add_custom_sentence)
        left_layout.addWidget(custom_btn)

        splitter.addWidget(left)

        # Right: active sentences table
        right = QGroupBox("Active Sentences")
        right_layout = QVBoxLayout(right)

        self._active_table = QTableWidget(0, 6)
        self._active_table.setHorizontalHeaderLabels([
            "Enabled", "Talker", "Sentence", "Rate (Hz)", "Outputs", "Custom?"
        ])
        self._active_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self._active_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._active_table.itemSelectionChanged.connect(self._on_active_selection_changed)
        right_layout.addWidget(self._active_table)

        btn_row = QHBoxLayout()
        self._remove_btn = QPushButton("− Remove Selected")
        self._remove_btn.clicked.connect(self._remove_selected)
        self._send_now_btn = QPushButton("▶ Send Now")
        self._send_now_btn.clicked.connect(self._send_now)
        self._edit_custom_btn = QPushButton("✏ Edit Custom...")
        self._edit_custom_btn.clicked.connect(self._edit_custom_sentence)
        self._edit_custom_btn.setToolTip("Open the Custom Sentence Editor for the selected custom sentence")
        btn_row.addWidget(self._remove_btn)
        btn_row.addWidget(self._edit_custom_btn)
        btn_row.addWidget(self._send_now_btn)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([280, 720])
        layout.addWidget(splitter)

        # Output routing panel (shown below table)
        output_group = QGroupBox("Output Routing — Selected Sentence")
        output_layout = QHBoxLayout(output_group)

        output_layout.addWidget(QLabel("Route to:"))
        self._output_list = QListWidget()
        self._output_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._output_list.setMaximumHeight(90)
        self._refresh_output_list()
        self._output_list.itemSelectionChanged.connect(self._on_output_selection_changed)
        output_layout.addWidget(self._output_list)

        layout.addWidget(output_group)

    # -----------------------------------------------------------------------
    # Tree population
    # -----------------------------------------------------------------------

    def _populate_sentence_tree(self) -> None:
        self._tree.clear()
        category_items = {}
        for cat in CATEGORIES:
            item = QTreeWidgetItem([cat])
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._tree.addTopLevelItem(item)
            category_items[cat] = item

        for s_def in STANDARD_SENTENCES:
            child = QTreeWidgetItem([f"{s_def.sentence_id} — {s_def.description}"])
            child.setData(0, Qt.ItemDataRole.UserRole, s_def.sentence_id)
            category_items[s_def.category].addChild(child)

        self._tree.expandAll()

    def _filter_tree(self, text: str) -> None:
        text = text.lower()
        for i in range(self._tree.topLevelItemCount()):
            cat_item = self._tree.topLevelItem(i)
            cat_visible = False
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                match = text in child.text(0).lower()
                child.setHidden(not match)
                if match:
                    cat_visible = True
            cat_item.setHidden(not cat_visible)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        self._selected_sentence_id = item.data(0, Qt.ItemDataRole.UserRole)

    # -----------------------------------------------------------------------
    # Active sentences table
    # -----------------------------------------------------------------------

    def _load_config_sentences(self) -> None:
        self._active_table.setRowCount(0)
        for cfg in self._config.sentences:
            self._add_active_row(cfg)

    def _add_active_row(self, cfg: NmeaSentenceConfig) -> None:
        row = self._active_table.rowCount()
        self._active_table.insertRow(row)

        enabled_cb = QCheckBox()
        enabled_cb.setChecked(cfg.enabled)
        enabled_cb.setStyleSheet("margin-left: 10px;")
        enabled_cb.stateChanged.connect(lambda state, r=row: self._on_enabled_changed(r, state))
        self._active_table.setCellWidget(row, 0, enabled_cb)

        talker_edit = QLineEdit(cfg.talker_id)
        talker_edit.setMaxLength(2)
        talker_edit.setFixedWidth(40)
        talker_edit.textChanged.connect(lambda text, r=row: self._on_talker_changed(r, text))
        self._active_table.setCellWidget(row, 1, talker_edit)

        sentence_item = QTableWidgetItem(cfg.sentence_id)
        sentence_item.setFlags(sentence_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._active_table.setItem(row, 2, sentence_item)

        rate_spin = QDoubleSpinBox()
        rate_spin.setRange(0.1, 100.0)
        rate_spin.setSingleStep(0.5)
        rate_spin.setDecimals(1)
        rate_spin.setSuffix(" Hz")
        rate_spin.setValue(cfg.rate_hz)
        rate_spin.valueChanged.connect(lambda val, r=row: self._on_rate_changed(r, val))
        self._active_table.setCellWidget(row, 3, rate_spin)

        outputs_item = QTableWidgetItem(", ".join(cfg.outputs))
        outputs_item.setFlags(outputs_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._active_table.setItem(row, 4, outputs_item)

        custom_item = QTableWidgetItem("✓" if cfg.is_custom else "")
        custom_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        custom_item.setFlags(custom_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._active_table.setItem(row, 5, custom_item)

        # Store cfg reference in row
        self._active_table.item(row, 2).setData(Qt.ItemDataRole.UserRole, cfg)

    def _add_selected_sentence(self) -> None:
        sid = getattr(self, "_selected_sentence_id", None)
        if not sid:
            return
        s_def = SENTENCE_LOOKUP.get(sid)
        if not s_def:
            return
        cfg = NmeaSentenceConfig(
            sentence_id=sid,
            talker_id="GP",
            enabled=True,
            rate_hz=1.0,
            fields={f.name: f.default for f in s_def.fields},
            outputs=[],
        )
        self._config.sentences.append(cfg)
        self._add_active_row(cfg)
        self._engine.add_sentence(cfg)
        self.sentences_changed.emit()

    def _add_custom_sentence(self) -> None:
        """Open the custom sentence editor to create a new sentence."""
        from ui.dialogs.custom_sentence_editor import CustomSentenceEditor
        from PySide6.QtWidgets import QDialog
        editor = CustomSentenceEditor(parent=self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            cfg = editor.result_config()
            self._config.sentences.append(cfg)
            self._add_active_row(cfg)
            self._engine.add_sentence(cfg)
            self.sentences_changed.emit()

    def _edit_custom_sentence(self) -> None:
        """Open the custom sentence editor to edit the selected custom sentence."""
        from ui.dialogs.custom_sentence_editor import CustomSentenceEditor
        from PySide6.QtWidgets import QDialog
        rows = set(i.row() for i in self._active_table.selectedItems())
        if not rows:
            return
        row = list(rows)[0]
        cfg = self._get_cfg(row)
        if not cfg or not cfg.is_custom:
            return
        editor = CustomSentenceEditor(parent=self, cfg=cfg)
        if editor.exec() == QDialog.DialogCode.Accepted:
            updated = editor.result_config()
            # Copy updated values back into existing config object
            cfg.sentence_id     = updated.sentence_id
            cfg.talker_id       = updated.talker_id
            cfg.fields          = updated.fields
            cfg.custom_template = updated.custom_template
            # Refresh the row display (col 1 is a QLineEdit widget, not an item)
            talker_widget = self._active_table.cellWidget(row, 1)
            if talker_widget:
                talker_widget.setText(cfg.talker_id)
            sentence_item = self._active_table.item(row, 2)
            if sentence_item:
                sentence_item.setText(cfg.sentence_id)
                sentence_item.setData(Qt.ItemDataRole.UserRole, cfg)
            # Re-register with scheduler
            self._engine.add_sentence(cfg)
            self.sentences_changed.emit()

    def _remove_selected(self) -> None:
        rows = sorted(
            set(i.row() for i in self._active_table.selectedItems()),
            reverse=True
        )
        for row in rows:
            cfg = self._active_table.item(row, 2).data(Qt.ItemDataRole.UserRole)
            if cfg in self._config.sentences:
                self._config.sentences.remove(cfg)
                self._engine.remove_sentence(cfg)
            self._active_table.removeRow(row)
        if rows:
            self.sentences_changed.emit()

    def _send_now(self) -> None:
        rows = set(i.row() for i in self._active_table.selectedItems())
        for row in rows:
            cfg = self._active_table.item(row, 2).data(Qt.ItemDataRole.UserRole)
            if cfg:
                self._engine.send_now(cfg)

    def _on_active_selection_changed(self) -> None:
        rows = set(i.row() for i in self._active_table.selectedItems())
        if not rows:
            self._selected_cfg = None
            return
        row = list(rows)[0]
        item = self._active_table.item(row, 2)
        if item:
            self._selected_cfg = item.data(Qt.ItemDataRole.UserRole)
            self._update_output_selection()

    # -----------------------------------------------------------------------
    # Cell change handlers
    # -----------------------------------------------------------------------

    def _on_enabled_changed(self, row: int, state: int) -> None:
        cfg = self._get_cfg(row)
        if cfg:
            cfg.enabled = (Qt.CheckState(state) == Qt.CheckState.Checked)
            self._engine.set_sentence_enabled(cfg, cfg.enabled)

    def _on_talker_changed(self, row: int, text: str) -> None:
        cfg = self._get_cfg(row)
        if cfg:
            cfg.talker_id = text.upper()

    def _on_rate_changed(self, row: int, value: float) -> None:
        cfg = self._get_cfg(row)
        if cfg:
            cfg.rate_hz = value
            self._engine.update_sentence_rate(cfg, value)

    def _get_cfg(self, row: int) -> NmeaSentenceConfig | None:
        item = self._active_table.item(row, 2)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    # -----------------------------------------------------------------------
    # Output routing
    # -----------------------------------------------------------------------

    def _refresh_output_list(self) -> None:
        self._output_list.clear()
        for cp in self._config.com_ports:
            label = cp.label or cp.port
            item = QListWidgetItem(f"COM: {label}")
            item.setData(Qt.ItemDataRole.UserRole, cp.port)
            self._output_list.addItem(item)

        for udp in self._config.udp_endpoints:
            eid = UdpManager.make_endpoint_id(udp.host, udp.port)
            label = udp.label or f"{udp.host}:{udp.port}"
            item = QListWidgetItem(f"UDP: {label}")
            item.setData(Qt.ItemDataRole.UserRole, eid)
            self._output_list.addItem(item)

    def _update_output_selection(self) -> None:
        if not self._selected_cfg:
            return
        for i in range(self._output_list.count()):
            item = self._output_list.item(i)
            oid = item.data(Qt.ItemDataRole.UserRole)
            item.setSelected(oid in self._selected_cfg.outputs)

    def _on_output_selection_changed(self) -> None:
        if not self._selected_cfg:
            return
        outputs = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._output_list.selectedItems()
        ]
        self._selected_cfg.outputs = outputs
        # Update table display
        rows = set(i.row() for i in self._active_table.selectedItems())
        for row in rows:
            item = self._active_table.item(row, 4)
            if item:
                item.setText(", ".join(outputs))
        self._engine.update_sentence_outputs(self._selected_cfg, outputs)
