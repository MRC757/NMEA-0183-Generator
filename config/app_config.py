"""
config/app_config.py
Handles persistent application configuration saved to a JSON file.
All user settings (ports, sentences, rates, theme) are stored here.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict


def _default_config_path() -> str:
    config_dir = Path.home() / ".nmea_tool"
    config_dir.mkdir(exist_ok=True)
    return str(config_dir / "nmea_tool_config.json")


CONFIG_FILE = _default_config_path()


@dataclass
class ComPortConfig:
    port: str = "COM1"
    baudrate: int = 4800
    bytesize: int = 8
    parity: str = "N"       # N, E, O, M, S
    stopbits: float = 1.0
    enabled: bool = False
    label: str = ""         # User-friendly label


@dataclass
class UdpEndpointConfig:
    host: str = "127.0.0.1"
    port: int = 10110        # NMEA default UDP port (remote)
    local_port: int = 0      # Local source port for outgoing packets (0 = OS-assigned)
    enabled: bool = False
    send: bool = True
    receive: bool = True
    label: str = ""


@dataclass
class NmeaSentenceConfig:
    sentence_id: str = ""        # e.g. "GGA", "RMC", or custom
    talker_id: str = "GP"        # e.g. "GP", "GN", "II"
    enabled: bool = False
    rate_hz: float = 1.0         # Transmit rate in Hz
    fields: Dict[str, str] = field(default_factory=dict)  # Field name -> value
    outputs: List[str] = field(default_factory=list)       # Output IDs to route to
    is_custom: bool = False       # True = user-defined non-standard sentence
    custom_template: str = ""     # Raw template string for custom sentences

    @property
    def scheduler_key(self) -> str:
        """Unique runtime key for this config instance in the scheduler."""
        return f"{self.talker_id}-{self.sentence_id}-{id(self)}"


@dataclass
class MonitorFilterConfig:
    show_sent: bool = True
    show_received: bool = True
    show_parsed: bool = False
    show_errors: bool = True
    max_lines: int = 500


@dataclass
class AppConfig:
    theme: str = "light"          # "light" or "dark"
    com_ports: List[ComPortConfig] = field(default_factory=list)
    udp_endpoints: List[UdpEndpointConfig] = field(default_factory=list)
    sentences: List[NmeaSentenceConfig] = field(default_factory=list)
    monitor: MonitorFilterConfig = field(default_factory=MonitorFilterConfig)
    window_width: int = 1200
    window_height: int = 800
    window_x: int = 100
    window_y: int = 100

    @staticmethod
    def load(path: str = CONFIG_FILE) -> "AppConfig":
        """Load config from JSON file, or return defaults if not found."""
        if not os.path.exists(path):
            return AppConfig()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig._from_dict(data)
        except Exception as e:
            print(f"[Config] Failed to load config: {e}. Using defaults.")
            return AppConfig()

    def save(self, path: str = CONFIG_FILE) -> None:
        """Save current config to JSON file."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._to_dict(), f, indent=2)
        except Exception as e:
            print(f"[Config] Failed to save config: {e}")

    def _to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def _from_dict(data: dict) -> "AppConfig":
        config = AppConfig()
        config.theme = data.get("theme", "light")
        config.window_width = data.get("window_width", 1200)
        config.window_height = data.get("window_height", 800)
        config.window_x = data.get("window_x", 100)
        config.window_y = data.get("window_y", 100)

        config.com_ports = [
            ComPortConfig(**p) for p in data.get("com_ports", [])
        ]
        config.udp_endpoints = [
            UdpEndpointConfig(**u) for u in data.get("udp_endpoints", [])
        ]
        config.sentences = [
            NmeaSentenceConfig(**s) for s in data.get("sentences", [])
        ]
        mon = data.get("monitor", {})
        config.monitor = MonitorFilterConfig(**mon) if mon else MonitorFilterConfig()

        return config
