"""Run the gateway reset protocol without blocking the GUI."""

import asyncio
import json
from urllib.parse import urlsplit

import websockets
from PySide6.QtCore import QThread, Signal


async def reset_matrix(uri, timeout=15.0):
    """Match sw_control reset, including Pico restart verification."""
    parsed = urlsplit(uri)
    if parsed.scheme not in ("ws", "wss") or not parsed.hostname:
        raise ValueError("Enter a valid switching matrix WebSocket address.")
    async with websockets.connect(
        uri, open_timeout=5.0, close_timeout=2.0, ping_interval=None,
    ) as websocket:
        await asyncio.wait_for(
            websocket.send(json.dumps({"gateway": "reset"})), timeout=timeout,
        )
        response = json.loads(await asyncio.wait_for(websocket.recv(), timeout=timeout))
    if not isinstance(response, dict) or (
        response.get("ok") != 1
        or response.get("event") != "reset"
        or response.get("restarted") != 1
    ):
        raise RuntimeError(f"Unexpected gateway reset response: {response}")
    return response


class MatrixResetWorker(QThread):
    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, uri, parent=None):
        super().__init__(parent)
        self.uri = uri

    def run(self):
        try:
            asyncio.run(reset_matrix(self.uri))
        except Exception as exc:
            self.failed.emit(str(exc) or type(exc).__name__)
        else:
            self.succeeded.emit()
