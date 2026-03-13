import json
from typing import Optional

try:
    from daq_client.daq_client_sync import DAQClientSync
except ModuleNotFoundError:
    from daq_client_sync import DAQClientSync


class GateComm:
    debug = False

    def __init__(self, uri: Optional[str] = None, timeout: float = 5.0, connect_timeout: float = 5.0):
        self.uri = self._normalize_uri(uri or "ws://localhost:8765")
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.client: Optional[DAQClientSync] = None

    def _normalize_uri(self, uri: str) -> str:
        uri = uri.rstrip("/")

        if uri.endswith("/control"):
            return uri

        if uri.endswith("/monitor"):
            return uri[:-8] + "/control"

        return uri + "/control"

    def connect(self):
        if self.client is None:
            self.client = DAQClientSync(
                self.uri,
                timeout=self.timeout,
                connect_timeout=self.connect_timeout,
            )
            self.client.connect()
        return self.client

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None

    def _require_client(self) -> DAQClientSync:
        if self.client is None:
            return self.connect()
        return self.client

    def _conv_pinstat(self, datain):
        pins = [str(int(i)) for i in datain]
        return " ".join(pins)

    def send_data(self, data):
        client = self._require_client()

        if not isinstance(data, str):
            raise TypeError("GateComm.send_data expects a command string")

        parts = data.strip().split()
        if len(parts) == 0:
            raise ValueError("Empty command")

        cmd = parts[0].upper()

        if self.debug:
            print(f"[GateComm] {data}")

        if cmd == "ON":
            if len(parts) < 2:
                raise ValueError("ON requires at least one pin")
            resp = client.on(*parts[1:])
            return json.dumps(resp)

        elif cmd == "OFF":
            if len(parts) < 2:
                raise ValueError("OFF requires at least one pin or ALL")
            if len(parts) == 2 and parts[1].upper() == "ALL":
                resp = client.alloff()
            else:
                resp = client.off(*parts[1:])
            return json.dumps(resp)

        elif cmd == "ALLOFF":
            resp = client.alloff()
            return json.dumps(resp)

        elif cmd == "PINSTAT":
            which = "ALL"
            if len(parts) >= 2:
                which = parts[1]

            resp = client.pinstat(which)

            if "pins" in resp:
                return self._conv_pinstat(resp["pins"])

            return json.dumps(resp)

        elif cmd == "PCFSTAT":
            which = "ALL"
            if len(parts) >= 2:
                which = parts[1]

            resp = client.pcfstat(which)
            return json.dumps(resp)

        elif cmd == "PING":
            resp = client.ping()
            return json.dumps(resp)

        elif cmd == "ROUTE":
            if len(parts) < 2:
                raise ValueError("ROUTE requires at least one target")
            resp = client.route(*parts[1:])
            return json.dumps(resp)

        else:
            raise ValueError(f"Invalid command: {data}")