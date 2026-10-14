import unittest
from unittest.mock import Mock, call, patch

from lgad_ivcv.inst import Keithley2400, Keithley2470
from lgad_ivcv.inst.instbase import InstError
from lgad_ivcv.inst.smu import open_smu, smu_driver_for_identity
from lgad_ivcv.ivcv.IVMeasurement import IVMeasurement
from lgad_ivcv.ivcv.iv_sw import IV_sw


class SMUSelectionTests(unittest.TestCase):
    def test_identity_selects_expected_driver(self):
        self.assertIs(
            smu_driver_for_identity("KEITHLEY INSTRUMENTS INC.,MODEL 2400"),
            Keithley2400,
        )
        self.assertIs(
            smu_driver_for_identity("KEITHLEY INSTRUMENTS INC.,MODEL 2410"),
            Keithley2400,
        )
        self.assertIs(
            smu_driver_for_identity("KEITHLEY INSTRUMENTS,MODEL 2470"),
            Keithley2470,
        )

    def test_unsupported_identity_is_rejected(self):
        with self.assertRaisesRegex(InstError, "Unsupported SMU"):
            smu_driver_for_identity("ACME,MODEL 1234")

    def test_supported_models_open_over_gpib_and_serial_resources(self):
        models = (
            ("KEITHLEY INSTRUMENTS INC.,MODEL 2400", Keithley2400),
            ("KEITHLEY INSTRUMENTS INC.,MODEL 2410", Keithley2400),
            ("KEITHLEY INSTRUMENTS,MODEL 2470", Keithley2470),
        )
        resources = (
            ("GPIB0::18::INSTR", None),
            ("ASRL/dev/ttyUSB0::INSTR", "\r"),
        )

        for identity, driver_type in models:
            for resource, read_termination in resources:
                with self.subTest(identity=identity, resource=resource), patch(
                    "lgad_ivcv.inst.smu.query_identity",
                    return_value=identity,
                ) as identify, patch.object(driver_type, "open") as open_instrument:
                    smu = open_smu(resource)

                self.assertIsInstance(smu, driver_type)
                identify.assert_called_once_with(
                    resource,
                    read_termination=read_termination,
                    backend=None,
                )
                open_instrument.assert_called_once_with(resource, backend=None)

    def test_open_smu_identifies_and_opens_2470_on_shared_backend(self):
        backend = object()
        with patch(
            "lgad_ivcv.inst.smu.query_identity",
            return_value="KEITHLEY INSTRUMENTS,MODEL 2470",
        ) as identify, patch.object(
            Keithley2470,
            "open",
        ) as open_instrument:
            smu = open_smu("GPIB0::18::INSTR", backend=backend)

        self.assertIsInstance(smu, Keithley2470)
        identify.assert_called_once_with(
            "GPIB0::18::INSTR",
            read_termination=None,
            backend=backend,
        )
        open_instrument.assert_called_once_with(
            "GPIB0::18::INSTR",
            backend=backend,
        )

    def test_serial_identity_falls_back_from_2400_to_2470_termination(self):
        resource = "ASRL/dev/ttyUSB0::INSTR"
        with patch(
            "lgad_ivcv.inst.smu.query_identity",
            side_effect=(
                TimeoutError("no CR-terminated reply"),
                "KEITHLEY INSTRUMENTS,MODEL 2470",
            ),
        ) as identify, patch.object(Keithley2470, "open"):
            smu = open_smu(resource)

        self.assertIsInstance(smu, Keithley2470)
        self.assertEqual(
            identify.call_args_list,
            [
                call(
                    resource,
                    read_termination="\r",
                    backend=None,
                ),
                call(
                    resource,
                    read_termination="\n",
                    backend=None,
                ),
            ],
        )

    def test_explicit_2470_resource_uses_2470_driver(self):
        runner = IV_sw.__new__(IV_sw)
        runner.dryrun = False
        runner.smu = Keithley2400()
        backend = object()

        selected_smu = Keithley2470()
        with patch(
            "lgad_ivcv.ivcv.iv_sw.identify_smu",
            return_value=selected_smu,
        ) as open_selected_smu, patch.object(
            runner,
            "_get_instrument_backend",
            return_value=backend,
        ):
            runner.set_smu("GPIB0::18::INSTR")

        self.assertIs(runner.smu, selected_smu)
        self.assertEqual(runner.smu_rsrc, "GPIB0::18::INSTR")
        open_selected_smu.assert_called_once_with("GPIB0::18::INSTR")

    def test_measurement_initialization_preserves_smu_terminal_selection(self):
        for driver_type in (Keithley2400, Keithley2470):
            with self.subTest(driver=driver_type.__name__):
                smu = driver_type()
                smu._inst = Mock()
                smu._inst.query.side_effect = lambda command: "SCPI" if command == "*LANG?" else '0,"No error"'
                with patch.object(smu, "sleep"):
                    measurement = IVMeasurement()
                    measurement.set_smu(smu)
                commands = [args.args[0].upper() for args in smu._inst.write.call_args_list]
                self.assertFalse(any("ROUT:TERM" in command for command in commands))
                self.assertNotIn("*RST", commands)

    def test_iv_measurement_string_resource_uses_selected_driver(self):
        selected_smu = Mock(spec=Keithley2470)
        with patch(
            "lgad_ivcv.ivcv.IVMeasurement.open_smu",
            return_value=selected_smu,
        ) as open_selected_smu:
            measurement = IVMeasurement()
            measurement.set_smu("ASRL/dev/ttyUSB0::INSTR")

        self.assertIs(measurement.smu, selected_smu)
        open_selected_smu.assert_called_once_with(
            "ASRL/dev/ttyUSB0::INSTR"
        )
        selected_smu.initialize.assert_called_once_with(
            current_compliance=measurement.current_compliance
        )
        selected_smu.set_front_rear.assert_not_called()


if __name__ == "__main__":
    unittest.main()
