"""
core/udp_manager.py
Manages multiple UDP endpoints for bidirectional NMEA I/O.
Uses Python's built-in socket module — zero external dependencies.
Each receive endpoint runs in its own background thread.
"""

import socket
import threading
import time
from typing import Callable, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class UdpStatus:
    endpoint_id: str
    host: str
    port: int
    active: bool = False
    error: str = ""
    packets_sent: int = 0
    packets_received: int = 0


class UdpManager:
    """
    Manages multiple simultaneous UDP send/receive endpoints.
    Endpoint IDs are strings like "UDP:192.168.1.100:10110".
    """

    def __init__(
        self,
        on_data_received: Callable[[str, str], None],   # (endpoint_id, raw_sentence)
        on_error: Callable[[str, str], None],            # (endpoint_id, error_msg)
        on_status_change: Callable[[str, UdpStatus], None],
    ):
        self._on_data_received = on_data_received
        self._on_error = on_error
        self._on_status_change = on_status_change

        # Send sockets keyed by endpoint_id
        self._send_sockets: Dict[str, socket.socket] = {}
        self._send_targets: Dict[str, Tuple[str, int]] = {}  # endpoint_id -> (host, port)

        # Receive sockets and threads keyed by endpoint_id
        self._recv_sockets: Dict[str, socket.socket] = {}
        self._recv_threads: Dict[str, threading.Thread] = {}
        self._recv_stop_events: Dict[str, threading.Event] = {}

        self._statuses: Dict[str, UdpStatus] = {}
        self._lock = threading.Lock()

    @staticmethod
    def make_endpoint_id(host: str, port: int) -> str:
        return f"UDP:{host}:{port}"

    def open_send(self, host: str, port: int, local_port: int = 0) -> str:
        """
        Open a UDP send socket to (host, port).

        local_port: if non-zero, the socket is bound to this local port so the
        OS-assigned ephemeral port is replaced by a fixed value.  Perle Serial
        Server devices learn the client source port from the first datagram they
        receive; fixing this port ensures they continue to route return traffic
        correctly across application restarts.

        Returns the endpoint_id.
        """
        endpoint_id = self.make_endpoint_id(host, port)
        with self._lock:
            if endpoint_id in self._send_sockets:
                return endpoint_id

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if local_port > 0:
                sock.bind(("0.0.0.0", local_port))
            with self._lock:
                self._send_sockets[endpoint_id] = sock
                self._send_targets[endpoint_id] = (host, port)

            status = UdpStatus(endpoint_id=endpoint_id, host=host, port=port, active=True)
            self._statuses[endpoint_id] = status
            self._on_status_change(endpoint_id, status)
        except Exception as e:
            self._on_error(endpoint_id, f"Failed to open send socket: {e}")

        return endpoint_id

    def open_receive(self, host: str, port: int) -> str:
        """
        Open a UDP receive socket bound to (host, port).
        Returns the endpoint_id.
        Binds to 0.0.0.0 to receive on all interfaces.
        """
        endpoint_id = self.make_endpoint_id(host, port)
        with self._lock:
            if endpoint_id in self._recv_sockets:
                return endpoint_id

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            # Bind to all interfaces so broadcast/multicast NMEA traffic is
            # received regardless of which network adapter delivers it.
            # The configured host is the send target, not the receive address.
            sock.bind(("0.0.0.0", port))

            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._recv_loop,
                args=(endpoint_id, sock, stop_event),
                daemon=True,
                name=f"UDP-Recv-{port}",
            )

            with self._lock:
                self._recv_sockets[endpoint_id] = sock
                self._recv_stop_events[endpoint_id] = stop_event
                self._recv_threads[endpoint_id] = thread

            if endpoint_id not in self._statuses:
                status = UdpStatus(endpoint_id=endpoint_id, host=host, port=port, active=True)
                self._statuses[endpoint_id] = status
                self._on_status_change(endpoint_id, status)
            else:
                self._statuses[endpoint_id].active = True

            thread.start()
        except Exception as e:
            self._on_error(endpoint_id, f"Failed to bind receive socket on port {port}: {e}")

        return endpoint_id

    def close(self, endpoint_id: str) -> None:
        """Close all sockets associated with an endpoint."""
        with self._lock:
            stop_event = self._recv_stop_events.pop(endpoint_id, None)
            recv_sock = self._recv_sockets.pop(endpoint_id, None)
            self._recv_threads.pop(endpoint_id, None)
            send_sock = self._send_sockets.pop(endpoint_id, None)
            self._send_targets.pop(endpoint_id, None)

        if stop_event:
            stop_event.set()
        for sock in filter(None, [recv_sock, send_sock]):
            try:
                sock.close()
            except Exception:
                pass

        if endpoint_id in self._statuses:
            self._statuses[endpoint_id].active = False
            self._on_status_change(endpoint_id, self._statuses[endpoint_id])

    def close_all(self) -> None:
        """Close all UDP endpoints."""
        for eid in list(self._send_sockets.keys()) + list(self._recv_sockets.keys()):
            self.close(eid)

    def send(self, endpoint_id: str, sentence: str) -> bool:
        """Send a raw NMEA sentence to a UDP endpoint."""
        with self._lock:
            sock = self._send_sockets.get(endpoint_id)
            target = self._send_targets.get(endpoint_id)

        if not sock or not target:
            return False

        try:
            data = sentence.encode("ascii", errors="replace")
            sock.sendto(data, target)
            if endpoint_id in self._statuses:
                self._statuses[endpoint_id].packets_sent += 1
            return True
        except Exception as e:
            self._on_error(endpoint_id, f"UDP send error [{endpoint_id}]: {e}")
            return False

    def send_to_all(self, sentence: str) -> None:
        """Broadcast a sentence to all open send sockets."""
        for eid in list(self._send_sockets.keys()):
            self.send(eid, sentence)

    def get_status(self, endpoint_id: str) -> Optional[UdpStatus]:
        return self._statuses.get(endpoint_id)

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _recv_loop(self, endpoint_id: str, sock: socket.socket,
                   stop_event: threading.Event) -> None:
        """Background thread: receive UDP packets and extract NMEA sentences."""
        buffer = ""
        while not stop_event.is_set():
            try:
                data, _ = sock.recvfrom(4096)
                text = data.decode("ascii", errors="replace")
                buffer += text

                # Extract complete sentences
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    raw = line.strip()
                    if raw.startswith("$") or raw.startswith("!"):
                        if endpoint_id in self._statuses:
                            self._statuses[endpoint_id].packets_received += 1
                        self._on_data_received(endpoint_id, raw)
            except socket.timeout:
                continue
            except Exception as e:
                if not stop_event.is_set():
                    self._on_error(endpoint_id, f"UDP receive error [{endpoint_id}]: {e}")
                    if endpoint_id in self._statuses:
                        self._statuses[endpoint_id].active = False
                    break
