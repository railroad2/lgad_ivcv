import unittest

from lgad_ivcv.inst.Keithley2470 import Keithley2470
from lgad_ivcv.inst.instbase import InstError


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


class Keithley2470Tests(unittest.TestCase):
    def make_driver(self, responses=None):
        driver = Keithley2470()
        driver._inst = FakeVisaInstrument(responses)
        driver.set_delay(0)
        return driver

    def test_identity_and_line_termination_are_for_2470(self):
        driver = Keithley2470()

        self.assertEqual(driver._verify_msg, "MODEL 2470")
        self.assertEqual(driver._read_termination, "\n")

    def test_initialize_uses_2470_scpi_commands(self):
        driver = self.make_driver({"*LANG?": "SCPI\n"})

        driver.initialize()

        self.assertEqual(driver._inst.queries, ["*LANG?"])
        self.assertIn(":SOUR:FUNC VOLT", driver._inst.writes)
        self.assertIn(':SENS:FUNC "CURR"', driver._inst.writes)
        self.assertIn(":SOUR:VOLT:READ:BACK ON", driver._inst.writes)
        self.assertIn(":SOUR:VOLT:ILIM 1e-05", driver._inst.writes)
        self.assertIn(":SOUR:VOLT 0", driver._inst.writes)
        self.assertNotIn(":SENS:CURR:PROT 1e-05", driver._inst.writes)

    def test_initialize_rejects_tsp_mode(self):
        driver = self.make_driver({"*LANG?": "TSP\n"})

        with self.assertRaisesRegex(InstError, "not in SCPI mode"):
            driver.initialize()

        self.assertEqual(driver._inst.writes, [])

    def test_read_requests_source_voltage_and_measured_current(self):
        command = ':READ? "defbuffer1", SOUR, READ'
        driver = self.make_driver({command: "-10.01,-1.2e-6\n"})

        self.assertEqual(driver.measure(), [-10.01, -1.2e-6])
        self.assertEqual(driver._inst.queries, [command])

    def test_voltage_ramp_uses_correct_direction(self):
        driver = self.make_driver({":SOUR:VOLT?": "0\n"})

        driver.set_voltage_ramp(-3, step=1)

        self.assertEqual(
            driver._inst.writes,
            [":SOUR:VOLT -1.0", ":SOUR:VOLT -2.0", ":SOUR:VOLT -3"],
        )


if __name__ == "__main__":
    unittest.main()
