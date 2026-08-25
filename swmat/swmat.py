import time
import numpy as np
from urllib.parse import urlparse

from swm_ctrl.websocket_client import parse_pin_tokens, row_col_to_pin

from . import wscomm
from . import usbcomm
from . import gatecomm


class SWmat:
    """Common switching-matrix facade for USB and WebSocket transports."""

    def __init__(self, port=None, delay=0.5):
        self.comm = None
        self.port = None
        self.delay = delay

        if port is not None:
            self.open(port)

    def open(self, port):
        if port is None:
            raise ValueError("port is None")

        self.close()
        self.port = port

        if "ttyACM" in port:
            self.comm = usbcomm.USBComm(port)
        elif port.startswith("ws://") or port.startswith("wss://"):
            if urlparse(port).port == 8765:
                self.comm = gatecomm.GateComm(port)
                self.comm.connect()
            else:
                self.comm = wscomm.WSComm(port)
        else:
            raise ValueError(f"Invalid port: {port}")

        return self

    def close(self):
        if self.comm is not None:
            try:
                self.comm.close()
            finally:
                self.comm = None

    def _require_comm(self):
        if self.comm is None:
            raise RuntimeError("SWmat is not open")
        return self.comm

    def _execute(self, method, *args):
        response = getattr(self._require_comm(), method)(*args)
        if response is not None:
            print(response)
        time.sleep(self.delay)
        return response

    @staticmethod
    def _pins(pins, col=None):
        # Preserve the existing on(row, col)/off(row, col) API.
        if col is not None:
            return [row_col_to_pin(int(pins), int(col))]

        tokens = (pins,) if isinstance(pins, (str, int)) else tuple(pins)
        return parse_pin_tokens(tokens)

    @staticmethod
    def _row_pins(row):
        if isinstance(row, int):
            if not 0 <= row <= 15:
                raise ValueError(f"row out of range: {row}")
            row = chr(ord("A") + row)
        return parse_pin_tokens(("row", str(row).strip().upper()))

    @staticmethod
    def _col_pins(col):
        return parse_pin_tokens(("col", str(col).strip()))

    def pinstat_all(self):
        response = self._require_comm().pinstat("ALL")
        pins = response.get("pins")

        if not isinstance(pins, (list, tuple)) or len(pins) != 256:
            raise ValueError("PINSTAT ALL must return exactly 256 pin states")

        return np.array([int(value) for value in pins]).reshape(16, 16)

    def on(self, pins, col=None):
        return self._execute("on", self._pins(pins, col))

    def off(self, pins, col=None):
        return self._execute("off", self._pins(pins, col))

    def on_row(self, row):
        return self._execute("on", self._row_pins(row))

    def off_row(self, row):
        return self._execute("off", self._row_pins(row))

    def on_col(self, col):
        return self._execute("on", self._col_pins(col))

    def off_col(self, col):
        return self._execute("off", self._col_pins(col))

    def off_all(self):
        return self._execute("alloff")
