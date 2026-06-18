"""
core/scheduler.py
Fires NMEA sentence transmission at per-sentence configurable rates.
Uses a single background timer thread with fine-grained scheduling.
"""

import threading
import time
from typing import Callable, Dict, List
from dataclasses import dataclass, field


@dataclass
class ScheduledSentence:
    sentence_key: str          # Unique key e.g. "GP-GGA"
    rate_hz: float             # Transmit rate in Hz (0 = disabled)
    build_fn: Callable[[], str]  # Returns the fully built NMEA string
    output_ids: List[str] = field(default_factory=list)  # Target output IDs
    enabled: bool = True

    # Internal scheduling state
    _next_fire: float = field(default_factory=time.monotonic, init=False)


class Scheduler:
    """
    High-resolution NMEA sentence scheduler.
    Each sentence has an independent rate in Hz.
    The dispatch callback receives (output_ids, raw_sentence).
    """

    TICK_INTERVAL = 0.005  # 5ms resolution — supports up to 200Hz

    def __init__(self, dispatch: Callable[[List[str], str], None]):
        """
        dispatch(output_ids, raw_sentence):
            Called on the scheduler thread when a sentence is due.
            Use Qt signals to forward to I/O managers safely.
        """
        self._dispatch = dispatch
        self._sentences: Dict[str, ScheduledSentence] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="NMEAScheduler",
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def add_sentence(self, sentence: ScheduledSentence) -> None:
        """Add or replace a scheduled sentence."""
        sentence._next_fire = time.monotonic()
        with self._lock:
            self._sentences[sentence.sentence_key] = sentence

    def remove_sentence(self, sentence_key: str) -> None:
        """Remove a sentence from the schedule."""
        with self._lock:
            self._sentences.pop(sentence_key, None)

    def update_rate(self, sentence_key: str, rate_hz: float) -> None:
        """Update the rate for an existing sentence."""
        with self._lock:
            s = self._sentences.get(sentence_key)
            if s:
                s.rate_hz = rate_hz

    def update_outputs(self, sentence_key: str, output_ids: List[str]) -> None:
        """Update the output routing for an existing sentence."""
        with self._lock:
            s = self._sentences.get(sentence_key)
            if s:
                s.output_ids = output_ids

    def set_enabled(self, sentence_key: str, enabled: bool) -> None:
        """Enable or disable a scheduled sentence."""
        with self._lock:
            s = self._sentences.get(sentence_key)
            if s:
                s.enabled = enabled

    def clear(self) -> None:
        """Remove all scheduled sentences."""
        with self._lock:
            self._sentences.clear()

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _run(self) -> None:
        while self._running:
            with self._lock:
                sentences = list(self._sentences.values())

            for s in sentences:
                if not s.enabled or s.rate_hz <= 0:
                    continue
                now = time.monotonic()
                if now >= s._next_fire:
                    interval = 1.0 / s.rate_hz
                    # Advance by one interval from the scheduled time to prevent
                    # drift; clamp to now so a paused sentence doesn't burst.
                    s._next_fire = max(s._next_fire + interval, now)
                    try:
                        raw = s.build_fn()
                        self._dispatch(s.output_ids, raw)
                    except Exception as e:
                        print(f"[Scheduler] Error building {s.sentence_key}: {e}")

            time.sleep(self.TICK_INTERVAL)
