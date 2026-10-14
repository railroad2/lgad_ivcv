import unittest
from unittest.mock import patch

from lgad_ivcv.gui.matrix_monitor import (
    MatrixConnectionMonitor,
    monitor_uri_from_control_uri,
)


class MatrixMonitorUriTests(unittest.TestCase):
    def test_control_port_is_replaced_with_monitor_port(self):
        self.assertEqual(
            monitor_uri_from_control_uri("ws://swm:8765"),
            "ws://swm:8766",
        )

    def test_legacy_endpoint_suffix_is_removed(self):
        self.assertEqual(
            monitor_uri_from_control_uri("ws://swm:8765/control"),
            "ws://swm:8766",
        )

    def test_ipv6_and_credentials_are_preserved(self):
        self.assertEqual(
            monitor_uri_from_control_uri("wss://user:pass@[::1]:8765"),
            "wss://user:pass@[::1]:8766",
        )

    def test_invalid_address_is_rejected(self):
        with self.assertRaises(ValueError):
            monitor_uri_from_control_uri("swm:8765")

    def test_monitor_reports_successful_gateway_ping(self):
        monitor = MatrixConnectionMonitor(
            "ws://swm:8765",
            check_interval=0.001,
        )
        statuses = []
        pico_statuses = []
        monitor.status_changed.connect(
            lambda address, status: statuses.append((address, status))
        )
        monitor.pico_status_changed.connect(
            lambda address, status: pico_statuses.append((address, status))
        )

        class FakeClient:
            def __init__(self, uri, **kwargs):
                self.uri = uri
                self.ping_count = 0

            def connect(self):
                return None

            def gateway_ping(self):
                self.ping_count += 1

            def ping(self):
                monitor.request_stop()

            def close(self):
                return None

        with patch(
            "lgad_ivcv.gui.matrix_monitor.WebSocketClientSync",
            FakeClient,
        ):
            monitor.run()

        self.assertEqual(
            statuses,
            [
                ("ws://swm:8765", "Checking..."),
                ("ws://swm:8765", "Connected"),
            ],
        )
        self.assertEqual(
            pico_statuses,
            [
                ("ws://swm:8765", "Checking..."),
                ("ws://swm:8765", "Connected"),
            ],
        )

    def test_monitor_distinguishes_gateway_from_disconnected_pico(self):
        monitor = MatrixConnectionMonitor("ws://swm:8765")
        gateway_statuses = []
        pico_statuses = []
        monitor.status_changed.connect(
            lambda _address, status: gateway_statuses.append(status)
        )
        monitor.pico_status_changed.connect(
            lambda _address, status: pico_statuses.append(status)
        )

        class FakeClient:
            def __init__(self, uri, **kwargs):
                self.uri = uri

            def connect(self):
                return None

            def gateway_ping(self):
                return None

            def ping(self):
                monitor.request_stop()
                raise RuntimeError("Pico did not respond")

            def close(self):
                return None

        with patch(
            "lgad_ivcv.gui.matrix_monitor.WebSocketClientSync",
            FakeClient,
        ):
            monitor.run()

        self.assertEqual(gateway_statuses, ["Checking...", "Connected"])
        self.assertEqual(pico_statuses, ["Checking...", "Disconnected"])


if __name__ == "__main__":
    unittest.main()
