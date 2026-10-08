import os
import unittest
from unittest.mock import patch

from lgad_ivcv.inst import visa
from lgad_ivcv.inst.instbase import InstBase


class FakeController:
    instances = []

    def __init__(self, timeout_usec=None):
        self.identities = {24: "KEITHLEY INSTRUMENTS INC.,MODEL 2400"}
        self.writes = []
        self.closed = False
        self.pending = None
        FakeController.instances.append(self)

    def write(self, address, message):
        if address not in self.identities:
            raise visa.GpibError("write error NO_LISTENER")
        self.writes.append((address, message))
        self.pending = self.identities[address] + "\n"

    def read(self, address, length):
        return self.pending.encode()

    def close(self):
        self.closed = True


class FakeVisaManager:
    def __init__(self, resources=()):
        self.resources = resources
        self.opened = []
        self.closed = False

    def list_resources(self):
        return tuple(self.resources)

    def open_resource(self, name, **_options):
        self.opened.append(name)
        raise AssertionError(f"PyVISA should not open {name}")

    def close(self):
        self.closed = True


class NIUSBGPIBBackendTests(unittest.TestCase):
    def setUp(self):
        FakeController.instances = []
        patches = [
            patch.object(visa, "NIUSBGPIB", FakeController),
            patch.dict(os.environ, {visa.GPIB_BACKEND_ENV: "niusb"}),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_gpib_resource_names_are_parsed(self):
        self.assertEqual(visa.gpib_address("GPIB0::24::INSTR"), 24)
        self.assertEqual(visa.gpib_address("gpib::5::INSTR"), 5)
        self.assertIsNone(visa.gpib_address("ASRL/dev/ttyUSB0::INSTR"))

    def test_gpib_resource_uses_adapter_and_strips_reply(self):
        manager = visa.ResourceManager()
        resource = manager.open_resource(
            "GPIB0::24::INSTR",
            read_termination="\r",
        )

        self.assertEqual(
            resource.query("*IDN?"),
            "KEITHLEY INSTRUMENTS INC.,MODEL 2400",
        )
        resource.close()
        manager.close()

        controller, = FakeController.instances
        self.assertEqual(controller.writes, [(24, "*IDN?")])
        self.assertTrue(controller.closed)

    def test_resources_share_one_adapter(self):
        manager = visa.ResourceManager()
        first = manager.open_resource("GPIB0::24::INSTR")
        second = manager.open_resource("GPIB0::24::INSTR")
        first.close()

        self.assertEqual(len(FakeController.instances), 1)
        self.assertFalse(FakeController.instances[0].closed)

        second.close()
        self.assertTrue(FakeController.instances[0].closed)

    def test_discovery_scans_adapter_instead_of_visa_gpib(self):
        visa_manager = FakeVisaManager(
            ("GPIB0::7::INSTR", "TCPIP0::192.0.2.1::INSTR")
        )

        with patch.object(
            visa.pyvisa,
            "ResourceManager",
            return_value=visa_manager,
        ):
            instrument = InstBase()
            found = instrument.find_inst(msg="MODEL 2400")

        self.assertEqual(found, "GPIB0::24::INSTR")
        self.assertEqual(
            instrument.found_idn,
            "KEITHLEY INSTRUMENTS INC.,MODEL 2400",
        )
        self.assertEqual(visa_manager.opened, [])
        self.assertTrue(visa_manager.closed)
        self.assertTrue(all(c.closed for c in FakeController.instances))

    def test_visa_backend_bypasses_adapter(self):
        visa_manager = FakeVisaManager()

        with patch.dict(os.environ, {visa.GPIB_BACKEND_ENV: "visa"}), \
                patch.object(
                    visa.pyvisa,
                    "ResourceManager",
                    return_value=visa_manager,
                ):
            with self.assertRaises(AssertionError):
                visa.ResourceManager().open_resource("GPIB0::24::INSTR")

        self.assertEqual(visa_manager.opened, ["GPIB0::24::INSTR"])
        self.assertEqual(FakeController.instances, [])

    def test_invalid_backend_is_rejected(self):
        with patch.dict(os.environ, {visa.GPIB_BACKEND_ENV: "bogus"}):
            with self.assertRaises(ValueError):
                visa.use_niusb_gpib()


if __name__ == "__main__":
    unittest.main()
