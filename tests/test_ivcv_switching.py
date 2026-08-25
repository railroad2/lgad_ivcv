import tempfile
import unittest
from unittest.mock import Mock, patch

from lgad_ivcv.ivcv.cv_sw import CV_sw
from lgad_ivcv.ivcv.iv_sw import IV_sw


class FakeSwitchMatrix:
    def __init__(self):
        self.calls = []
        self.comm = object()

    def on(self, pins):
        self.calls.append(("on", pins))

    def off(self, pins):
        self.calls.append(("off", pins))

    def on_row(self, row):
        self.calls.append(("on_row", row))

    def off_row(self, row):
        self.calls.append(("off_row", row))

    def on_col(self, col):
        self.calls.append(("on_col", col))

    def off_col(self, col):
        self.calls.append(("off_col", col))

    def off_all(self):
        self.calls.append(("off_all",))

    def pinstat_all(self):
        self.calls.append(("pinstat_all",))
        return [[0] * 16 for _ in range(16)]

    def close(self):
        self.calls.append(("close",))


class FakeMeasurement:
    def __init__(self):
        self.time_set = False
        self.out_dir_path = ""

    def set_measurement_time(self):
        self.time_set = True

    def prepare_output_directory(self, prefix="IV"):
        self.out_dir_path = "/tmp/result/measurement"
        return self.out_dir_path

    def get_out_dir(self):
        return self.out_dir_path


class SwitchingMeasurementTests(unittest.TestCase):
    def test_iv_and_cv_prepare_named_session_directories(self):
        for runner_type, prefix, measurement_name in (
            (IV_sw, "IV", "iv"),
            (CV_sw, "CV", "cv"),
        ):
            with self.subTest(runner=runner_type.__name__):
                with tempfile.TemporaryDirectory() as result_path:
                    runner = runner_type(port=None, dryrun=True)
                    runner.set_basepath(result_path)
                    runner.set_sensor_name("sensor")

                    output_path = runner.prepare_output_directory()

                    self.assertIn(f"/{prefix}_", output_path)
                    self.assertIn("/sensor/", output_path)
                    self.assertEqual(
                        getattr(runner, measurement_name).sensor_name,
                        "sensor",
                    )

    def test_iv_channel_uses_linear_pin_and_cleans_up_on_failure(self):
        runner = IV_sw.__new__(IV_sw)
        runner.iv = FakeMeasurement()
        runner.swm = FakeSwitchMatrix()
        runner.dryrun = False
        runner.measure_Vsweep = Mock(side_effect=RuntimeError("IV failed"))

        with patch("builtins.print"):
            with self.assertRaisesRegex(RuntimeError, "IV failed"):
                runner.measure_channel([18], verbose=0)

        runner.measure_Vsweep.assert_called_once_with(1, 2)
        self.assertEqual(
            runner.swm.calls,
            [("off_all",), ("on", 18), ("off", 18), ("off_all",)],
        )
        self.assertTrue(runner.iv.time_set)

    def test_cv_channel_uses_linear_pin_and_cleans_up_on_failure(self):
        runner = CV_sw.__new__(CV_sw)
        runner.cv = FakeMeasurement()
        runner.swm = FakeSwitchMatrix()
        runner._stop_requested = None
        runner.measure = Mock(side_effect=RuntimeError("CV failed"))

        with patch("builtins.print"):
            with self.assertRaisesRegex(RuntimeError, "CV failed"):
                runner.measure_channel([35], verbose=0)

        runner.measure.assert_called_once_with(2, 3)
        self.assertEqual(
            runner.swm.calls,
            [("off_all",), ("on", 35), ("off", 35), ("off_all",)],
        )

    def test_cv_channel_callbacks_report_progress(self):
        runner = CV_sw.__new__(CV_sw)
        runner.cv = FakeMeasurement()
        runner.swm = FakeSwitchMatrix()
        runner._stop_requested = None
        runner.measure = Mock()
        starts = []
        completions = []

        with patch("builtins.print"):
            runner.measure_channel(
                [3, 17],
                verbose=0,
                on_channel_start=lambda *args: starts.append(args),
                on_channel_complete=lambda *args: completions.append(args),
            )

        self.assertEqual(starts, [(3, 0, 2), (17, 1, 2)])
        self.assertEqual(completions, starts)

    def test_coordinate_input_is_only_a_compatibility_conversion(self):
        iv_runner = IV_sw.__new__(IV_sw)
        iv_runner.measure_channel = Mock()
        iv_runner.measure_coord([(1, 2), (3, 4)], verbose=0)
        iv_runner.measure_channel.assert_called_once_with([18, 52], verbose=0)

        cv_runner = CV_sw.__new__(CV_sw)
        cv_runner.measure_channel = Mock()
        cv_runner.measure_coord([(1, 2), (3, 4)], verbose=0)
        cv_runner.measure_channel.assert_called_once_with([18, 52], verbose=0)

    def test_iv_row_cleanup_runs_before_final_alloff(self):
        runner = IV_sw.__new__(IV_sw)
        runner.iv = FakeMeasurement()
        runner.swm = FakeSwitchMatrix()
        runner.dryrun = False
        runner.measure_Vsweep = Mock(side_effect=RuntimeError("row failed"))

        with patch("builtins.print"):
            with self.assertRaisesRegex(RuntimeError, "row failed"):
                runner.measure_rows([2], verbose=0)

        self.assertEqual(
            runner.swm.calls,
            [("off_all",), ("on_row", 2), ("off_row", 2), ("off_all",)],
        )

    def test_iv_row_and_column_callbacks_report_group_progress(self):
        runner = IV_sw.__new__(IV_sw)
        runner.iv = FakeMeasurement()
        runner.swm = FakeSwitchMatrix()
        runner.dryrun = True
        starts = []
        completions = []

        with patch("builtins.print"):
            runner.measure_rows(
                [2],
                verbose=0,
                on_row_start=lambda *args: starts.append(("row", *args)),
                on_row_complete=lambda *args: completions.append(("row", *args)),
            )
            runner.measure_col(
                [3],
                verbose=0,
                on_col_start=lambda *args: starts.append(("column", *args)),
                on_col_complete=lambda *args: completions.append(("column", *args)),
            )

        self.assertEqual(starts, [("row", 2, 0, 1), ("column", 3, 0, 1)])
        self.assertEqual(
            completions,
            [("row", 2, 0, 1), ("column", 3, 0, 1)],
        )

    def test_ivcv_close_turns_everything_off_before_disconnect(self):
        for runner_type in (IV_sw, CV_sw):
            runner = runner_type.__new__(runner_type)
            runner.swm = FakeSwitchMatrix()

            with patch("builtins.print"):
                runner.close()

            self.assertEqual(runner.swm.calls, [("off_all",), ("close",)])

    def test_cv_measurement_sets_single_target_label(self):
        runner = CV_sw.__new__(CV_sw)
        runner.cv = Mock()
        runner.dryrun = True
        runner.v0 = 0
        runner.v1 = -10
        runner.dv = 1
        runner.return_swp = False
        runner.rt_plot = False
        runner.ac_level = 0.1
        runner.freq = 1000

        with patch("builtins.print"):
            runner.measure(0, 0, target_label="single")

        runner.cv.set_measurement_target_label.assert_called_once_with("single")


if __name__ == "__main__":
    unittest.main()
