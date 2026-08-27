import unittest

import numpy as np

from lgad_ivcv.ivcv.CVMeasurement import CVMeasurement
from lgad_ivcv.ivcv.IVMeasurement import IVMeasurement


class FakeSMU:
    def __init__(self, fail_ramp=False):
        self.calls = []
        self.fail_ramp = fail_ramp

    def set_voltage_ramp(self, voltage):
        self.calls.append(("set_voltage_ramp", voltage))
        if self.fail_ramp:
            raise RuntimeError("ramp failed")

    def set_voltage(self, voltage):
        self.calls.append(("set_voltage", voltage))

    def set_output(self, state):
        self.calls.append(("set_output", state))


class FakePAU:
    def __init__(self):
        self.calls = []

    def set_voltage(self, voltage):
        self.calls.append(("set_voltage", voltage))

    def set_output(self, state):
        self.calls.append(("set_output", state))


class FakeLCR:
    def __init__(self, measurement_error=None):
        self.calls = []
        self.measurement_error = measurement_error

    def set_dc_voltage(self, voltage):
        self.calls.append(("set_dc_voltage", voltage))

    def set_output(self, state):
        self.calls.append(("set_output", state))

    def measure(self):
        if self.measurement_error is not None:
            raise self.measurement_error
        return 1e-12, 1e6


def fail_measurement(*_args, **_kwargs):
    raise RuntimeError("simulated measurement failure")


class MeasurementSafetyTest(unittest.TestCase):
    def test_stop_uses_fast_shutdown_without_forced_return_measurements(self):
        measurement = IVMeasurement()
        measurement.smu = FakeSMU()
        measurement.voltage_array = np.array([-100, -101])
        measured_points = []

        def stop_after_first_point(voltage, index, is_forced_return=False):
            measured_points.append((voltage, index, is_forced_return))
            measurement.event.set()

        measurement._update_measurement_array = stop_after_first_point

        measurement._measure()

        self.assertEqual(measured_points, [(-100, 0, False)])
        self.assertIn(("set_voltage_ramp", 0), measurement.smu.calls)
        self.assertEqual(measurement.smu.calls[-1], ("set_output", "off"))

    def test_iv_failure_sets_zero_and_turns_output_off(self):
        measurement = IVMeasurement()
        measurement.smu = FakeSMU()
        measurement.voltage_array = np.array([-10])
        measurement._update_measurement_array = fail_measurement

        with self.assertRaisesRegex(RuntimeError, "simulated measurement failure"):
            measurement._measure()

        self.assertIn(("set_voltage_ramp", 0), measurement.smu.calls)
        self.assertIn(("set_voltage", 0), measurement.smu.calls)
        self.assertEqual(measurement.smu.calls[-1], ("set_output", "off"))
        self.assertFalse(measurement.measurement_in_progress)

    def test_iv_shutdown_continues_when_voltage_ramp_fails(self):
        measurement = IVMeasurement()
        measurement.smu = FakeSMU(fail_ramp=True)

        measurement._ensure_output_off()

        self.assertIn(("set_voltage", 0), measurement.smu.calls)
        self.assertEqual(measurement.smu.calls[-1], ("set_output", "off"))

    def test_cv_failure_disables_both_bias_sources(self):
        measurement = CVMeasurement()
        measurement.pau = FakePAU()
        measurement.lcr = FakeLCR()
        measurement.voltage_array = np.array([-10])
        measurement._update_measurement_array = fail_measurement

        with self.assertRaisesRegex(RuntimeError, "simulated measurement failure"):
            measurement._measure()

        self.assertEqual(
            measurement.pau.calls,
            [("set_voltage", 0), ("set_output", "OFF")],
        )
        self.assertEqual(
            measurement.lcr.calls,
            [("set_dc_voltage", 0), ("set_output", "OFF")],
        )
        self.assertFalse(measurement.measurement_in_progress)

    def test_lcr_read_failure_is_bounded_and_turns_output_off(self):
        measurement = CVMeasurement()
        measurement.lcr = FakeLCR(RuntimeError("LCR unavailable"))
        measurement.voltage_array = np.array([-10])

        with self.assertRaisesRegex(RuntimeError, "failed after 10 attempts"):
            measurement._measure()

        self.assertEqual(
            measurement.lcr.calls[-2:],
            [("set_dc_voltage", 0), ("set_output", "OFF")],
        )


if __name__ == "__main__":
    unittest.main()
