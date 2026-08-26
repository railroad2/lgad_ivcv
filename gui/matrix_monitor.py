import threading
from urllib.parse import urlsplit, urlunsplit

from PySide6.QtCore import QObject, Signal, Slot

from swm_ctrl.websocket_client import WebSocketClientSync


def monitor_uri_from_control_uri(control_uri, monitor_port=8766):
    """Derive the public monitor URI from a switching-matrix control URI."""
    parsed = urlsplit(control_uri.strip())
    if parsed.scheme not in ("ws", "wss") or not parsed.hostname:
        raise ValueError("invalid WebSocket address")

    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"

    userinfo = ""
    if "@" in parsed.netloc:
        userinfo = parsed.netloc.rsplit("@", 1)[0] + "@"

    path = parsed.path.rstrip("/")
    if path in ("", "/control", "/monitor"):
        path = ""

    return urlunsplit(
        parsed._replace(
            netloc=f"{userinfo}{host}:{monitor_port}",
            path=path,
            fragment="",
        )
    )


class MatrixConnectionMonitor(QObject):
    """Continuously check the gateway monitor endpoint outside the GUI thread."""

    status_changed = Signal(str, str)
    finished = Signal()

    def __init__(
        self,
        control_uri,
        *,
        check_interval=5.0,
        retry_interval=2.0,
        timeout=2.0,
        parent=None,
    ):
        super().__init__(parent)
        self._control_uri = control_uri
        self._check_interval = check_interval
        self._retry_interval = retry_interval
        self._timeout = timeout
        self._stop_event = threading.Event()
        self._address_changed = threading.Event()
        self._address_lock = threading.Lock()
        self._last_status = None
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self.run,
            name="switching-matrix-monitor",
            daemon=True,
        )
        self._thread.start()

    def set_control_uri(self, control_uri):
        with self._address_lock:
            self._control_uri = control_uri
        self._address_changed.set()

    def request_stop(self):
        self._stop_event.set()
        self._address_changed.set()

    def stop(self, timeout=5.0):
        self.request_stop()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        self._thread = None

    def _current_control_uri(self):
        with self._address_lock:
            return self._control_uri

    def _emit_status(self, control_uri, status):
        current = (control_uri, status)
        if current != self._last_status:
            self._last_status = current
            self.status_changed.emit(control_uri, status)

    def _wait(self, timeout):
        changed = self._address_changed.wait(timeout)
        self._address_changed.clear()
        return changed or self._stop_event.is_set()

    @Slot()
    def run(self):
        try:
            while not self._stop_event.is_set():
                control_uri = self._current_control_uri()
                self._emit_status(control_uri, "Checking...")
                client = None
                try:
                    monitor_uri = monitor_uri_from_control_uri(control_uri)
                    client = WebSocketClientSync(
                        monitor_uri,
                        timeout=self._timeout,
                        connect_timeout=self._timeout,
                    )
                    client.connect()
                    if self._stop_event.is_set():
                        break
                    client.gateway_ping()
                    if self._address_changed.is_set():
                        continue
                    self._emit_status(control_uri, "Connected")

                    while not self._wait(self._check_interval):
                        client.gateway_ping()
                except Exception:
                    if not self._stop_event.is_set():
                        self._emit_status(control_uri, "Disconnected")
                        self._wait(self._retry_interval)
                finally:
                    if client is not None:
                        client.close()
        finally:
            self.finished.emit()
