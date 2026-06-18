"""
ui/tabs/fields_tab.py
Fields tab: edit the data values for each active sentence's fields.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QLineEdit,
    QComboBox, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt

from config.app_config import AppConfig, NmeaSentenceConfig
from core.nmea_sentences import SENTENCE_LOOKUP, NmeaFieldDef


class FieldsTab(QWidget):

    def __init__(self, config: AppConfig, engine, parent=None):
        super().__init__(parent)
        self._config = config
        self._engine = engine
        self._setup_ui()
        self._load_sentence_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: sentence selector
        left = QGroupBox("Active Sentences")
        left_layout = QVBoxLayout(left)
        self._sentence_list = QListWidget()
        self._sentence_list.currentItemChanged.connect(self._on_sentence_selected)
        left_layout.addWidget(self._sentence_list)
        splitter.addWidget(left)

        # Right: field editor
        right = QWidget()
        right_layout = QVBoxLayout(right)

        self._sentence_label = QLabel("Select a sentence to edit its fields.")
        self._sentence_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        right_layout.addWidget(self._sentence_label)

        # Standard fields table
        self._fields_table = QTableWidget(0, 4)
        self._fields_table.setHorizontalHeaderLabels(
            ["Field", "Description", "Units", "Value"]
        )
        self._fields_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._fields_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._fields_table.setColumnWidth(0, 140)
        self._fields_table.setColumnWidth(2, 60)
        self._fields_table.itemChanged.connect(self._on_field_value_changed)
        right_layout.addWidget(self._fields_table)

        # Custom sentence template editor (hidden for standard sentences)
        self._custom_group = QGroupBox("Custom Sentence Template")
        custom_layout = QVBoxLayout(self._custom_group)
        custom_layout.addWidget(QLabel(
            "Enter the raw sentence body (without $, checksum, or CRLF).\n"
            "Example:  PGRME,3.0,M,4.0,M,5.0,M"
        ))
        self._custom_template_edit = QTextEdit()
        self._custom_template_edit.setMaximumHeight(80)
        self._custom_template_edit.textChanged.connect(self._on_custom_template_changed)
        custom_layout.addWidget(self._custom_template_edit)

        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("Preview:"))
        self._preview_label = QLabel("")
        self._preview_label.setStyleSheet("font-family: monospace;")
        self._preview_label.setWordWrap(True)
        preview_row.addWidget(self._preview_label, 1)
        custom_layout.addLayout(preview_row)
        right_layout.addWidget(self._custom_group)
        self._custom_group.hide()

        # Preview for standard sentences
        self._std_preview_group = QGroupBox("Sentence Preview")
        std_preview_layout = QVBoxLayout(self._std_preview_group)
        self._std_preview_label = QLabel("")
        self._std_preview_label.setStyleSheet("font-family: monospace;")
        self._std_preview_label.setWordWrap(True)
        std_preview_layout.addWidget(self._std_preview_label)
        right_layout.addWidget(self._std_preview_group)

        splitter.addWidget(right)
        splitter.setSizes([200, 800])
        layout.addWidget(splitter)

    # -----------------------------------------------------------------------
    # Sentence list
    # -----------------------------------------------------------------------

    def _load_sentence_list(self) -> None:
        self._sentence_list.clear()
        for cfg in self._config.sentences:
            label = f"{cfg.talker_id}{cfg.sentence_id}"
            if cfg.is_custom:
                label += " [custom]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, cfg)
            self._sentence_list.addItem(item)

    def refresh(self) -> None:
        """Call when sentences list changes."""
        self._load_sentence_list()

    def _on_sentence_selected(self, current: QListWidgetItem, previous) -> None:
        if not current:
            return
        cfg: NmeaSentenceConfig = current.data(Qt.ItemDataRole.UserRole)
        self._current_cfg = cfg
        self._sentence_label.setText(
            f"{cfg.talker_id}{cfg.sentence_id}"
            + (" — Custom" if cfg.is_custom else
               f" — {SENTENCE_LOOKUP[cfg.sentence_id].description}"
               if cfg.sentence_id in SENTENCE_LOOKUP else "")
        )

        if cfg.is_custom:
            self._fields_table.hide()
            self._std_preview_group.hide()
            self._custom_group.show()
            self._custom_template_edit.blockSignals(True)
            self._custom_template_edit.setPlainText(cfg.custom_template)
            self._custom_template_edit.blockSignals(False)
            self._update_custom_preview(cfg)
        else:
            self._custom_group.hide()
            self._fields_table.show()
            self._std_preview_group.show()
            self._load_fields(cfg)

    # -----------------------------------------------------------------------
    # Standard fields
    # -----------------------------------------------------------------------

    def _load_fields(self, cfg: NmeaSentenceConfig) -> None:
        self._fields_table.blockSignals(True)
        self._fields_table.setRowCount(0)

        s_def = SENTENCE_LOOKUP.get(cfg.sentence_id)
        if not s_def:
            self._fields_table.blockSignals(False)
            return

        for field_def in s_def.fields:
            row = self._fields_table.rowCount()
            self._fields_table.insertRow(row)

            name_item = QTableWidgetItem(field_def.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._fields_table.setItem(row, 0, name_item)

            desc_item = QTableWidgetItem(field_def.description)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._fields_table.setItem(row, 1, desc_item)

            units_item = QTableWidgetItem(field_def.units)
            units_item.setFlags(units_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._fields_table.setItem(row, 2, units_item)

            current_value = cfg.fields.get(field_def.name, field_def.default)

            if field_def.choices:
                combo = QComboBox()
                combo.addItems(field_def.choices)
                if current_value in field_def.choices:
                    combo.setCurrentText(current_value)
                combo.currentTextChanged.connect(
                    lambda text, fn=field_def.name: self._on_combo_changed(fn, text)
                )
                self._fields_table.setCellWidget(row, 3, combo)
                # Placeholder item so itemChanged can reference row
                self._fields_table.setItem(row, 3, QTableWidgetItem(""))
            else:
                value_item = QTableWidgetItem(current_value)
                self._fields_table.setItem(row, 3, value_item)

        self._fields_table.blockSignals(False)
        self._update_std_preview(cfg)

    def _on_field_value_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 3:
            return
        cfg = getattr(self, "_current_cfg", None)
        if not cfg or cfg.is_custom:
            return
        row = item.row()
        field_name_item = self._fields_table.item(row, 0)
        if not field_name_item:
            return
        field_name = field_name_item.text()
        cfg.fields[field_name] = item.text()
        self._update_std_preview(cfg)

    def _on_combo_changed(self, field_name: str, value: str) -> None:
        cfg = getattr(self, "_current_cfg", None)
        if cfg and not cfg.is_custom:
            cfg.fields[field_name] = value
            self._update_std_preview(cfg)

    def _update_std_preview(self, cfg: NmeaSentenceConfig) -> None:
        try:
            raw = self._engine._build_raw(cfg).strip()
            self._std_preview_label.setText(raw)
        except Exception as e:
            self._std_preview_label.setText(f"[Preview error: {e}]")

    # -----------------------------------------------------------------------
    # Custom sentence template
    # -----------------------------------------------------------------------

    def _on_custom_template_changed(self) -> None:
        cfg = getattr(self, "_current_cfg", None)
        if cfg and cfg.is_custom:
            cfg.custom_template = self._custom_template_edit.toPlainText().strip()
            self._update_custom_preview(cfg)

    def _update_custom_preview(self, cfg: NmeaSentenceConfig) -> None:
        try:
            raw = self._engine._build_raw(cfg).strip()
            self._preview_label.setText(raw)
        except Exception as e:
            self._preview_label.setText(f"[Preview error: {e}]")
