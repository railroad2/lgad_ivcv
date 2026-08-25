import json
import time

import serial

try:
    from .protocol import normalize_command, validate_response
except ImportError:
    from protocol import normalize_command, validate_response


class USBComm:
    """Synchronous JSON-line transport over USB CDC serial."""

    def __init__(self, port=None, baudrate=115200, timeout=5.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self, port=None):
        if port is not None:
            self.port = port
        if self.port is None:
            raise ValueError("USB serial port is not set")
        if self.is_connected():
            return
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

    def close(self):
        if self.ser is not None:
            try:
                self.ser.close()
            finally:
                self.ser = None

    def is_connected(self):
        return self.ser is not None and getattr(self.ser, "is_open", True)

    @staticmethod
    def _write_command(ser, command):
        payload = json.dumps(command, separators=(",", ":")) + "\r\n"
        ser.write(payload.encode("utf-8"))
        ser.flush()

    def _read_response(self, ser, expected_cmd):
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            try:
                response = json.loads(raw.decode("utf-8").strip())
            except (UnicodeError, ValueError):
                continue
            if not isinstance(response, dict):
                continue
            if response.get("ok") == 0 or response.get("cmd") == expected_cmd:
                return validate_response(response, expected_cmd)
            # Ignore startup messages such as {"ok":1,"event":"READY"}.

        raise TimeoutError(
            f"No {expected_cmd} JSON response received from {self.port}"
        )

    def _exchange(self, ser, data):
        command = normalize_command(data)
        self._write_command(ser, command)
        return self._read_response(ser, command["cmd"])

    def send_data(self, data):
        if not self.is_connected():
            self.connect()
        return self._exchange(self.ser, data)

    def send_data_once(self, data):
        if self.is_connected():
            raise RuntimeError("USB serial port is already connected")
        if self.port is None:
            raise ValueError("USB serial port is not set")

        ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        try:
            return self._exchange(ser, data)
        finally:
            ser.close()

    def on(self, pins):
        return self.send_data({"cmd": "ON", "pins": pins})

    def off(self, pins):
        return self.send_data({"cmd": "OFF", "pins": pins})

    def alloff(self):
        return self.send_data({"cmd": "ALLOFF"})

    def pinstat(self, which="ALL"):
        return self.send_data({"cmd": "PINSTAT", "which": which})
