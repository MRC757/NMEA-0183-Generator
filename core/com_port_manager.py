"""
core/com_port_manager.py
Manages multiple COM port connections for bidirectional NMEA I/O.
Each port runs in its own background thread.
Uses pyserial for Windows COM port access.
"""

import threading
import time
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# Baud rates tried in order during auto-detection (most common NMEA rates first)
DETECT_BAUD_RATES: List[int] = [4800, 9600, 19200, 38400, 57600, 115200]
DETECT_TIMEOUT_PER_RATE = 1.5   # seconds to listen at each rate


@dataclass
class PortStatus:
    port: str
    connected: bool = False
    error: str = ""
    bytes_sent: int = 0
    bytes_received: int = 0


class ComPortManager:
    """
    Manages multiple simultaneous COM port connections.
    Callbacks are invoked on background threads — use Qt signals
    to safely forward data to the UI.
    """

    def __init__(
        self,
        on_data_received: Callable[[str, str], None],  # (port_name, raw_sentence)
        on_error: Callable[[str, str], None],           # (port_name, error_msg)
        on_status_change: Callable[[str, PortStatus], None],
    ):
        self._on_data_received = on_data_received
        self._on_error = on_error
        self._on_status_change = on_status_change

        self._ports: Dict[str, serial.Serial] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._statuses: Dict[str, PortStatus] = {}
        self._lock = threading.Lock()

    def available_ports(self) -> list:
        """Return list of available COM port names on this machine."""
        if not SERIAL_AVAILABLE:
            return []
        return [p.device for p in serial.tools.list_ports.comports()]

    def open(self, port_name: str, baudrate: int = 4800,
             bytesize: int = 8, parity: str = "N",
             stopbits: float = 1.0) -> bool:
        """Open a COM port and start its read thread."""
        if not SERIAL_AVAILABLE:
            self._on_error(port_name, "pyserial is not installed.")
            return False

        with self._lock:
            if port_name in self._ports:
                return True  # Already open

        try:
            ser = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=1.0,
            )
        except Exception as e:
            status = PortStatus(port=port_name, connected=False, error=str(e))
            self._statuses[port_name] = status
            self._on_status_change(port_name, status)
            self._on_error(port_name, f"Failed to open {port_name}: {e}")
            return False

        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._read_loop,
            args=(port_name, ser, stop_event),
            daemon=True,
            name=f"ComPort-{port_name}",
        )

        with self._lock:
            self._ports[port_name] = ser
            self._stop_events[port_name] = stop_event
            self._threads[port_name] = thread

        status = PortStatus(port=port_name, connected=True)
        self._statuses[port_name] = status
        self._on_status_change(port_name, status)

        thread.start()
        return True

    def close(self, port_name: str) -> None:
        """Close a COM port and stop its read thread."""
        with self._lock:
            stop_event = self._stop_events.pop(port_name, None)
            ser = self._ports.pop(port_name, None)
            self._threads.pop(port_name, None)

        if stop_event:
            stop_event.set()
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass

        status = PortStatus(port=port_name, connected=False)
        self._statuses[port_name] = status
        self._on_status_change(port_name, status)

    def close_all(self) -> None:
        """Close all open COM ports."""
        for port_name in list(self._ports.keys()):
            self.close(port_name)

    def send(self, port_name: str, sentence: str) -> bool:
        """Send a raw NMEA sentence string to a COM port."""
        with self._lock:
            ser = self._ports.get(port_name)
        if not ser or not ser.is_open:
            return False
        try:
            data = sentence.encode("ascii", errors="replace")
            ser.write(data)
            if port_name in self._statuses:
                self._statuses[port_name].bytes_sent += len(data)
            return True
        except Exception as e:
            self._on_error(port_name, f"Send error on {port_name}: {e}")
            return False

    def send_to_all(self, sentence: str) -> None:
        """Send a sentence to all open COM ports."""
        for port_name in list(self._ports.keys()):
            self.send(port_name, sentence)

    def get_status(self, port_name: str) -> Optional[PortStatus]:
        return self._statuses.get(port_name)

    def is_open(self, port_name: str) -> bool:
        with self._lock:
            ser = self._ports.get(port_name)
        return ser is not None and ser.is_open

    def detect_baudrate(
        self,
        port_name: str,
        on_detected: Callable[[str, int], None],
        on_failed: Callable[[str], None],
    ) -> None:
        """
        Probe DETECT_BAUD_RATES in order and call on_detected(port, baud) with
        the first rate that yields a sentence with a valid NMEA checksum.
        Runs on a daemon thread so the UI stays responsive.
        """
        if not SERIAL_AVAILABLE:
            on_failed(port_name)
            return
        threading.Thread(
            target=self._detect_loop,
            args=(port_name, on_detected, on_failed),
            daemon=True,
            name=f"BaudDetect-{port_name}",
        ).start()

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _read_loop(self, port_name: str, ser: "serial.Serial",
                   stop_event: threading.Event) -> None:
        """Background thread: continuously read lines from the COM port."""
        buffer = b""
        while not stop_event.is_set():
            try:
                if not ser.is_open:
                    break
                chunk = ser.read(256)
                if chunk:
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        raw = line.decode("ascii", errors="replace").strip()
                        if raw.startswith("$") or raw.startswith("!"):
                            if port_name in self._statuses:
                                self._statuses[port_name].bytes_received += len(raw)
                            self._on_data_received(port_name, raw)
            except Exception as e:
                if not stop_event.is_set():
                    self._on_error(port_name, f"Read error on {port_name}: {e}")
                    # Update status
                    if port_name in self._statuses:
                        self._statuses[port_name].connected = False
                        self._statuses[port_name].error = str(e)
                    break
            time.sleep(0.001)

    def _detect_loop(
        self,
        port_name: str,
        on_detected: Callable[[str, int], None],
        on_failed: Callable[[str], None],
    ) -> None:
        from core.nmea_parser import calculate_checksum
        for baud in DETECT_BAUD_RATES:
            try:
                ser = serial.Serial(port=port_name, baudrate=baud, timeout=0.1)
                deadline = time.monotonic() + DETECT_TIMEOUT_PER_RATE
                buf = b""
                found = False
                while time.monotonic() < deadline:
                    chunk = ser.read(256)
                    if chunk:
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            text = line.decode("ascii", errors="ignore").strip()
                            if (text.startswith("$") or text.startswith("!")) and "*" in text:
                                try:
                                    body, cs = text[1:].rsplit("*", 1)
                                    if calculate_checksum(body) == cs[:2].upper():
                                        found = True
                                        break
                                except Exception:
                                    pass
                    if found:
                        break
                ser.close()
                if found:
                    on_detected(port_name, baud)
                    return
            except Exception:
                continue
        on_failed(port_name)
