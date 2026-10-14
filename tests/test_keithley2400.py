import unittest

from lgad_ivcv.inst.Keithley2400 import Keithley2400


class FakeVisaInstrument:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.queries = []
        self.writes = []

    def query(self, command):
        self.queries.append(command)
        return self.responses.get(command, "0")

    def write(self, command):
        self.writes.append(command)


class Keithley2400Tests(unittest.TestCase):
    def make_driver(self, responses=None):
        driver = Keithley2400()
        driver._inst = FakeVisaInstrument(responses)
        driver.set_delay(0)
        return driver

    def test_voltage_ramp_uses_negative_steps_for_negative_target(self):
        driver = self.make_driver({":SOUR:VOLT:LEV?": "0\r"})

        driver.set_voltage_ramp(-3, step=1)

        self.assertEqual(
            driver._inst.writes,
            [
                ":SOUR:VOLT:LEV -1.0",
                ":SOUR:VOLT:LEV -2.0",
                ":SOUR:VOLT:LEV -3",
            ],
        )

    def test_voltage_ramp_rejects_nonpositive_step(self):
        driver = self.make_driver()

        with self.assertRaisesRegex(ValueError, "greater than zero"):
            driver.set_voltage_ramp(-3, step=0)

    def test_model_2400_initialization_uses_200_volt_range(self):
        driver = self.make_driver()
        driver.found_idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2400"

        driver.initialize()

        self.assertIn(":SOUR:VOLT:RANG 200", driver._inst.writes)
        self.assertNotIn(":SOUR:VOLT:RANG 1000", driver._inst.writes)

    def test_model_2400_sweep_rejects_more_than_200_volts(self):
        driver = self.make_driver()
        driver.found_idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2400"

        with self.assertRaisesRegex(ValueError, "200 V limit"):
            driver.configure_voltage_sweep([0, -201])

        self.assertEqual(driver._inst.writes, [])

    def test_model_2410_sweep_uses_1000_volt_nominal_range(self):
        driver = self.make_driver()
        driver.found_idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2410"

        selected_range = driver.configure_voltage_sweep([0, -250, -1100])

        self.assertEqual(selected_range, 1000)
        self.assertEqual(driver._inst.writes, [":SOUR:VOLT:RANG 1000"])

    def test_model_2410_sweep_rejects_more_than_1100_volts(self):
        driver = self.make_driver()
        driver.found_idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2410"

        with self.assertRaisesRegex(ValueError, "1100 V limit"):
            driver.configure_voltage_sweep([0, -1101])


if __name__ == "__main__":
    unittest.main()
