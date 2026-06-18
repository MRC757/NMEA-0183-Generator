"""
tests/run_editor_standalone.py

Launches the Custom Sentence Editor in isolation — no COM ports, no UDP,
no engine required. Useful for iterating on the dialog UI quickly.

Run directly:
    python tests/run_editor_standalone.py

Or use the VS Code launch config:
    "Debug Custom Sentence Editor (standalone)"
"""

import sys
import os

# Ensure project root is on the path when running standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QDialog
from config.app_config import NmeaSentenceConfig
from ui.dialogs.custom_sentence_editor import CustomSentenceEditor


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    print("=" * 60)
    print("  Custom Sentence Editor — Standalone Test Runner")
    print("=" * 60)
    print()
    print("Choose test mode:")
    print("  1. New sentence (blank editor)")
    print("  2. Edit existing custom sentence (pre-populated)")
    print()

    # For non-interactive CI runs, always use mode 1
    mode = "1"
    if sys.stdin.isatty():
        try:
            mode = input("Mode [1/2]: ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            mode = "1"

    if mode == "2":
        # Pre-populate with a Garmin PGRME sentence
        existing = NmeaSentenceConfig(
            sentence_id     = "GRME",
            talker_id       = "P",
            enabled         = True,
            rate_hz         = 1.0,
            is_custom       = True,
            custom_template = "PGRME,3.0,M,4.0,M,5.0,M",
            fields          = {
                "h_err":      "3.0",
                "h_err_unit": "M",
                "v_err":      "4.0",
                "v_err_unit": "M",
                "s_err":      "5.0",
                "s_err_unit": "M",
            },
            outputs = [],
        )
        editor = CustomSentenceEditor(cfg=existing)
        print("Editing existing sentence: $PGRME")
    else:
        editor = CustomSentenceEditor()
        print("Creating new sentence (blank)")

    print()
    print("Close the dialog to see the result...")
    print()

    result = editor.exec()

    if result == QDialog.DialogCode.Accepted:
        cfg = editor.result_config()
        print("✓  Dialog accepted.")
        print(f"   Talker ID    : {cfg.talker_id}")
        print(f"   Sentence ID  : {cfg.sentence_id}")
        print(f"   Fields       : {cfg.fields}")
        print(f"   Template     : {cfg.custom_template}")
        print(f"   Rate         : {cfg.rate_hz} Hz")
        print(f"   Enabled      : {cfg.enabled}")
    else:
        print("✗  Dialog cancelled.")

    sys.exit(0)


if __name__ == "__main__":
    main()
