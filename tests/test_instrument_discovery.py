import unittest
from unittest.mock import patch

from lgad_ivcv.inst.instbase import InstBase


class FakeResource:
    def __init__(self, idn=None, error=None):
        self.idn = idn
        self.error = error
        self.close_count = 0

    def query(self, _command):
        if self.error is not None:
            raise self.error
        return self.idn

    def close(self):
        self.close_count += 1


class FakeResourceManager:
    def __init__(self, resources):
        self.resources = resources
        self.close_count = 0
        self.opened = []

    def list_resources(self):
        return tuple(self.resources)

    def open_resource(self, name, **_kwargs):
        self.opened.append(name)
        return self.resources[name]

    def close(self):
        self.close_count += 1


class InstrumentDiscoveryTests(unittest.TestCase):
    def test_matching_resource_and_manager_are_closed_once(self):
        resource = FakeResource("KEITHLEY INSTRUMENTS INC.,MODEL 2400")
        manager = FakeResourceManager(
            {"ASRL/dev/ttyUSB0::INSTR": resource}
        )
        instrument = InstBase()

        with patch(
            "lgad_ivcv.inst.instbase.pyvisa.ResourceManager",
            return_value=manager,
        ):
            found = instrument.find_inst(msg="MODEL 2400")

        self.assertEqual(found, "ASRL/dev/ttyUSB0::INSTR")
        self.assertEqual(
            instrument.found_idn,
            "KEITHLEY INSTRUMENTS INC.,MODEL 2400",
        )
        self.assertEqual(resource.close_count, 1)
        self.assertEqual(manager.close_count, 1)

    def test_nonmatching_resources_are_closed_once(self):
        resource = FakeResource("OTHER INSTRUMENT")
        manager = FakeResourceManager(
            {"ASRL/dev/ttyUSB1::INSTR": resource}
        )
        instrument = InstBase()

        with patch(
            "lgad_ivcv.inst.instbase.pyvisa.ResourceManager",
            return_value=manager,
        ):
            found = instrument.find_inst(msg="MODEL 2400")

        self.assertIsNone(found)
        self.assertIsNone(instrument.found_idn)
        self.assertEqual(resource.close_count, 1)
        self.assertEqual(manager.close_count, 1)

    def test_matching_gpib_resource_is_found(self):
        resource = FakeResource("KEITHLEY INSTRUMENTS INC.,MODEL 2400")
        manager = FakeResourceManager({"GPIB0::24::INSTR": resource})
        instrument = InstBase()

        with patch(
            "lgad_ivcv.inst.instbase.pyvisa.ResourceManager",
            return_value=manager,
        ):
            found = instrument.find_inst(msg="MODEL 2400")

        self.assertEqual(found, "GPIB0::24::INSTR")
        self.assertEqual(manager.opened, ["GPIB0::24::INSTR"])
        self.assertEqual(resource.close_count, 1)
        self.assertEqual(manager.close_count, 1)

    def test_keithley_2400_driver_also_matches_model_2410(self):
        from lgad_ivcv.inst import Keithley2400

        resource = FakeResource("KEITHLEY INSTRUMENTS INC.,MODEL 2410")
        manager = FakeResourceManager({"GPIB0::24::INSTR": resource})

        with patch(
            "lgad_ivcv.inst.instbase.pyvisa.ResourceManager",
            return_value=manager,
        ):
            found = Keithley2400().find_inst()

        self.assertEqual(found, "GPIB0::24::INSTR")

    def test_unrelated_visa_resource_is_not_probed(self):
        resource = FakeResource("KEITHLEY INSTRUMENTS INC.,MODEL 2400")
        manager = FakeResourceManager({"TCPIP0::192.0.2.1::INSTR": resource})
        instrument = InstBase()

        with patch(
            "lgad_ivcv.inst.instbase.pyvisa.ResourceManager",
            return_value=manager,
        ):
            found = instrument.find_inst(msg="MODEL 2400")

        self.assertIsNone(found)
        self.assertEqual(manager.opened, [])
        self.assertEqual(resource.close_count, 0)
        self.assertEqual(manager.close_count, 1)


if __name__ == "__main__":
    unittest.main()
