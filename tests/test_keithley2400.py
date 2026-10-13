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


if __name__ == "__main__":
    unittest.main()
