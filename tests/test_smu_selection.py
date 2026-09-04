import unittest
from unittest.mock import patch

from lgad_ivcv.inst import Keithley2400, Keithley2470
from lgad_ivcv.ivcv.iv_sw import IV_sw, _smu_driver_for_identity


class SMUSelectionTests(unittest.TestCase):
    def test_identity_selects_expected_driver(self):
        self.assertIs(
            _smu_driver_for_identity("KEITHLEY INSTRUMENTS INC.,MODEL 2400"),
            Keithley2400,
        )
        self.assertIs(
            _smu_driver_for_identity("KEITHLEY INSTRUMENTS INC.,MODEL 2410"),
            Keithley2400,
        )
        self.assertIs(
            _smu_driver_for_identity("KEITHLEY INSTRUMENTS,MODEL 2470"),
            Keithley2470,
        )

    def test_explicit_2470_resource_uses_2470_driver(self):
        runner = IV_sw.__new__(IV_sw)
        runner.dryrun = False
        runner.smu = Keithley2400()

        with patch(
            "lgad_ivcv.ivcv.iv_sw._query_visa_identity",
            return_value="KEITHLEY INSTRUMENTS,MODEL 2470",
        ), patch.object(Keithley2470, "open") as open_instrument:
            runner.set_smu("GPIB0::18::INSTR")

        self.assertIsInstance(runner.smu, Keithley2470)
        self.assertEqual(runner.smu_rsrc, "GPIB0::18::INSTR")
        open_instrument.assert_called_once_with("GPIB0::18::INSTR")


if __name__ == "__main__":
    unittest.main()
