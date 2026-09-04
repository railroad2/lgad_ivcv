import unittest
from unittest.mock import patch

from lgad_ivcv.gui.instrument_finder import InstrumentFinder


class InstrumentFinderTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
