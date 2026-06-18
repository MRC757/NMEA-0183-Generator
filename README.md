# NMEA Tool

A bidirectional NMEA 0183 simulator, sender, and monitor for Windows 10/11.
Sends and receives over multiple simultaneous COM ports (USB-to-serial) and
UDP endpoints (Perle UDP-to-Serial and network devices).

Distributed as a single portable `.exe` — no Python or dependencies required
on the target machine.

---

## Features

| Feature | Detail |
|---|---|
| **Full NMEA 0183 sentence set** | All standard sentences with named fields + custom/proprietary sentences |
| **Custom Sentence Editor** | Visual field builder, import from raw sentence, live preview, drag-to-reorder |
| **Multiple COM ports** | Simultaneous bidirectional I/O, configurable baud/parity/stop bits |
| **Multiple UDP endpoints** | Perle UDP-to-Serial, broadcast, unicast — send and/or receive per endpoint |
| **Per-sentence TX rates** | Independent Hz setting per sentence (0.1–100 Hz, 5ms scheduler resolution) |
| **Output routing** | Assign each sentence to any combination of COM and UDP outputs |
| **Live monitor** | Colour-coded TX / RX / parsed fields / errors — filterable, pausable, saveable |
| **Dark mode** | Full Fusion dark palette |
| **System tray** | Minimises to tray, double-click to restore |
| **Persistent config** | All settings auto-saved to `nmea_tool_config.json` next to the EXE |
| **Zero end-user install** | Single portable EXE built with PyInstaller |

---

## Project Structure

```
nmea_tool/
│
├── main.py                          Entry point
├── requirements.txt                 Development dependencies
├── pytest.ini                       Test configuration
├── .gitignore
│
├── nmea_tool.code-workspace         Open this in VS Code
│
├── .vscode/
│   ├── settings.json                Python interpreter, formatter, paths
│   ├── launch.json                  Debug configs (app, tests, editor standalone)
│   ├── tasks.json                   Run / build / test tasks (Ctrl+Shift+B)
│   └── extensions.json              Recommended extensions
│
├── config/
│   └── app_config.py                Persistent JSON config — all dataclasses
│
├── core/
│   ├── engine.py                    Central controller, Qt signal bridge
│   ├── nmea_parser.py               Encode / decode / checksum (zero deps)
│   ├── nmea_sentences.py            Full standard sentence + field definitions
│   ├── com_port_manager.py          Multi-port COM I/O (pyserial + threading)
│   ├── udp_manager.py               Multi-endpoint UDP I/O (socket + threading)
│   └── scheduler.py                 Per-sentence rate scheduler (5ms tick)
│
├── ui/
│   ├── main_window.py               Tabbed window, menu, system tray
│   ├── dialogs/
│   │   └── custom_sentence_editor.py   Custom / proprietary sentence builder
│   └── tabs/
│       ├── connections_tab.py       COM port + UDP endpoint configuration
│       ├── sentences_tab.py         Enable sentences, set rates, route outputs
│       ├── fields_tab.py            Edit field values, custom templates
│       └── monitor_tab.py           Live colour-coded NMEA monitor
│
├── utils/
│   └── theme.py                     Light / dark Fusion theme
│
├── build/
│   └── build.bat                    PyInstaller build script (run on Windows)
│
├── resources/                       Icons and assets (add app.ico here)
│
└── tests/
    ├── run_editor_standalone.py     Launch Custom Sentence Editor without full app
    ├── test_nmea_parser.py          Unit tests — parser, checksum, build/parse
    └── test_custom_sentence_editor.py  Unit tests — editor dialog logic
```

---

## Quick Start (Development)

### 1. Prerequisites

- Python 3.11+ (https://www.python.org/downloads/)
- VS Code (https://code.visualstudio.com/)

### 2. Clone / download the project

```
git clone <repo-url>
cd nmea_tool
```

### 3. Open in VS Code

Double-click `nmea_tool.code-workspace`, or:

```
code nmea_tool.code-workspace
```

VS Code will prompt you to install recommended extensions — accept.

### 4. Create a virtual environment

Press `Ctrl+Shift+B` and choose **🏗 Create Virtual Environment**, or run:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run the app

Press `F5` (Run NMEA Tool) or `Ctrl+Shift+B` → **▶ Run App**.

---

## Running Tests

```bat
python -m pytest tests/ -v
```

Or press `Ctrl+Shift+B` → **🧪 Run Tests**.

To test just the parser (no display needed):
```bat
python -m pytest tests/test_nmea_parser.py -v
```

To launch the Custom Sentence Editor standalone (useful for UI iteration):
```bat
python tests/run_editor_standalone.py
```

---

## Building the Portable EXE

Run on your Windows development machine:

```bat
cd build
build.bat
```

Output: `dist\NMEATool.exe`

Copy `NMEATool.exe` to any Windows 10/11 machine and run it — no Python,
no pip, no installs of any kind required on the target machine.

---

## Custom Sentence Editor

The Custom Sentence Editor (`ui/dialogs/custom_sentence_editor.py`) is a
standalone dialog for building proprietary and non-standard NMEA sentences.

### Opening it

- **Sentences tab → "+ Add Custom Sentence"** — opens a blank editor
- **Sentences tab → "✏ Edit Custom..."** — opens editor pre-populated with
  the selected custom sentence

### Features

| Section | What it does |
|---|---|
| **Sentence Identity** | Set Talker ID (dropdown + editable) and Sentence ID |
| **Import** | Paste any captured `$...` sentence — auto-populates fields |
| **Fields table** | Add / remove / duplicate / reorder fields via buttons or drag-and-drop |
| **Field attributes** | Name, description, type (Text / Numeric / Choice), default value, units |
| **Choices** | For Choice type fields, enter pipe-separated valid values: `N\|S` or `A\|D\|E\|M\|S\|N` |
| **Live Preview** | Full sentence string with auto-calculated checksum, updated on every keystroke |
| **Validation** | Warns if sentence exceeds 82-char NMEA limit, or Sentence ID is invalid |
| **Copy** | One-click copy of the preview sentence to clipboard |

### Programmatic use

```python
from ui.dialogs.custom_sentence_editor import CustomSentenceEditor
from PySide6.QtWidgets import QDialog

editor = CustomSentenceEditor(parent=self)

# To pre-populate from an existing config:
editor = CustomSentenceEditor(parent=self, cfg=existing_nmea_sentence_config)

if editor.exec() == QDialog.DialogCode.Accepted:
    cfg = editor.result_config()   # Returns NmeaSentenceConfig
    # cfg.is_custom == True
    # cfg.custom_template == "PGRME,3.0,M,4.0,M,5.0,M"
    # cfg.fields == {"field_01": "3.0", "field_02": "M", ...}
```

---

## Adding a New Standard Sentence

1. Open `core/nmea_sentences.py`
2. Add a `NmeaSentenceDef(...)` entry with `NmeaFieldDef` entries for each field
3. Add the sentence to the correct category — it appears automatically in the UI tree

Optionally add a parser:

1. Open `core/nmea_parser.py`
2. Add a `parse_xxx(fields)` function
3. Register it in the `PARSERS` dict

---

## Architecture

### Threading model

```
Main thread (Qt event loop)
    │
    ├── NmeaEngine (QObject)
    │       │  owns:
    │       ├── ComPortManager
    │       │       └── [thread per COM port]  reads/writes serial
    │       ├── UdpManager
    │       │       └── [thread per UDP endpoint]  recvfrom loop
    │       └── Scheduler
    │               └── [one background thread]  5ms tick, fires sentences
    │
    └── UI (MainWindow, tabs, dialogs)
            Receives data via Qt signals — always on the main thread
```

All I/O threads post data back to the UI via `NmeaEngine`'s Qt signals
(`sentence_sent`, `sentence_received`, `sentence_parsed`, `error_occurred`).
This guarantees thread-safe UI updates without manual locking in the UI layer.

### Config flow

```
AppConfig (JSON on disk)
    └── loaded at startup → passed to NmeaEngine + all tabs
    └── updated live as user changes settings
    └── saved on Ctrl+S or window close
```

### Sentence lifecycle (outbound)

```
User configures sentence in SentencesTab + FieldsTab
    → NmeaSentenceConfig stored in AppConfig.sentences
    → ScheduledSentence registered with Scheduler
    → Scheduler fires at rate_hz
    → build_fn() calls nmea_parser.build_sentence() or build_custom_sentence()
    → NmeaEngine._dispatch() routes to ComPortManager.send() or UdpManager.send()
    → sentence_sent signal → MonitorTab.on_sentence_sent()
```

---

## Configuration File

Settings are saved to `nmea_tool_config.json` next to the EXE (or in the
project root during development). The file is human-readable JSON.

To reset to defaults, delete the file or use:
`Ctrl+Shift+B` → **🗑 Clear Config File**

---

## Dependencies

| Package | Version | Purpose | End-user install? |
|---|---|---|---|
| PySide6 | ≥6.6 | Qt UI framework | ❌ Bundled by PyInstaller |
| pyserial | ≥3.5 | COM port access | ❌ Bundled by PyInstaller |
| PyInstaller | ≥6.0 | Build EXE | Developer only |
| pytest | any | Testing | Developer only |

Standard library used for UDP (`socket`), threading (`threading`),
config (`json`), and scheduling (`time`) — zero additional installs.

---

## License

MIT — see LICENSE file.
