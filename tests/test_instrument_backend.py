import unittest
from unittest.mock import Mock

from lgad_ivcv.inst.backend import (
    InstrumentBackend,
    NIGPIBResource,
    parse_gpib_resource,
)


class FakeGPIBController:
    def __init__(self):
        self.calls = []
        self.close_count = 0

    def write(self, address, command):
        self.calls.append(("write", address, command))

    def query(self, address, command):
        self.calls.append(("query", address, command))
        return "KEITHLEY INSTRUMENTS,MODEL 2470"

    def close(self):
        self.close_count += 1


class FakeVisaManager:
    def __init__(self, resource=None, resources=()):
        self.resource = resource
        self.resources = resources
        self.opened = []
        self.close_count = 0

    def open_resource(self, resource_name, **options):
        self.opened.append((resource_name, options))
        return self.resource

    def list_resources(self):
        return self.resources

    def close(self):
        self.close_count += 1


class InstrumentBackendTests(unittest.TestCase):
    def test_parse_gpib_resource(self):
        self.assertEqual(parse_gpib_resource("GPIB0::18::INSTR"), (0, 18))
        self.assertIsNone(parse_gpib_resource("ASRL/dev/ttyUSB0::INSTR"))
        with self.assertRaisesRegex(ValueError, "GPIB0"):
            parse_gpib_resource("GPIB1::18::INSTR")
        with self.assertRaisesRegex(ValueError, "between 1 and 30"):
            parse_gpib_resource("GPIB0::31::INSTR")

    def test_gpib_resource_uses_ni_controller(self):
        controller = FakeGPIBController()
        visa_factory = Mock(side_effect=AssertionError("PyVISA was used"))
        backend = InstrumentBackend(
            visa_manager_factory=visa_factory,
            gpib_controller_factory=lambda: controller,
        )

        resource = backend.open_resource(
            "GPIB0::18::INSTR",
            read_termination="\n",
        )
        self.assertIsInstance(resource, NIGPIBResource)
        self.assertEqual(resource.query("*IDN?"), "KEITHLEY INSTRUMENTS,MODEL 2470")
        resource.write(":OUTP OFF")
        resource.close()
        backend.close()

        self.assertEqual(
            controller.calls,
            [
                ("query", 18, "*IDN?"),
                ("write", 18, ":OUTP OFF"),
            ],
        )
        self.assertEqual(controller.close_count, 1)
        visa_factory.assert_not_called()

    def test_serial_resource_uses_pyvisa(self):
        resource = Mock()
        visa_manager = FakeVisaManager(resource=resource)
        gpib_factory = Mock(side_effect=AssertionError("NI GPIB was used"))
        backend = InstrumentBackend(
            visa_manager_factory=lambda: visa_manager,
            gpib_controller_factory=gpib_factory,
        )

        opened = backend.open_resource(
            "ASRL/dev/ttyUSB0::INSTR",
            read_termination="\r",
        )
        backend.close()

        self.assertIs(opened, resource)
        self.assertEqual(
            visa_manager.opened,
            [
                (
                    "ASRL/dev/ttyUSB0::INSTR",
                    {"read_termination": "\r"},
                )
            ],
        )
        self.assertEqual(visa_manager.close_count, 1)
        gpib_factory.assert_not_called()

    def test_discovery_replaces_visa_gpib_with_ni_addresses(self):
        controller = FakeGPIBController()
        visa_manager = FakeVisaManager(
            resources=(
                "ASRL/dev/ttyUSB0::INSTR",
                "GPIB0::18::INSTR",
            )
        )
        backend = InstrumentBackend(
            visa_manager_factory=lambda: visa_manager,
            gpib_controller_factory=lambda: controller,
        )

        resources = backend.list_resources()
        backend.close()

        self.assertEqual(resources[0], "ASRL/dev/ttyUSB0::INSTR")
        self.assertIn("GPIB0::18::INSTR", resources)
        self.assertEqual(len(resources), 31)
        self.assertEqual(controller.close_count, 1)


if __name__ == "__main__":
    unittest.main()
