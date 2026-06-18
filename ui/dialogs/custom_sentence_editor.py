"""
ui/dialogs/custom_sentence_editor.py

Full-featured visual editor for building custom / proprietary NMEA 0183 sentences.

Features
--------
- Named field table: add, remove, reorder fields with drag-and-drop
- Per-field attributes: name, description, value, units, type (text/choice/numeric)
- Choice editor: define a fixed set of valid values for a field
- Live sentence preview updating on every keystroke
- Checksum display (read-only, auto-calculated)
- Sentence ID and Talker ID inputs with validation
- Import: paste a raw NMEA sentence to reverse-engineer its fields
- Export / copy the finished sentence string to clipboard
- OK / Cancel — result available via .result() after exec()
"""

from __future__ import annotations

import re
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDoubleSpinBox, QCheckBox, QTextEdit,
    QDialogButtonBox, QMessageBox, QSplitter,
    QWidget, QToolButton, QAbstractItemView, QSizePolicy,
    QApplication,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon

from config.app_config import NmeaSentenceConfig
from core.nmea_parser import calculate_checksum, build_custom_sentence


# ---------------------------------------------------------------------------
# Field type constants
# ---------------------------------------------------------------------------
FIELD_TYPE_TEXT    = "Text"
FIELD_TYPE_NUMERIC = "Numeric"
FIELD_TYPE_CHOICE  = "Choice"
FIELD_TYPES = [FIELD_TYPE_TEXT, FIELD_TYPE_NUMERIC, FIELD_TYPE_CHOICE]

# Common talker IDs for the dropdown
COMMON_TALKERS = [
    "GP", "GN", "GL", "GA", "GB",   # GNSS
    "II",                             # Integrated instrumentation
    "HC",                             # Compass
    "HE",                             # Gyro
    "P",                              # Proprietary
    "SD",                             # Sounder
    "VD",                             # Velocity sensor
    "WI",                             # Weather instruments
    "EC",                             # ECDIS
    "AI",                             # AIS
    "RA",                             # RADAR
]


# ---------------------------------------------------------------------------
# Helper: parse a raw NMEA string into talker/sentence/fields
# ---------------------------------------------------------------------------

def _parse_raw_for_import(raw: str) -> Optional[dict]:
    """
    Attempt to decompose a raw NMEA sentence into parts.
    Returns dict with keys: talker_id, sentence_id, fields, checksum_ok
    or None on failure.
    """
    raw = raw.strip()
    if not raw.startswith("$"):
        return None

    body = raw[1:]
    checksum_ok = False

    if "*" in body:
        body, cs_part = body.rsplit("*", 1)
        provided = cs_part[:2].upper()
        calculated = calculate_checksum(body)
        checksum_ok = (provided == calculated)

    parts = body.split(",")
    if not parts:
        return None

    tag = parts[0]
    fields = parts[1:]

    if len(tag) >= 5:
        talker_id   = tag[:2]
        sentence_id = tag[2:]
    elif len(tag) >= 3:
        talker_id   = ""
        sentence_id = tag
    else:
        return None

    return {
        "talker_id":   talker_id,
        "sentence_id": sentence_id,
        "fields":      fields,
        "checksum_ok": checksum_ok,
    }


# ---------------------------------------------------------------------------
# Field row data (internal model)
# ---------------------------------------------------------------------------

class FieldRow:
    """One editable field in the custom sentence."""

    def __init__(
        self,
        name:        str = "",
        description: str = "",
        value:       str = "",
        units:       str = "",
        field_type:  str = FIELD_TYPE_TEXT,
        choices:     str = "",   # Pipe-separated: "N|S"
    ):
        self.name        = name
        self.description = description
        self.value       = value
        self.units       = units
        self.field_type  = field_type
        self.choices     = choices   # stored as "A|B|C"


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class CustomSentenceEditor(QDialog):
    """
    Modal dialog for creating or editing a custom NMEA 0183 sentence.

    Usage
    -----
        editor = CustomSentenceEditor(parent=self)
        # To edit an existing custom sentence:
        editor = CustomSentenceEditor(parent=self, cfg=existing_cfg)

        if editor.exec() == QDialog.DialogCode.Accepted:
            new_cfg = editor.result_config()
    """

    # Table column indices
    COL_NAME   = 0
    COL_DESC   = 1
    COL_TYPE   = 2
    COL_VALUE  = 3
    COL_UNITS  = 4
    COL_CHOICES = 5

    def __init__(
        self,
        parent=None,
        cfg: Optional[NmeaSentenceConfig] = None,
    ):
        super().__init__(parent)
        self._source_cfg = cfg

        self.setWindowTitle("Custom Sentence Editor")
        self.setMinimumSize(900, 650)
        self.resize(1050, 720)
        self.setModal(True)

        self._build_ui()
        self._connect_signals()

        if cfg is not None:
            self._load_from_config(cfg)
        else:
            self._reset_to_defaults()

        self._refresh_preview()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── Top section: identity + import ──────────────────────────────────
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        identity_group = QGroupBox("Sentence Identity")
        identity_grid  = QGridLayout(identity_group)

        identity_grid.addWidget(QLabel("Talker ID:"), 0, 0)
        self._talker_combo = QComboBox()
        self._talker_combo.setEditable(True)
        self._talker_combo.addItems(COMMON_TALKERS)
        self._talker_combo.setCurrentText("P")
        self._talker_combo.setToolTip(
            "Two-character talker ID prefix.\n"
            "Use 'P' for proprietary sentences."
        )
        self._talker_combo.setFixedWidth(80)
        identity_grid.addWidget(self._talker_combo, 0, 1)

        identity_grid.addWidget(QLabel("Sentence ID:"), 0, 2)
        self._sentence_id_edit = QLineEdit()
        self._sentence_id_edit.setPlaceholderText("e.g. PGRME  or  CUSTOM01")
        self._sentence_id_edit.setToolTip(
            "The sentence type identifier (up to 8 chars, uppercase).\n"
            "For proprietary sentences this typically starts with the manufacturer code."
        )
        self._sentence_id_edit.setFixedWidth(160)
        identity_grid.addWidget(self._sentence_id_edit, 0, 3)

        identity_grid.addWidget(QLabel("Description:"), 0, 4)
        self._description_edit = QLineEdit()
        self._description_edit.setPlaceholderText("Human-readable description (not transmitted)")
        identity_grid.addWidget(self._description_edit, 0, 5)

        identity_grid.setColumnStretch(5, 1)
        top_layout.addWidget(identity_group)

        # Import from raw sentence
        import_group = QGroupBox("Import from Raw Sentence  (paste a captured NMEA sentence to auto-populate fields)")
        import_layout = QHBoxLayout(import_group)
        self._import_edit = QLineEdit()
        self._import_edit.setPlaceholderText("$PGRME,3.0,M,4.0,M,5.0,M*20")
        self._import_edit.setFont(QFont("Consolas", 9))
        import_layout.addWidget(self._import_edit)
        self._import_btn = QPushButton("⬆  Import")
        self._import_btn.setFixedWidth(90)
        self._import_btn.clicked.connect(self._do_import)
        import_layout.addWidget(self._import_btn)
        top_layout.addWidget(import_group)

        splitter.addWidget(top_widget)

        # ── Middle section: field table ──────────────────────────────────────
        field_widget = QWidget()
        field_layout = QVBoxLayout(field_widget)
        field_layout.setContentsMargins(0, 0, 0, 0)

        field_header = QHBoxLayout()
        field_header.addWidget(QLabel("<b>Fields</b>  (ordered — drag rows to reorder)"))
        field_header.addStretch()

        self._add_field_btn = QPushButton("+ Add Field")
        self._add_field_btn.clicked.connect(self._add_field)
        field_header.addWidget(self._add_field_btn)

        self._dup_field_btn = QPushButton("⧉ Duplicate")
        self._dup_field_btn.clicked.connect(self._duplicate_field)
        field_header.addWidget(self._dup_field_btn)

        self._del_field_btn = QPushButton("− Remove")
        self._del_field_btn.clicked.connect(self._remove_field)
        field_header.addWidget(self._del_field_btn)

        self._move_up_btn = QPushButton("↑")
        self._move_up_btn.setFixedWidth(32)
        self._move_up_btn.setToolTip("Move selected field up")
        self._move_up_btn.clicked.connect(self._move_up)
        field_header.addWidget(self._move_up_btn)

        self._move_down_btn = QPushButton("↓")
        self._move_down_btn.setFixedWidth(32)
        self._move_down_btn.setToolTip("Move selected field down")
        self._move_down_btn.clicked.connect(self._move_down)
        field_header.addWidget(self._move_down_btn)

        field_layout.addLayout(field_header)

        self._field_table = QTableWidget(0, 6)
        self._field_table.setHorizontalHeaderLabels([
            "Field Name", "Description", "Type", "Default Value", "Units", "Choices (pipe-separated)"
        ])
        hdr = self._field_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self._field_table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._field_table.setDragDropOverwriteMode(False)
        self._field_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._field_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._field_table.verticalHeader().setSectionsMovable(True)
        self._field_table.verticalHeader().setDragEnabled(True)
        self._field_table.verticalHeader().setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._field_table.setAlternatingRowColors(True)
        self._field_table.setMinimumHeight(200)

        field_layout.addWidget(self._field_table)
        splitter.addWidget(field_widget)

        # ── Bottom section: preview ──────────────────────────────────────────
        preview_group = QGroupBox("Live Preview")
        preview_layout = QGridLayout(preview_group)

        preview_layout.addWidget(QLabel("Raw sentence:"), 0, 0)
        self._preview_raw = QLineEdit()
        self._preview_raw.setReadOnly(True)
        self._preview_raw.setFont(QFont("Consolas", 10))
        self._preview_raw.setStyleSheet("background: #1e1e1e; color: #4fc3f7;")
        preview_layout.addWidget(self._preview_raw, 0, 1)

        self._copy_btn = QPushButton("📋 Copy")
        self._copy_btn.setFixedWidth(70)
        self._copy_btn.clicked.connect(self._copy_preview)
        preview_layout.addWidget(self._copy_btn, 0, 2)

        preview_layout.addWidget(QLabel("Checksum:"), 1, 0)
        self._checksum_label = QLabel("")
        self._checksum_label.setFont(QFont("Consolas", 10))
        preview_layout.addWidget(self._checksum_label, 1, 1)

        preview_layout.addWidget(QLabel("Byte length:"), 2, 0)
        self._length_label = QLabel("")
        preview_layout.addWidget(self._length_label, 2, 1)

        self._validation_label = QLabel("")
        self._validation_label.setWordWrap(True)
        preview_layout.addWidget(self._validation_label, 3, 0, 1, 3)

        preview_layout.setColumnStretch(1, 1)
        splitter.addWidget(preview_group)

        splitter.setSizes([160, 380, 160])
        root.addWidget(splitter, 1)

        # ── Dialog buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._reset_btn = QPushButton("↺ Reset to Defaults")
        self._reset_btn.clicked.connect(self._reset_to_defaults)
        btn_row.addWidget(self._reset_btn)

        btn_row.addStretch()

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        btn_row.addWidget(self._button_box)

        root.addLayout(btn_row)

    # -----------------------------------------------------------------------
    # Signal wiring
    # -----------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._talker_combo.currentTextChanged.connect(self._refresh_preview)
        self._sentence_id_edit.textChanged.connect(self._refresh_preview)
        self._field_table.itemChanged.connect(self._on_table_item_changed)
        self._field_table.cellChanged.connect(lambda *_: self._refresh_preview())
        self._field_table.model().rowsMoved.connect(lambda *_: self._refresh_preview())

    # -----------------------------------------------------------------------
    # Load / reset
    # -----------------------------------------------------------------------

    def _load_from_config(self, cfg: NmeaSentenceConfig) -> None:
        """Populate the editor from an existing NmeaSentenceConfig."""
        self._talker_combo.setCurrentText(cfg.talker_id)
        self._sentence_id_edit.setText(cfg.sentence_id)
        self._description_edit.setText(getattr(cfg, "description", ""))

        self._field_table.blockSignals(True)
        self._field_table.setRowCount(0)

        if cfg.is_custom and cfg.custom_template:
            # Reverse-engineer template into fields
            template = cfg.custom_template.strip()
            # Strip tag (talker+sentence) from template if present
            tag = f"{cfg.talker_id}{cfg.sentence_id}"
            if template.startswith(tag + ","):
                template = template[len(tag) + 1:]
            elif template.startswith(tag):
                template = template[len(tag):]
            raw_fields = template.split(",")
            for i, val in enumerate(raw_fields):
                self._insert_table_row(FieldRow(
                    name=f"field_{i+1:02d}",
                    description="",
                    value=val,
                    field_type=FIELD_TYPE_TEXT,
                ))
        else:
            # Load from named fields dict
            for name, value in cfg.fields.items():
                self._insert_table_row(FieldRow(name=name, value=value, field_type=FIELD_TYPE_TEXT))

        self._field_table.blockSignals(False)
        self._refresh_preview()

    def _reset_to_defaults(self) -> None:
        """Clear all fields and reset to a blank proprietary sentence template."""
        self._talker_combo.setCurrentText("P")
        self._sentence_id_edit.setText("PCUSTOM")
        self._description_edit.setText("")
        self._import_edit.clear()

        self._field_table.blockSignals(True)
        self._field_table.setRowCount(0)

        for fr in [
            FieldRow("field_01", "First field",  "value1", "", FIELD_TYPE_TEXT),
            FieldRow("field_02", "Second field", "value2", "", FIELD_TYPE_TEXT),
        ]:
            self._insert_table_row(fr)

        self._field_table.blockSignals(False)
        self._refresh_preview()

    # -----------------------------------------------------------------------
    # Field table operations
    # -----------------------------------------------------------------------

    def _insert_table_row(self, fr: FieldRow, row: int = -1) -> None:
        """Append or insert a FieldRow into the QTableWidget."""
        if row == -1:
            row = self._field_table.rowCount()
        self._field_table.insertRow(row)

        self._field_table.setItem(row, self.COL_NAME,  QTableWidgetItem(fr.name))
        self._field_table.setItem(row, self.COL_DESC,  QTableWidgetItem(fr.description))

        type_combo = QComboBox()
        type_combo.addItems(FIELD_TYPES)
        type_combo.setCurrentText(fr.field_type)
        type_combo.currentTextChanged.connect(
            lambda text, r=row: self._on_type_changed(r, text)
        )
        self._field_table.setCellWidget(row, self.COL_TYPE, type_combo)

        self._field_table.setItem(row, self.COL_VALUE,   QTableWidgetItem(fr.value))
        self._field_table.setItem(row, self.COL_UNITS,   QTableWidgetItem(fr.units))
        self._field_table.setItem(row, self.COL_CHOICES, QTableWidgetItem(fr.choices))

        self._update_choices_state(row, fr.field_type)

    def _add_field(self) -> None:
        fr = FieldRow(
            name=f"field_{self._field_table.rowCount()+1:02d}",
            field_type=FIELD_TYPE_TEXT,
        )
        self._field_table.blockSignals(True)
        self._insert_table_row(fr)
        self._field_table.blockSignals(False)
        self._refresh_preview()
        # Select and scroll to new row
        new_row = self._field_table.rowCount() - 1
        self._field_table.selectRow(new_row)
        self._field_table.scrollToBottom()

    def _duplicate_field(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        src_row = rows[0]
        fr = self._read_row(src_row)
        fr.name = fr.name + "_copy"
        self._field_table.blockSignals(True)
        self._insert_table_row(fr)
        self._field_table.blockSignals(False)
        self._refresh_preview()

    def _remove_field(self) -> None:
        rows = sorted(self._selected_rows(), reverse=True)
        self._field_table.blockSignals(True)
        for r in rows:
            self._field_table.removeRow(r)
        self._field_table.blockSignals(False)
        self._refresh_preview()

    def _move_up(self) -> None:
        rows = self._selected_rows()
        if not rows or rows[0] == 0:
            return
        r = rows[0]
        self._swap_rows(r, r - 1)
        self._field_table.selectRow(r - 1)
        self._refresh_preview()

    def _move_down(self) -> None:
        rows = self._selected_rows()
        if not rows or rows[0] >= self._field_table.rowCount() - 1:
            return
        r = rows[0]
        self._swap_rows(r, r + 1)
        self._field_table.selectRow(r + 1)
        self._refresh_preview()

    def _swap_rows(self, r1: int, r2: int) -> None:
        """Swap two rows in the field table by reading and re-writing data."""
        self._field_table.blockSignals(True)
        fr1 = self._read_row(r1)
        fr2 = self._read_row(r2)
        self._write_row(r1, fr2)
        self._write_row(r2, fr1)
        self._field_table.blockSignals(False)

    def _read_row(self, row: int) -> FieldRow:
        """Read the current values from a table row into a FieldRow."""
        def cell(col):
            item = self._field_table.item(row, col)
            return item.text() if item else ""

        widget = self._field_table.cellWidget(row, self.COL_TYPE)
        ftype = widget.currentText() if widget else FIELD_TYPE_TEXT

        return FieldRow(
            name        = cell(self.COL_NAME),
            description = cell(self.COL_DESC),
            field_type  = ftype,
            value       = cell(self.COL_VALUE),
            units       = cell(self.COL_UNITS),
            choices     = cell(self.COL_CHOICES),
        )

    def _write_row(self, row: int, fr: FieldRow) -> None:
        """Write a FieldRow back into a table row."""
        self._field_table.setItem(row, self.COL_NAME,    QTableWidgetItem(fr.name))
        self._field_table.setItem(row, self.COL_DESC,    QTableWidgetItem(fr.description))
        widget = self._field_table.cellWidget(row, self.COL_TYPE)
        if widget:
            widget.setCurrentText(fr.field_type)
        self._field_table.setItem(row, self.COL_VALUE,   QTableWidgetItem(fr.value))
        self._field_table.setItem(row, self.COL_UNITS,   QTableWidgetItem(fr.units))
        self._field_table.setItem(row, self.COL_CHOICES, QTableWidgetItem(fr.choices))
        self._update_choices_state(row, fr.field_type)

    def _on_type_changed(self, row: int, field_type: str) -> None:
        self._update_choices_state(row, field_type)
        self._refresh_preview()

    def _update_choices_state(self, row: int, field_type: str) -> None:
        """Enable/disable the Choices cell depending on field type."""
        item = self._field_table.item(row, self.COL_CHOICES)
        if item is None:
            item = QTableWidgetItem("")
            self._field_table.setItem(row, self.COL_CHOICES, item)

        if field_type == FIELD_TYPE_CHOICE:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setForeground(QColor("#ffffff"))
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setForeground(QColor("#666666"))

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        self._refresh_preview()

    def _selected_rows(self) -> List[int]:
        return sorted(set(idx.row() for idx in self._field_table.selectedIndexes()))

    # -----------------------------------------------------------------------
    # Import
    # -----------------------------------------------------------------------

    def _do_import(self) -> None:
        """Parse a pasted raw NMEA sentence and populate the editor."""
        raw = self._import_edit.text().strip()
        if not raw:
            return

        parsed = _parse_raw_for_import(raw)
        if parsed is None:
            QMessageBox.warning(
                self, "Import Failed",
                "Could not parse the sentence. Make sure it starts with '$' "
                "and follows standard NMEA format."
            )
            return

        if not parsed["checksum_ok"] and "*" in raw:
            reply = QMessageBox.question(
                self, "Checksum Mismatch",
                "The sentence checksum does not match. Import anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._talker_combo.setCurrentText(parsed["talker_id"] or "P")
        self._sentence_id_edit.setText(parsed["sentence_id"])

        self._field_table.blockSignals(True)
        self._field_table.setRowCount(0)
        self._field_rows.clear()

        for i, val in enumerate(parsed["fields"]):
            fr = FieldRow(
                name=f"field_{i+1:02d}",
                description="",
                value=val,
                field_type=FIELD_TYPE_TEXT,
            )
            self._field_rows.append(fr)
            self._insert_table_row(fr)

        self._field_table.blockSignals(False)
        self._refresh_preview()

    # -----------------------------------------------------------------------
    # Live preview
    # -----------------------------------------------------------------------

    def _build_sentence_body(self) -> str:
        """Build the raw sentence body (tag + comma + fields, no $ or checksum)."""
        talker = self._talker_combo.currentText().strip().upper()
        sid    = self._sentence_id_edit.text().strip().upper()
        tag    = f"{talker}{sid}"

        field_values = []
        for row in range(self._field_table.rowCount()):
            item = self._field_table.item(row, self.COL_VALUE)
            field_values.append(item.text() if item else "")

        return tag + "," + ",".join(field_values)

    def _refresh_preview(self) -> None:
        """Rebuild preview, checksum, and validation every time something changes."""
        try:
            body = self._build_sentence_body()
            checksum = calculate_checksum(body)
            sentence = f"${body}*{checksum}\r\n"
            display  = sentence.strip()

            self._preview_raw.setText(display)
            self._checksum_label.setText(f"*{checksum}")
            byte_len = len(sentence.encode("ascii"))
            self._length_label.setText(f"{byte_len} bytes")

            # NMEA spec: max 82 chars between $ and CRLF inclusive
            content_len = len(display)
            warnings = []

            if content_len > 82:
                warnings.append(
                    f"⚠  Sentence is {content_len} chars — exceeds the NMEA 82-char limit. "
                    "Some receivers may reject it."
                )

            sid = self._sentence_id_edit.text().strip()
            if not sid:
                warnings.append("⚠  Sentence ID is empty.")
            elif not re.match(r"^[A-Za-z0-9]{1,8}$", sid):
                warnings.append("⚠  Sentence ID should be 1–8 alphanumeric characters.")

            if warnings:
                self._validation_label.setText("\n".join(warnings))
                self._validation_label.setStyleSheet("color: #f39c12;")
            else:
                self._validation_label.setText("✓  Sentence looks valid.")
                self._validation_label.setStyleSheet("color: #2ecc71;")

        except Exception as e:
            self._preview_raw.setText(f"[Error: {e}]")
            self._validation_label.setText(f"Error building sentence: {e}")
            self._validation_label.setStyleSheet("color: #e74c3c;")

    def _copy_preview(self) -> None:
        text = self._preview_raw.text()
        if text:
            QApplication.clipboard().setText(text)

    # -----------------------------------------------------------------------
    # Build result config
    # -----------------------------------------------------------------------

    def result_config(self) -> NmeaSentenceConfig:
        """
        Return the NmeaSentenceConfig represented by the current editor state.
        Call only after exec() returns Accepted.
        """
        talker = self._talker_combo.currentText().strip().upper()
        sid    = self._sentence_id_edit.text().strip().upper()

        # Build fields dict (name -> default value)
        fields_dict = {}
        for row in range(self._field_table.rowCount()):
            name_item  = self._field_table.item(row, self.COL_NAME)
            value_item = self._field_table.item(row, self.COL_VALUE)
            name  = name_item.text()  if name_item  else f"field_{row+1:02d}"
            value = value_item.text() if value_item else ""
            fields_dict[name] = value

        # Build the raw template body for storage
        tag    = f"{talker}{sid}"
        values = list(fields_dict.values())
        template_body = tag + "," + ",".join(values)

        # Preserve non-custom attributes from the source config if editing
        if self._source_cfg is not None:
            cfg = NmeaSentenceConfig(
                sentence_id     = sid,
                talker_id       = talker,
                enabled         = self._source_cfg.enabled,
                rate_hz         = self._source_cfg.rate_hz,
                fields          = fields_dict,
                outputs         = list(self._source_cfg.outputs),
                is_custom       = True,
                custom_template = template_body,
            )
        else:
            cfg = NmeaSentenceConfig(
                sentence_id     = sid,
                talker_id       = talker,
                enabled         = True,
                rate_hz         = 1.0,
                fields          = fields_dict,
                outputs         = [],
                is_custom       = True,
                custom_template = template_body,
            )

        return cfg

    # -----------------------------------------------------------------------
    # Accept / validation
    # -----------------------------------------------------------------------

    def _on_accept(self) -> None:
        sid = self._sentence_id_edit.text().strip()
        if not sid:
            QMessageBox.warning(self, "Validation Error", "Sentence ID cannot be empty.")
            return
        if self._field_table.rowCount() == 0:
            reply = QMessageBox.question(
                self, "No Fields",
                "The sentence has no fields. Accept anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.accept()
