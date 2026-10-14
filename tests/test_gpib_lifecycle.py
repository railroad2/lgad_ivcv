"""Regression tests for exclusive USB ownership during matrix measurements."""
import unittest
from unittest.mock import Mock, patch

from lgad_ivcv.inst.backend import InstrumentBackend
from lgad_ivcv.inst.instbase import InstBase
from lgad_ivcv.ivcv.iv_sw import IV_sw
from lgad_ivcv.ivcv.cv_sw import CV_sw


class GPIBLifecycleTests(unittest.TestCase):
    def test_discovery_releases_and_channel_loop_shares_measurement_connection(self):
        state = {"opens": 0, "active": False, "closes": 0}

        class Controller:
            def __init__(self):
                if state["active"]:
                    raise RuntimeError("resource busy")
                state["active"] = True
                state["opens"] += 1

            def query(self, address, command):
                if address == 6:
                    return "WAYNE KERR, 4300"
                models = {24: "2400", 23: "6487"}
                if address not in models:
                    raise TimeoutError("No instrument")
                return f"KEITHLEY INSTRUMENTS INC.,MODEL {models[address]}"

            def close(self):
                state["active"] = False
                state["closes"] += 1

        with patch('lgad_ivcv.inst.backend._load_ni_gpib_controller', return_value=Controller), patch(
            'lgad_ivcv.inst.backend.pyvisa.ResourceManager'
        ) as visa:
            visa.return_value.list_resources.return_value = ()
            for runner_type, primary, model_address in (
                (IV_sw, "smu", 24),
                (CV_sw, "lcr", 6),
            ):
                runner = runner_type(port=None)
                runner.swm = Mock()
                runner.prepare_output_directory = Mock()
                with self.subTest(runner=runner_type.__name__):
                    try:
                        getattr(runner, f"set_{primary}")()
                        self.assertFalse(state["active"])
                        runner.set_pau(None if primary == "smu" else "GPIB0::23::INSTR")
                        self.assertFalse(state["active"])
                        before = state["opens"]
                        measurement = runner.iv if primary == "smu" else runner.cv
                        # Exercise real session + channel loops, stubbing instrument sweep only.
                        measurement.initialize_measurement = Mock()
                        measurement.set_measurement_options = Mock()
                        measurement.measurement_thread = Mock()
                        controllers = []
                        def start(*args, **kwargs):
                            controller = getattr(runner, primary)._inst.controller
                            controllers.append(controller)
                            self.assertIs(runner.pau._inst.controller, controller)
                            self.assertEqual(state["opens"], before + 1)
                            self.assertTrue(state["active"])
                        measurement.start_measurement = Mock(side_effect=start)
                        with patch('time.sleep'):
                            runner.measure_channel([0, 1, 2], verbose=0)
                        self.assertEqual(len(controllers), 3)
                        self.assertTrue(all(c is controllers[0] for c in controllers))
                        self.assertFalse(state["active"])
                        self.assertEqual(state["opens"], state["closes"])
                        # A new measurement opens a new session and releases it on failure.
                        measurement.start_measurement.side_effect = RuntimeError("sweep failed")
                        with patch('time.sleep'), self.assertRaisesRegex(RuntimeError, 'sweep failed'):
                            runner.measure_channel([0], verbose=0)
                        self.assertFalse(state["active"])
                        self.assertEqual(state["opens"], state["closes"])
                    finally:
                        runner.close()
                    self.assertEqual(state["opens"], state["closes"])

    def test_discovery_failure_closes_its_backend(self):
        backend = Mock()
        backend.list_resources.side_effect = RuntimeError('discovery failed')
        with patch('lgad_ivcv.inst.instbase.InstrumentBackend', return_value=backend):
            with self.assertRaisesRegex(RuntimeError, 'discovery failed'):
                InstBase().find_inst()
        backend.close.assert_called_once_with()

    def test_partial_connection_failure_releases_shared_controller(self):
        for runner_type, primary in ((IV_sw, 'smu'), (CV_sw, 'lcr')):
            with self.subTest(runner=runner_type.__name__):
                controller = Mock()
                controller.query.side_effect = lambda address, command: (
                    'KEITHLEY INSTRUMENTS INC.,MODEL 2400' if primary == 'smu'
                    else 'WAYNE KERR, 4300'
                )
                backend = InstrumentBackend(gpib_controller_factory=lambda: controller)
                runner = runner_type(port=None)
                runner._instrument_backend = backend
                setattr(runner, f'{primary}_rsrc', 'GPIB0::24::INSTR')
                runner.pau_rsrc = 'GPIB0::23::INSTR'
                runner.pau = Mock()
                runner.pau.open.side_effect = RuntimeError('PAU connection failed')
                with self.assertRaisesRegex(RuntimeError, 'PAU connection failed'):
                    runner._ensure_instruments()
                controller.close.assert_called_once_with()
                self.assertIsNone(runner._instrument_backend)
                self.assertFalse(runner._instruments_open)

    def test_switch_and_instrument_close_errors_do_not_leak_controller(self):
        for runner_type, primary in ((IV_sw, 'smu'), (CV_sw, 'lcr')):
            with self.subTest(runner=runner_type.__name__):
                controller = Mock()
                factory = Mock(return_value=controller)
                backend = InstrumentBackend(gpib_controller_factory=factory)
                backend.open_resource('GPIB0::23::INSTR')
                runner = runner_type(port=None)
                runner._instrument_backend = backend
                runner.swm = Mock()
                runner.swm.off_all.side_effect = RuntimeError('switch off failed')
                runner.swm.close.side_effect = RuntimeError('WebSocket close failed')
                runner.pau = Mock()
                runner.pau.close.side_effect = RuntimeError('PAU close failed')
                instrument = Mock()
                setattr(runner, primary, instrument)
                runner.close()
                instrument.close.assert_called_once_with()
                controller.close.assert_called_once_with()
                self.assertIsNone(runner._instrument_backend)
