import os
import re
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from lgad_ivcv.gui.channel_grid import ChannelGrid
    from lgad_ivcv.gui.iv_worker import IVRunConfig, IVWorker
    from lgad_ivcv.gui.main_window import MainWindow
except ImportError:
    QApplication = None
    ChannelGrid = None
    IVRunConfig = None
    IVWorker = None
    MainWindow = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class ChannelGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setOrganizationName("LGAD GUI tests")
        cls.app.setApplicationName("LGAD GUI tests")
        QSettings().clear()

    def test_all_linear_channels_are_selected_initially(self):
        grid = ChannelGrid()
        self.assertEqual(grid.selected_channels(), list(range(256)))

    def test_rows_and_columns_toggle_linear_channels(self):
        grid = ChannelGrid()
        grid.clear_all()
        grid.toggle_row(2)
        self.assertEqual(grid.selected_channels(), list(range(32, 48)))

        grid.clear_all()
        grid.toggle_col(3)
        self.assertEqual(grid.selected_channels(), list(range(3, 256, 16)))

    def test_selection_mode_expands_cell_to_whole_row_or_column(self):
        grid = ChannelGrid()
        grid.clear_all()
        grid.set_selection_mode("row")
        grid._buttons[2][5].click()
        self.assertEqual(grid.selected_targets(), [2])
        self.assertEqual(grid.selected_channels(), list(range(32, 48)))

        grid.clear_all()
        grid.set_selection_mode("column")
        grid._buttons[7][3].click()
        self.assertEqual(grid.selected_targets(), [3])
        self.assertEqual(grid.selected_channels(), list(range(3, 256, 16)))


class FakeIVMeasurement:
    def __init__(self):
        self.output_arr = []
        self.n_measurement_points = 1
        self.callback = None

    def set_data_callback(self, callback):
        self.callback = callback

    def get_out_dir(self):
        return "/tmp/result/measurement"


class FakeIVRunner:
    def __init__(self, *_args):
        self.iv = FakeIVMeasurement()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def set_smu(self, _resource):
        pass

    def set_pau(self, _resource):
        pass

    def set_basepath(self, _path):
        pass

    def set_sensor_name(self, _name):
        pass

    def prepare_output_directory(self):
        return self.iv.get_out_dir()

    def set_sweep(self, *_args):
        pass

    def set_compliance(self, _value):
        pass

    def measure_channel(self, channels, on_channel_start, on_channel_complete):
        channel = channels[0]
        self._measure(channel, on_channel_start, on_channel_complete)

    def measure_rows(self, rows, on_row_start, on_row_complete):
        self._measure(rows[0], on_row_start, on_row_complete)

    def measure_col(self, cols, on_col_start, on_col_complete):
        self._measure(cols[0], on_col_start, on_col_complete)

    def _measure(self, target, on_start, on_complete):
        on_start(target, 0, 1)
        self.iv.output_arr.append([-1.0, -2e-9, -3e-6])
        self.iv.callback(self.iv.output_arr[-1])
        on_complete(target, 0, 1)

    def stop_requested(self):
        return False

    def request_stop(self):
        pass


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class IVWorkerTests(unittest.TestCase):
    def test_worker_dispatches_all_measurement_modes(self):
        for mode, target in (("channel", 7), ("row", 2), ("column", 3)):
            with self.subTest(mode=mode):
                config = IVRunConfig(
                    port="ws://test:8765",
                    smu_resource=None,
                    pau_resource=None,
                    sensor_name="sensor",
                    result_path="/tmp/result",
                    start_voltage=0,
                    end_voltage=-10,
                    voltage_step=1,
                    current_compliance=1e-5,
                    return_sweep=False,
                    dry_run=True,
                    measurement_mode=mode,
                    targets=(target,),
                )
                worker = IVWorker(config)
                points = []
                completions = []
                result_paths = []
                worker.point_measured.connect(lambda *args: points.append(args))
                worker.completed.connect(lambda *args: completions.append(args))
                worker.result_path_ready.connect(result_paths.append)

                with patch("lgad_ivcv.gui.iv_worker.IV_sw", FakeIVRunner):
                    worker.run()

                self.assertEqual(
                    points,
                    [(mode, target, -1.0, -2e-9, -3e-6, 1, 1)],
                )
                self.assertEqual(
                    completions,
                    [(False, "/tmp/result/measurement")],
                )
                self.assertEqual(result_paths, ["/tmp/result/measurement"])


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setOrganizationName("LGAD main window tests")
        cls.app.setApplicationName("LGAD main window tests")
        QSettings().clear()

    def test_channel_and_plot_are_independent_windows(self):
        window = MainWindow()

        self.assertTrue(window.channel_window.isWindow())
        self.assertTrue(window.live_iv_window.isWindow())
        self.assertIsNot(window.channel_grid.window(), window)
        self.assertIsNot(window.plot_widget.window(), window)
        self.assertIs(window.log_edit.window(), window)
        self.assertFalse(window.live_iv_window.isVisible())

        window._show_live_iv_window()
        self.assertTrue(window.live_iv_window.isVisible())

        window.close()

    def test_status_log_is_written_under_result_path(self):
        window = MainWindow()

        with tempfile.TemporaryDirectory() as result_path:
            window._append_log("Measurement started")
            first_path = window._start_file_log(result_path)
            window._append_log("Measurement completed")
            second_path = window._start_file_log(result_path)

            self.assertEqual(first_path.parent.as_posix(), result_path)
            self.assertRegex(
                first_path.name,
                r"^IV_GUI_\d{4}-\d{2}-\d{2}T\d{6}_v0\.log$",
            )
            self.assertNotEqual(first_path, second_path)
            self.assertRegex(
                first_path.read_text(encoding="utf-8"),
                re.compile(
                    r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] "
                    r"Measurement started\n"
                    r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] "
                    r"Measurement completed\n$"
                ),
            )

        window.close()


if __name__ == "__main__":
    unittest.main()
