import threading
import unittest
from unittest.mock import Mock, patch

from lgad_ivcv.ivcv.IVMeasurement import IVMeasurement
from lgad_ivcv.ivcv.iv_sw import IV_sw
from lgad_ivcv.util.thread import BaseThread


class FakeSwitchMatrix:
    def __init__(self):
        self.calls = []

    def off_all(self):
        self.calls.append(("off_all",))

    def on(self, channel):
        self.calls.append(("on", channel))

    def off(self, channel):
        self.calls.append(("off", channel))

    def pinstat_all(self):
        return [[0] * 16 for _ in range(16)]


class FakeMeasurement:
    def __init__(self):
        self.event = threading.Event()

    def set_measurement_time(self):
        pass


class IVGuiSupportTests(unittest.TestCase):
    def test_measurement_data_callback_receives_each_point(self):
        measurement = IVMeasurement()
        callback = Mock()
        measurement.set_data_callback(callback)
        measurement.smu = Mock()
        measurement.smu.read.return_value = "-1,-2e-6"
        measurement.pau = None
        measurement.voltage_array = [-1]

        measurement._update_measurement_array(-1, 0)

        callback.assert_called_once_with((-1, 0, -2e-6))

    def test_measurement_thread_failure_is_raised_by_joiner(self):
        def fail():
            raise RuntimeError("instrument failed")

        thread = BaseThread(target=fail)
        thread.start()

        with self.assertRaisesRegex(RuntimeError, "instrument failed"):
            thread.join_and_raise()

    def test_stop_request_prevents_starting_next_channel(self):
        runner = IV_sw.__new__(IV_sw)
        runner.iv = FakeMeasurement()
        runner.swm = FakeSwitchMatrix()
        runner.dryrun = True
        runner._stop_requested = threading.Event()
        started = []

        def stop_on_first_channel(channel, _index, _total):
            started.append(channel)
            runner.request_stop()

        with patch("builtins.print"):
            runner.measure_channel(
                [1, 2, 3],
                verbose=0,
                on_channel_start=stop_on_first_channel,
            )

        self.assertEqual(started, [1])
        self.assertEqual(runner.swm.calls, [("off_all",), ("off_all",)])


if __name__ == "__main__":
    unittest.main()
