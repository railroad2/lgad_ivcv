import unittest
from unittest.mock import patch

from lgad_ivcv.gui.instrument_finder import InstrumentFinder


class InstrumentFinderTests(unittest.TestCase):
    class FakeVisaResource:
        def __init__(self, identity):
            self.identity = identity
            self.closed = False

        def query(self, command):
            if command != "*IDN?":
                raise AssertionError(command)
            return self.identity

        def close(self):
            self.closed = True

    class FakeResourceManager:
        def __init__(self, resource):
            self.resource = resource
            self.opened = []
            self.closed = False

        def open_resource(self, resource_name, **options):
            self.opened.append((resource_name, options))
            return self.resource

        def close(self):
            self.closed = True

    def test_found_resource_is_emitted(self):
        class FakeInstrument:
            found_idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2400"

            def find_inst(self):
                return "ASRL/dev/ttyUSB0::INSTR"

        finder = InstrumentFinder("smu")
        found = []
        finder.found.connect(
            lambda resource, identity: found.append((resource, identity))
        )

        with patch.dict(
            "lgad_ivcv.gui.instrument_finder.INSTRUMENT_FACTORIES",
            {"smu": FakeInstrument},
        ):
            finder.run()

        self.assertEqual(
            found,
            [
                (
                    "ASRL/dev/ttyUSB0::INSTR",
                    "KEITHLEY INSTRUMENTS INC.,MODEL 2400",
                )
            ],
        )

    def test_not_found_is_emitted(self):
        class FakeInstrument:
            def find_inst(self):
                return None

        finder = InstrumentFinder("lcr")
        not_found = []
        finder.not_found.connect(lambda: not_found.append(True))

        with patch.dict(
            "lgad_ivcv.gui.instrument_finder.INSTRUMENT_FACTORIES",
            {"lcr": FakeInstrument},
        ):
            finder.run()

        self.assertEqual(not_found, [True])

    def test_smu_search_tries_multiple_driver_types(self):
        class Missing2400:
            def find_inst(self):
                return None

        class Found2470:
            found_idn = "KEITHLEY INSTRUMENTS,MODEL 2470"

            def find_inst(self):
                return "GPIB0::18::INSTR"

        finder = InstrumentFinder("smu")
        found = []
        finder.found.connect(lambda *args: found.append(args))

        with patch.dict(
            "lgad_ivcv.gui.instrument_finder.INSTRUMENT_FACTORIES",
            {"smu": (Missing2400, Found2470)},
        ):
            finder.run()

        self.assertEqual(
            found,
            [("GPIB0::18::INSTR", "KEITHLEY INSTRUMENTS,MODEL 2470")],
        )

    def test_search_error_is_emitted(self):
        class FakeInstrument:
            def find_inst(self):
                raise RuntimeError("VISA backend unavailable")

        finder = InstrumentFinder("pau")
        failures = []
        finder.failed.connect(failures.append)

        with patch.dict(
            "lgad_ivcv.gui.instrument_finder.INSTRUMENT_FACTORIES",
            {"pau": FakeInstrument},
        ):
            finder.run()

        self.assertEqual(failures, ["VISA backend unavailable"])

    def test_existing_resource_is_checked_before_full_search(self):
        class FakeInstrument:
            _verify_msg = ("MODEL 2400", "MODEL 2410")
            _read_termination = "\r"

            def find_inst(self):
                raise AssertionError("full search should not run")

        visa_resource = self.FakeVisaResource(
            "KEITHLEY INSTRUMENTS INC.,MODEL 2410"
        )
        manager = self.FakeResourceManager(visa_resource)
        finder = InstrumentFinder(
            "smu",
            preferred_resource="GPIB0::24::INSTR",
        )
        found = []
        finder.found.connect(lambda *args: found.append(args))

        with patch.dict(
            "lgad_ivcv.gui.instrument_finder.INSTRUMENT_FACTORIES",
            {"smu": FakeInstrument},
        ), patch(
            "lgad_ivcv.gui.instrument_finder.pyvisa.ResourceManager",
            return_value=manager,
        ):
            finder.run()

        self.assertEqual(
            found,
            [
                (
                    "GPIB0::24::INSTR",
                    "KEITHLEY INSTRUMENTS INC.,MODEL 2410",
                )
            ],
        )
        self.assertTrue(visa_resource.closed)
        self.assertTrue(manager.closed)

    def test_invalid_existing_resource_falls_back_to_full_search(self):
        class FakeInstrument:
            _verify_msg = "MODEL 2400"
            _read_termination = "\r"
            found_idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2400"

            def find_inst(self):
                return "GPIB0::25::INSTR"

        visa_resource = self.FakeVisaResource("UNSUPPORTED INSTRUMENT")
        manager = self.FakeResourceManager(visa_resource)
        finder = InstrumentFinder(
            "smu",
            preferred_resource="GPIB0::99::INSTR",
        )
        found = []
        finder.found.connect(lambda *args: found.append(args))

        with patch.dict(
            "lgad_ivcv.gui.instrument_finder.INSTRUMENT_FACTORIES",
            {"smu": FakeInstrument},
        ), patch(
            "lgad_ivcv.gui.instrument_finder.pyvisa.ResourceManager",
            return_value=manager,
        ):
            finder.run()

        self.assertEqual(
            found,
            [
                (
                    "GPIB0::25::INSTR",
                    "KEITHLEY INSTRUMENTS INC.,MODEL 2400",
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
