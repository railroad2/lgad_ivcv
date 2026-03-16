import sys
import asyncio
import json
from typing import Optional

import websockets


class GateComm:
    debug = False

    def __init__(self, uri: Optional[str] = None):
        self.uri = self._normalize_uri(uri or "ws://localhost:8765")

    def _normalize_uri(self, uri: str) -> str:
        uri = uri.rstrip("/")

        if uri.endswith("/control"):
            return uri

        if uri.endswith("/monitor"):
            return uri[:-8] + "/control"

        return uri + "/control"

    def connect(self):
        # Kept for interface compatibility with SWmat.
        return self

    def close(self):
        # Kept for interface compatibility with SWmat.
        return None

    def send_data(self, data):
        if not isinstance(data, str):
            raise TypeError("GateComm.send_data expects a command string")

        payload, expect_reply = self._parse_command(data)

        response = asyncio.run(
            self.send_data_once(payload, timeout=5, reply=expect_reply)
        )

        if response is None:
            return None

        responsed = json.loads(response)
        return self._convert_response(payload, responsed)

    def _parse_command(self, data: str):
        parts = data.strip().split()
        if not parts:
            raise ValueError("Empty command")

        cmd = parts[0].upper()

        if cmd == "ON":
            if len(parts) < 2:
                raise ValueError("ON requires at least one pin")
            payload = {"cmd": "ON", "pins": [self._parse_pin_token(x) for x in parts[1:]]}
            return payload, True

        if cmd == "OFF":
            if len(parts) < 2:
                raise ValueError("OFF requires at least one pin or ALL")
            if len(parts) == 2 and parts[1].upper() == "ALL":
                payload = {"cmd": "ALLOFF"}
            else:
                payload = {"cmd": "OFF", "pins": [self._parse_pin_token(x) for x in parts[1:]]}
            return payload, True

        if cmd == "ALLOFF":
            payload = {"cmd": "ALLOFF"}
            return payload, True

        if cmd == "PINSTAT":
            which = "ALL"
            if len(parts) >= 2:
                which = self._parse_which(parts[1])
            payload = {"cmd": "PINSTAT", "which": which}
            return payload, True

        if cmd == "PCFSTAT":
            which = "ALL"
            if len(parts) >= 2:
                which = self._parse_which(parts[1])
            payload = {"cmd": "PCFSTAT", "which": which}
            return payload, True

        if cmd == "PING":
            payload = {"cmd": "PING"}
            return payload, True

        if cmd == "ROUTE":
            if len(parts) != 2:
                raise ValueError("ROUTE requires exactly one target")
            payload = {"cmd": "ROUTE", "pins": [self._parse_pin_token(parts[1])]}
            return payload, True

        raise ValueError(f"Invalid command: {data}")

    def _parse_pin_token(self, token: str):
        token = token.strip()

        # For now keep compatibility with numeric channel usage in SWmat.
        # Matrix labels such as A00 can be added later if needed.
        try:
            pin = int(token)
        except ValueError as exc:
            raise ValueError(f"Invalid pin token: {token}") from exc

        if not (0 <= pin <= 255):
            raise ValueError(f"Pin out of range: {pin}")

        return pin

    def _parse_which(self, token: str):
        token = token.strip()
        if token.upper() == "ALL":
            return "ALL"

        try:
            which = int(token)
        except ValueError as exc:
            raise ValueError(f"Invalid which token: {token}") from exc

        return which

    async def send_data_once(self, data, timeout=5, reply=True):
        if isinstance(data, dict):
            text = json.dumps(data)
        else:
            text = str(data)

        if self.debug:
            print(text)

        async with websockets.connect(
            self.uri,
            ping_interval=None,
            open_timeout=timeout,
        ) as ws:
            try:
                # Receive gateway hello first.
                hello = await asyncio.wait_for(ws.recv(), timeout=timeout)
                if self.debug:
                    print(hello)

                await asyncio.wait_for(ws.send(text), timeout=timeout)

                if reply:
                    response = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    return response

                return None

            except asyncio.TimeoutError:
                return json.dumps({
                    "ok": 0,
                    "error": "Timeout: no response from the websocket gateway"
                })

    def _convert_response(self, request_payload, response_payload):
        cmd = str(request_payload.get("cmd", "")).upper()

        if "ok" in response_payload and response_payload.get("ok") != 1:
            return json.dumps(response_payload)

        if cmd == "PINSTAT":
            pins = response_payload.get("pins")
            if isinstance(pins, list):
                return self._conv_pinstat(pins)
            return json.dumps(response_payload)

        if cmd == "PCFSTAT":
            present = response_payload.get("present")
            if isinstance(present, list):
                return " ".join(str(int(v)) for v in present)
            if isinstance(present, int):
                return str(int(present))
            return json.dumps(response_payload)

        return json.dumps(response_payload)

    def _conv_pinstat(self, datain):
        pinstat = [str(int(i)) for i in datain]
        return " ".join(pinstat)
