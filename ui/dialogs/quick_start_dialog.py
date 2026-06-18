"""
ui/dialogs/quick_start_dialog.py
Quick Start Guide — displayed from Help menu.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QTextBrowser
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


QUICK_START_HTML = """
<html>
<body style="font-family: Segoe UI, Arial, sans-serif; font-size: 10pt; margin: 8px;">

<h2 style="color:#0078d4;">NMEA Tool — Quick Start Guide</h2>

<h3>Overview</h3>
<p>
NMEA Tool generates and transmits NMEA 0183 sentences over COM ports (USB-to-serial
adapters) and UDP network endpoints (e.g. Perle Serial Servers). It can also
receive and monitor incoming NMEA traffic on the same connections.
</p>

<hr/>

<h3>Step 1 — Add a Connection</h3>
<p>Go to the <b>Connections</b> tab.</p>

<p><b>UDP endpoint (Perle / network device):</b></p>
<ol>
  <li>Click <b>+ Add UDP Endpoint</b>.</li>
  <li>Set <b>Host / IP</b> to the device IP address (e.g. <tt>192.168.1.100</tt>).</li>
  <li>Set <b>Remote Port</b> to the device's UDP port (NMEA default is <tt>10110</tt>).</li>
  <li>Set <b>Local Port</b> to the same value (e.g. <tt>10110</tt>).<br/>
      This locks the outgoing source port so Perle devices always route
      return traffic back correctly after a restart.<br/>
      Leave at <tt>auto</tt> for a simple loopback test on <tt>127.0.0.1</tt>.</li>
  <li>Check <b>Send</b> and/or <b>Receive</b> as needed.</li>
  <li>Check <b>Enabled</b>.</li>
</ol>

<p><b>COM port (USB-to-serial adapter):</b></p>
<ol>
  <li>Click <b>+ Add COM Port</b>, then <b>↻ Refresh Ports</b> to populate the list.</li>
  <li>Select the port, baud rate (NMEA standard is <tt>4800</tt>), and parity.</li>
  <li>Check <b>Enabled</b>.</li>
</ol>

<p>Click <b>Apply Changes</b> when done. The engine will restart and open the connections.</p>

<hr/>

<h3>Step 2 — Add Sentences</h3>
<p>Go to the <b>Sentences</b> tab.</p>
<ol>
  <li>Browse or search the <b>Sentence Library</b> on the left.</li>
  <li>Click a sentence type to select it, then click <b>+ Add to Active</b>.</li>
  <li>Set the <b>Rate (Hz)</b> — e.g. <tt>1.0</tt> for once per second.</li>
  <li>To add a proprietary or custom sentence, click <b>+ Add Custom Sentence</b>
      and use the visual editor. You can paste a captured sentence into the
      Import box to reverse-engineer its fields automatically.</li>
</ol>

<hr/>

<h3>Step 3 — Route Sentences to Outputs</h3>
<p>
Select a sentence in the <b>Active Sentences</b> table.
The <b>Output Routing</b> panel at the bottom lists all configured connections.
Click one or more to assign that sentence to those outputs.
Each sentence can be routed to a different set of outputs independently.
</p>

<hr/>

<h3>Step 4 — Edit Field Values</h3>
<p>Go to the <b>Fields</b> tab.</p>
<p>
Select a sentence on the left. The table on the right shows every field with
its description, units, and current value. Edit the <b>Value</b> column directly.
Fields with a fixed set of valid values show a drop-down. A live sentence
preview updates at the bottom of the panel as you type.
</p>

<hr/>

<h3>Step 5 — Start the Engine</h3>
<p>
Click <b>Engine → Start</b> (or use the tray icon menu).
The engine starts automatically on launch if any connection is enabled.
</p>

<hr/>

<h3>Step 6 — Monitor Traffic</h3>
<p>Go to the <b>Monitor</b> tab.</p>
<ul>
  <li><span style="color:#4fc3f7;"><b>Blue</b></span> — sentences transmitted (TX)</li>
  <li><span style="color:#a5d6a7;"><b>Green</b></span> — sentences received (RX)</li>
  <li><span style="color:#fff176;"><b>Yellow</b></span> — parsed field values</li>
  <li><span style="color:#ef9a9a;"><b>Red</b></span> — errors</li>
</ul>
<p>
Use the <b>Filter</b> box to show only lines containing a keyword
(e.g. <tt>GGA</tt>, <tt>COM3</tt>, <tt>error</tt>).
Click <b>⏸ Pause</b> to freeze the display without dropping messages,
then <b>▶ Resume</b> to flush the buffer.
Click <b>💾 Save Log</b> to write the current log to a text file.
</p>

<hr/>

<h3>Saving Your Configuration</h3>
<p>
Use <b>File → Save Configuration</b> (<b>Ctrl+S</b>) to persist all connections,
sentences, field values, rates, and output routes. Settings are saved to
<tt>~/.nmea_tool/nmea_tool_config.json</tt> and restored automatically on next launch.
</p>

<hr/>

<h3>Loopback Test (no hardware needed)</h3>
<ol>
  <li>Add a UDP endpoint: Host <tt>127.0.0.1</tt>, Remote Port <tt>10110</tt>,
      Local Port <tt>auto</tt>, Send ✓, Receive ✓, Enabled ✓.</li>
  <li>Click <b>Apply Changes</b>.</li>
  <li>Add a sentence (e.g. GGA), route it to the UDP endpoint.</li>
  <li>Start the engine — the Monitor will show both TX and RX lines
      as packets loop back on localhost.</li>
</ol>

</body>
</html>
"""


class QuickStartDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Start Guide")
        self.setMinimumSize(640, 600)
        self.resize(720, 700)
        self.setModal(False)  # Non-modal so user can follow along in the main window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(QUICK_START_HTML)
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
