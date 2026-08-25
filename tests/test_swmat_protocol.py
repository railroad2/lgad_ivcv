import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from swmat import usbtools, wstools
from swmat.protocol import (
    SwitchProtocolError,
    col_pins,
    normalize_command,
    row_pins,
)
from swmat.swmat import SWmat
from swmat.usbcomm import USBComm
from swmat.wscomm import WSComm


class FakeSerial:
    def __init__(self, responses):
        self.responses = list(responses)
        self.written = b""
        self.closed = False
        self.is_open = True

    def write(self, data):
        self.written += data

    def flush(self):
        pass

    def readline(self):
        return self.responses.pop(0) if self.responses else b""

    def close(self):
        self.closed = True
        self.is_open = False


class FakeWebSocket:
    def __init__(self, response):
        self.response = json.dumps(response)
        self.sent = None

    async def send(self, data):
        self.sent = data

    async def recv(self):
        return self.response


class FakeWebSocketContext:
    def __init__(self, ws):
        self.ws = ws

    async def __aenter__(self):
        return self.ws

    async def __aexit__(self, exc_type, exc, tb):
        pass


class ProtocolTests(unittest.TestCase):
    def test_normalizes_legacy_and_json_commands(self):
        self.assertEqual(
            normalize_command("ON 3 1 2"),
            {"cmd": "ON", "pins": [1, 2, 3]},
        )
        self.assertEqual(normalize_command("OFF all"), {"cmd": "ALLOFF"})
        self.assertEqual(
            normalize_command('{"cmd":"pinstat","which":"all"}'),
            {"cmd": "PINSTAT", "which": "ALL"},
        )

    def test_expands_rows_and_columns_in_one_shared_place(self):
        self.assertEqual(row_pins(1), list(range(16, 32)))
        self.assertEqual(row_pins("P"), list(range(240, 256)))
        self.assertEqual(col_pins(3), list(range(3, 256, 16)))

    def test_usb_uses_common_json_and_skips_ready_message(self):
        fake = FakeSerial([
            b'{"ok":1,"event":"READY"}\r\n',
            b'{"ok":1,"cmd":"ON","results":[]}\r\n',
        ])
        comm = USBComm(port="test", timeout=0.1)

        with patch("swmat.usbcomm.serial.Serial", return_value=fake):
            response = comm.send_data_once({"cmd": "ON", "pins": [2, 1]})

        self.assertEqual(response["cmd"], "ON")
        self.assertEqual(
            json.loads(fake.written.decode()),
            {"cmd": "ON", "pins": [1, 2]},
        )
        self.assertTrue(fake.closed)

    def test_usb_rejects_controller_error(self):
        fake = FakeSerial([b'{"ok":0,"error":"hardware failure"}\n'])
        comm = USBComm(port="test", timeout=0.1)

        with patch("swmat.usbcomm.serial.Serial", return_value=fake):
            with self.assertRaises(SwitchProtocolError):
                comm.send_data_once({"cmd": "ALLOFF"})


class AsyncProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_websocket_uses_same_json_format(self):
        ws = FakeWebSocket({"ok": 1, "cmd": "OFF", "results": []})
        context = FakeWebSocketContext(ws)

        with patch("swmat.wscomm.websockets.connect", return_value=context):
            response = await WSComm("ws://test").send_data_once(
                {"cmd": "OFF", "pins": [17, 16]}
            )

        self.assertEqual(response["cmd"], "OFF")
        self.assertEqual(
            json.loads(ws.sent),
            {"cmd": "OFF", "pins": [16, 17]},
        )

    async def test_ws_row_is_sent_as_one_command(self):
        response = {"ok": 1, "cmd": "ON", "results": []}
        with patch.object(
            wstools,
            "send_data_once",
            new=AsyncMock(return_value=response),
        ) as send:
            result = await wstools.on_row("B")

        send.assert_awaited_once_with(
            {"cmd": "ON", "pins": list(range(16, 32))}
        )
        self.assertIs(result, response)


class ToolTests(unittest.TestCase):
    def test_usb_column_is_sent_as_one_command(self):
        response = {"ok": 1, "cmd": "OFF", "results": []}
        with patch.object(
            usbtools,
            "_send_json_command",
            return_value=response,
        ) as send:
            result = usbtools.off_col(3, port="test")

        send.assert_called_once_with(
            {"cmd": "OFF", "pins": list(range(3, 256, 16))},
            port="test",
        )
        self.assertIs(result, response)


class FakeComm:
    def __init__(self):
        self.calls = []

    def on(self, pins):
        self.calls.append(("on", pins))
        return {"ok": 1, "cmd": "ON", "results": []}

    def off(self, pins):
        self.calls.append(("off", pins))
        return {"ok": 1, "cmd": "OFF", "results": []}

    def alloff(self):
        self.calls.append(("alloff",))
        return {"ok": 1, "cmd": "ALLOFF"}

    def pinstat(self, which):
        self.calls.append(("pinstat", which))
        return {"ok": 1, "cmd": "PINSTAT", "pins": [0] * 256}


class SWmatTests(unittest.TestCase):
    def setUp(self):
        self.swm = SWmat(delay=0)
        self.swm.comm = FakeComm()

    def test_preserves_row_col_call_and_accepts_pin_lists(self):
        with patch("builtins.print"):
            self.swm.on(1, 2)
            self.swm.off([7, 3])

        self.assertEqual(
            self.swm.comm.calls,
            [("on", [18]), ("off", [3, 7])],
        )

    def test_row_column_and_alloff_use_common_methods(self):
        with patch("builtins.print"):
            self.swm.on_row(1)
            self.swm.off_col(3)
            self.swm.off_all()

        self.assertEqual(
            self.swm.comm.calls,
            [
                ("on", list(range(16, 32))),
                ("off", list(range(3, 256, 16))),
                ("alloff",),
            ],
        )

    def test_pinstat_all_keeps_matrix_result(self):
        result = self.swm.pinstat_all()

        self.assertEqual(result.shape, (16, 16))
        self.assertEqual(self.swm.comm.calls, [("pinstat", "ALL")])


if __name__ == "__main__":
    unittest.main()
