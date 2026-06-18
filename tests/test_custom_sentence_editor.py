"""
tests/test_custom_sentence_editor.py
Unit tests for the CustomSentenceEditor dialog logic.
Tests the non-UI helper functions and the result_config() output
without requiring a display (uses QApplication in offscreen mode).

Run with:  python -m pytest tests/test_custom_sentence_editor.py -v
"""

import sys
import os
import pytest

# Must create QApplication before importing PySide6 widgets
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# One QApplication for all tests in this module
@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication(sys.argv)
    return application


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

from ui.dialogs.custom_sentence_editor import (
    _parse_raw_for_import,
    CustomSentenceEditor,
    FieldRow,
    FIELD_TYPE_TEXT,
    FIELD_TYPE_NUMERIC,
    FIELD_TYPE_CHOICE,
)
from config.app_config import NmeaSentenceConfig
from core.nmea_parser import calculate_checksum


# ---------------------------------------------------------------------------
# _parse_raw_for_import
# ---------------------------------------------------------------------------

class TestParseRawForImport:

    def test_valid_gga(self):
        raw = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        result = _parse_raw_for_import(raw)
        assert result is not None
        assert result["talker_id"] == "GP"
        assert result["sentence_id"] == "GGA"
        assert result["checksum_ok"] is True
        assert result["fields"][0] == "123519"

    def test_valid_proprietary(self):
        raw = "$PGRME,3.0,M,4.0,M,5.0,M*20"
        result = _parse_raw_for_import(raw)
        assert result is not None
        assert result["talker_id"] == "PG"
        assert "3.0" in result["fields"]

    def test_bad_checksum(self):
        raw = "$GPGGA,123519,4807.038,N*FF"
        result = _parse_raw_for_import(raw)
        assert result is not None
        assert result["checksum_ok"] is False

    def test_no_dollar(self):
        result = _parse_raw_for_import("GPGGA,123519")
        assert result is None

    def test_empty_string(self):
        result = _parse_raw_for_import("")
        assert result is None

    def test_whitespace_stripped(self):
        raw = "  $GPGLL,4807.038,N,01131.000,E,123519,A,A*7F  "
        result = _parse_raw_for_import(raw)
        assert result is not None

    def test_field_count(self):
        raw = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        result = _parse_raw_for_import(raw)
        assert result is not None
        assert len(result["fields"]) == 11


# ---------------------------------------------------------------------------
# CustomSentenceEditor — dialog creation and result_config
# ---------------------------------------------------------------------------

class TestCustomSentenceEditorDialog:

    def test_creates_without_config(self, app):
        editor = CustomSentenceEditor()
        assert editor is not None
        editor.close()

    def test_creates_with_existing_config(self, app):
        cfg = NmeaSentenceConfig(
            sentence_id="GRME",
            talker_id="P",
            enabled=True,
            rate_hz=1.0,
            is_custom=True,
            custom_template="PGRME,3.0,M,4.0,M,5.0,M",
            fields={"h_err": "3.0", "h_err_unit": "M"},
            outputs=[],
        )
        editor = CustomSentenceEditor(cfg=cfg)
        assert editor._talker_combo.currentText() == "P"
        assert editor._sentence_id_edit.text() == "GRME"
        editor.close()

    def test_result_config_defaults(self, app):
        editor = CustomSentenceEditor()
        cfg = editor.result_config()
        assert cfg.is_custom is True
        assert cfg.talker_id != ""
        assert cfg.sentence_id != ""
        editor.close()

    def test_result_config_preserves_rate_from_source(self, app):
        source = NmeaSentenceConfig(
            sentence_id="GRME",
            talker_id="P",
            enabled=True,
            rate_hz=5.0,
            is_custom=True,
            custom_template="PGRME,3.0,M",
            fields={"h_err": "3.0"},
            outputs=["COM1"],
        )
        editor = CustomSentenceEditor(cfg=source)
        cfg = editor.result_config()
        assert cfg.rate_hz == 5.0
        assert cfg.outputs == ["COM1"]
        editor.close()

    def test_result_config_template_has_tag(self, app):
        editor = CustomSentenceEditor()
        editor._talker_combo.setCurrentText("GP")
        editor._sentence_id_edit.setText("HDT")
        cfg = editor.result_config()
        assert cfg.custom_template.startswith("GPHDT")
        editor.close()

    def test_add_field_increases_row_count(self, app):
        editor = CustomSentenceEditor()
        initial = editor._field_table.rowCount()
        editor._add_field()
        assert editor._field_table.rowCount() == initial + 1
        editor.close()

    def test_remove_field_decreases_row_count(self, app):
        editor = CustomSentenceEditor()
        initial = editor._field_table.rowCount()
        editor._field_table.selectRow(0)
        editor._remove_field()
        assert editor._field_table.rowCount() == initial - 1
        editor.close()

    def test_duplicate_field(self, app):
        editor = CustomSentenceEditor()
        initial = editor._field_table.rowCount()
        editor._field_table.selectRow(0)
        editor._duplicate_field()
        assert editor._field_table.rowCount() == initial + 1
        editor.close()

    def test_preview_updates_on_sentence_id_change(self, app):
        editor = CustomSentenceEditor()
        editor._sentence_id_edit.setText("MYTEST")
        preview = editor._preview_raw.text()
        assert "MYTEST" in preview
        editor.close()

    def test_preview_contains_dollar(self, app):
        editor = CustomSentenceEditor()
        preview = editor._preview_raw.text()
        assert preview.startswith("$")
        editor.close()

    def test_preview_checksum_is_valid(self, app):
        editor = CustomSentenceEditor()
        preview = editor._preview_raw.text().strip()
        assert "*" in preview
        body, cs = preview[1:].rsplit("*", 1)
        assert calculate_checksum(body) == cs.upper()
        editor.close()

    def test_import_populates_fields(self, app):
        editor = CustomSentenceEditor()
        editor._import_edit.setText("$GPGLL,4807.038,N,01131.000,E,123519,A,A*7F")
        editor._do_import()
        assert editor._sentence_id_edit.text() == "GLL"
        assert editor._field_table.rowCount() == 7
        editor.close()

    def test_import_bad_sentence_shows_no_crash(self, app, monkeypatch):
        # Monkeypatch QMessageBox so it doesn't block in tests
        monkeypatch.setattr(
            "ui.dialogs.custom_sentence_editor.QMessageBox.warning",
            lambda *a, **kw: None,
        )
        editor = CustomSentenceEditor()
        editor._import_edit.setText("not a sentence at all")
        editor._do_import()  # Should not raise
        editor.close()

    def test_reset_to_defaults(self, app):
        editor = CustomSentenceEditor()
        editor._sentence_id_edit.setText("SOMETHING")
        editor._reset_to_defaults()
        assert editor._sentence_id_edit.text() == "PCUSTOM"
        editor.close()

    def test_move_up_swap(self, app):
        editor = CustomSentenceEditor()
        # Ensure at least 2 rows
        while editor._field_table.rowCount() < 2:
            editor._add_field()
        # Set distinct names
        editor._field_table.item(0, 0).setText("alpha")
        editor._field_table.item(1, 0).setText("beta")
        # Select row 1 and move up
        editor._field_table.selectRow(1)
        editor._move_up()
        assert editor._field_table.item(0, 0).text() == "beta"
        assert editor._field_table.item(1, 0).text() == "alpha"
        editor.close()

    def test_move_down_swap(self, app):
        editor = CustomSentenceEditor()
        while editor._field_table.rowCount() < 2:
            editor._add_field()
        editor._field_table.item(0, 0).setText("first")
        editor._field_table.item(1, 0).setText("second")
        editor._field_table.selectRow(0)
        editor._move_down()
        assert editor._field_table.item(0, 0).text() == "second"
        assert editor._field_table.item(1, 0).text() == "first"
        editor.close()

    def test_result_fields_match_table(self, app):
        editor = CustomSentenceEditor()
        editor._field_table.setRowCount(0)
        # Manually add one field
        from ui.dialogs.custom_sentence_editor import FieldRow
        fr = FieldRow(name="myfield", value="42", field_type=FIELD_TYPE_TEXT)
        editor._field_table.blockSignals(True)
        editor._insert_table_row(fr)
        editor._field_table.blockSignals(False)
        cfg = editor.result_config()
        assert "myfield" in cfg.fields
        assert cfg.fields["myfield"] == "42"
        editor.close()
