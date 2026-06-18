"""
core/engine.py
The central NMEA engine.
Owns the scheduler, COM manager, and UDP manager.
Bridges background threads to the Qt UI via signals.
"""

from PySide6.QtCore import QObject, Signal
from typing import List

from config.app_config import AppConfig, NmeaSentenceConfig
from core.com_port_manager import ComPortManager, PortStatus
from core.udp_manager import UdpManager, UdpStatus
from core.scheduler import Scheduler, ScheduledSentence
from core.nmea_parser import build_sentence, build_custom_sentence, parse_sentence, parse_fields


class NmeaEngine(QObject):
    """
    Central controller. All I/O threads post data back here via Qt signals,
    which guarantees safe delivery to the UI on the main thread.
    """

    # Emitted when a sentence is sent (output_id, raw)
    sentence_sent = Signal(str, str)

    # Emitted when a sentence is received (source_id, raw)
    sentence_received = Signal(str, str)

    # Emitted when a sentence is parsed (source_id, sentence_id, parsed_dict)
    sentence_parsed = Signal(str, str, dict)

    # Emitted on any I/O error (source_id, message)
    error_occurred = Signal(str, str)

    # Emitted when a COM port status changes
    com_status_changed = Signal(str, object)

    # Emitted when a UDP endpoint status changes
    udp_status_changed = Signal(str, object)

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._running = False

        self._com = ComPortManager(
            on_data_received=self._on_com_received,
            on_error=self._on_error,
            on_status_change=self._on_com_status,
        )

        self._udp = UdpManager(
            on_data_received=self._on_udp_received,
            on_error=self._on_error,
            on_status_change=self._on_udp_status,
        )

        self._scheduler = Scheduler(dispatch=self._dispatch)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def start(self) -> None:
        """Open all configured connections and start the scheduler."""
        if self._running:
            return
        self._running = True
        self._open_connections()
        self._load_sentences()
        self._scheduler.start()

    def stop(self) -> None:
        """Stop scheduler and close all connections."""
        self._running = False
        self._scheduler.stop()
        self._com.close_all()
        self._udp.close_all()

    def reload_config(self, config: AppConfig) -> None:
        """Apply updated config without full restart."""
        self._config = config
        self._scheduler.clear()
        self._load_sentences()

    # -----------------------------------------------------------------------
    # Public helpers
    # -----------------------------------------------------------------------

    def available_com_ports(self) -> List[str]:
        return self._com.available_ports()

    def detect_com_baudrate(
        self,
        port_name: str,
        on_detected,
        on_failed,
    ) -> None:
        """Start async baud-rate detection on port_name."""
        self._com.detect_baudrate(port_name, on_detected, on_failed)

    def send_now(self, sentence_cfg: NmeaSentenceConfig) -> None:
        """Immediately send a sentence once (outside the scheduler)."""
        raw = self._build_raw(sentence_cfg)
        self._dispatch(sentence_cfg.outputs, raw)

    def add_sentence(self, cfg: NmeaSentenceConfig) -> None:
        """Register (or re-register) a sentence config with the scheduler."""
        scheduled = ScheduledSentence(
            sentence_key=cfg.scheduler_key,
            rate_hz=cfg.rate_hz,
            build_fn=lambda c=cfg: self._build_raw(c),
            output_ids=list(cfg.outputs),
            enabled=cfg.enabled,
        )
        self._scheduler.add_sentence(scheduled)

    def remove_sentence(self, cfg: NmeaSentenceConfig) -> None:
        """Unregister a sentence config from the scheduler."""
        self._scheduler.remove_sentence(cfg.scheduler_key)

    def set_sentence_enabled(self, cfg: NmeaSentenceConfig, enabled: bool) -> None:
        self._scheduler.set_enabled(cfg.scheduler_key, enabled)

    def update_sentence_rate(self, cfg: NmeaSentenceConfig, rate_hz: float) -> None:
        self._scheduler.update_rate(cfg.scheduler_key, rate_hz)

    def update_sentence_outputs(self, cfg: NmeaSentenceConfig, output_ids: List[str]) -> None:
        self._scheduler.update_outputs(cfg.scheduler_key, output_ids)

    # -----------------------------------------------------------------------
    # Internal: setup
    # -----------------------------------------------------------------------

    def _open_connections(self) -> None:
        for cp in self._config.com_ports:
            if cp.enabled:
                self._com.open(
                    port_name=cp.port,
                    baudrate=cp.baudrate,
                    bytesize=cp.bytesize,
                    parity=cp.parity,
                    stopbits=cp.stopbits,
                )

        for udp in self._config.udp_endpoints:
            if udp.enabled:
                if udp.send:
                    self._udp.open_send(udp.host, udp.port, udp.local_port)
                if udp.receive:
                    self._udp.open_receive(udp.host, udp.port)

    def _load_sentences(self) -> None:
        """Register all enabled sentences with the scheduler."""
        for s_cfg in self._config.sentences:
            if not s_cfg.enabled:
                continue
            self.add_sentence(s_cfg)

    # -----------------------------------------------------------------------
    # Internal: dispatch
    # -----------------------------------------------------------------------

    def _dispatch(self, output_ids: List[str], raw: str) -> None:
        """Send a raw sentence to all specified outputs."""
        for oid in output_ids:
            if oid.startswith("UDP:"):
                self._udp.send(oid, raw)
            else:
                self._com.send(oid, raw)
            # Signal to UI (thread-safe via Qt)
            self.sentence_sent.emit(oid, raw)

    def _build_raw(self, cfg: NmeaSentenceConfig) -> str:
        """Build a raw NMEA sentence string from a config object."""
        if cfg.is_custom:
            return build_custom_sentence(cfg.custom_template)
        field_values = list(cfg.fields.values())
        return build_sentence(cfg.talker_id, cfg.sentence_id, field_values)

    # -----------------------------------------------------------------------
    # Internal: callbacks from background threads (called on worker threads)
    # Use Qt signals to marshal back to main thread safely.
    # -----------------------------------------------------------------------

    def _on_com_received(self, port_name: str, raw: str) -> None:
        self.sentence_received.emit(port_name, raw)
        self._try_parse(port_name, raw)

    def _on_udp_received(self, endpoint_id: str, raw: str) -> None:
        self.sentence_received.emit(endpoint_id, raw)
        self._try_parse(endpoint_id, raw)

    def _on_error(self, source_id: str, msg: str) -> None:
        self.error_occurred.emit(source_id, msg)

    def _on_com_status(self, port_name: str, status: PortStatus) -> None:
        self.com_status_changed.emit(port_name, status)

    def _on_udp_status(self, endpoint_id: str, status: UdpStatus) -> None:
        self.udp_status_changed.emit(endpoint_id, status)

    def _try_parse(self, source_id: str, raw: str) -> None:
        """Attempt to parse a received sentence and emit parsed fields."""
        parsed = parse_sentence(raw)
        if parsed:
            fields_dict = parse_fields(parsed["sentence_id"], parsed["fields"])
            if fields_dict:
                self.sentence_parsed.emit(source_id, parsed["sentence_id"], fields_dict)
