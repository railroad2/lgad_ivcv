import asyncio
import json

import websockets


try:
    from .protocol import normalize_command, validate_response
except ImportError:
    from protocol import normalize_command, validate_response


class WSComm:
    """Synchronous facade over a one-request WebSocket JSON transport."""

    debug = False

    def __init__(self, uri=None, timeout=5.0):
        self.uri = uri
        self.timeout = timeout

    def connect(self):
        # Connections are opened per request by send_data_once().
        return None

    def close(self):
        return None

    def is_connected(self):
        return self.uri is not None

    def send_data(self, data):
        return asyncio.run(self.send_data_once(data))

    async def send_data_once(self, data):
        command = normalize_command(data)
        text = json.dumps(command, separators=(",", ":"))

        if self.debug:
            print(text)

        async with websockets.connect(
            self.uri,
            ping_interval=None,
            open_timeout=self.timeout,
        ) as ws:
            await asyncio.wait_for(ws.send(text), timeout=self.timeout)
            message = await asyncio.wait_for(ws.recv(), timeout=self.timeout)

        try:
            response = json.loads(message)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"WebSocket returned invalid JSON: {message!r}"
            ) from exc

        return validate_response(response, command["cmd"])

    def on(self, pins):
        return self.send_data({"cmd": "ON", "pins": pins})

    def off(self, pins):
        return self.send_data({"cmd": "OFF", "pins": pins})

    def alloff(self):
        return self.send_data({"cmd": "ALLOFF"})

    def pinstat(self, which="ALL"):
        return self.send_data({"cmd": "PINSTAT", "which": which})
