import os
import re
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QApplication, QFrame, QGroupBox, QLabel

    from lgad_ivcv.gui.channel_grid import ChannelGrid
    from lgad_ivcv.gui.cv_worker import CVRunConfig, CVWorker
    from lgad_ivcv.gui.iv_worker import IVRunConfig, IVWorker
    from lgad_ivcv.gui.main_window import MainWindow
except ImportError:
    QApplication = None
    ChannelGrid = None
    CVRunConfig = None
    CVWorker = None
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

    def test_headers_and_channel_buttons_use_compact_square_cells(self):
        grid = ChannelGrid()

        self.assertEqual(
            [header.text() for header in grid._row_headers],
            list("ABCDEFGHIJKLMNOP"),
        )
        self.assertEqual(
            [header.text() for header in grid._col_headers],
            [f"{column:02d}" for column in range(16)],
        )
        for button in (
            grid._row_headers
            + grid._col_headers
            + [item for row in grid._buttons for item in row]
        ):
            self.assertEqual(button.width(), button.height())
            self.assertEqual(button.width(), ChannelGrid.CELL_SIZE)

    def test_header_separators_divide_labels_from_channel_cells(self):
        grid = ChannelGrid()

        self.assertEqual(
            grid.header_horizontal_separator.frameShape(),
            QFrame.HLine,
        )
        self.assertEqual(
            grid.header_vertical_separator.frameShape(),
            QFrame.VLine,
        )

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

    def test_completed_measurement_targets_show_check_marks(self):
        grid = ChannelGrid()

        grid.mark_completed("channel", 18)
        self.assertEqual(grid.completed_channels(), [18])

        grid.mark_completed("row", 2)
        self.assertEqual(
            grid.completed_channels(),
            [18] + list(range(32, 48)),
        )

        grid.mark_completed("column", 3)
        self.assertEqual(
            grid.completed_channels(),
            sorted(set([18] + list(range(32, 48)) + list(range(3, 256, 16)))),
        )

        grid.clear_completed()
        self.assertEqual(grid.completed_channels(), [])


class FakeIVMeasurement:
    def __init__(self):
        self.output_arr = []
        self.n_measurement_points = 1
        self.callback = None

    def set_data_callback(self, callback):
        self.callback = callback

    def get_out_dir(self):
        return "/tmp/result/measurement"


class FakeStatusMatrix:
    def __init__(self):
        self.statuses = []

    def publish_measurement_status(self, **status):
        self.statuses.append(status)


class FakeInstrumentIdentity:
    def __init__(self, identity):
        self.found_idn = identity


class FakeIVRunner:
    last_instance = None

    def __init__(self, *_args):
        type(self).last_instance = self
        self.iv = FakeIVMeasurement()
        self.swm = FakeStatusMatrix()
        self.smu = FakeInstrumentIdentity("FAKE SMU")
        self.pau = FakeInstrumentIdentity("FAKE PAU")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def close(self):
        pass

    def set_smu(self, resource):
        self.smu_rsrc = resource or "ASRL/dev/ttyUSB0::INSTR"

    def set_pau(self, resource):
        self.pau_rsrc = resource or "ASRL/dev/ttyUSB1::INSTR"

    def set_basepath(self, _path):
        pass

    def set_sensor_name(self, _name):
        pass

    def prepare_output_directory(self, _measurement_mode=None):
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


class FakeCVMeasurement(FakeIVMeasurement):
    pass


class FakeCVRunner:
    last_instance = None

    def __init__(self, *_args):
        type(self).last_instance = self
        self.cv = FakeCVMeasurement()
        self.ac_level = None
        self.freq = None
        self.swm = FakeStatusMatrix()
        self.lcr = FakeInstrumentIdentity("FAKE LCR")
        self.pau = FakeInstrumentIdentity("FAKE PAU")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def close(self):
        pass

    def set_basepath(self, _path):
        pass

    def set_sensor_name(self, _name):
        pass

    def prepare_output_directory(self, _measurement_mode=None):
        return self.cv.get_out_dir()

    def set_lcr(self, resource):
        self.lcr_rsrc = resource or "ASRL/dev/ttyUSB2::INSTR"

    def set_pau(self, resource):
        self.pau_rsrc = resource

    def set_sweep(self, *_args):
        pass

    def measure_channel(self, channels, on_channel_start, on_channel_complete):
        self._measure(channels[0], on_channel_start, on_channel_complete)

    def measure_rows(self, rows, on_row_start, on_row_complete):
        self._measure(rows[0], on_row_start, on_row_complete)

    def measure_col(self, cols, on_col_start, on_col_complete):
        self._measure(cols[0], on_col_start, on_col_complete)

    def _measure(self, target, on_start, on_complete):
        on_start(target, 0, 1)
        point = [-1.0, 2e-12, 3e6, 4e-9]
        self.cv.output_arr.append(point)
        self.cv.callback(point)
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
                resources = []
                worker.point_measured.connect(lambda *args: points.append(args))
                worker.completed.connect(lambda *args: completions.append(args))
                worker.result_path_ready.connect(result_paths.append)
                worker.instrument_resource_resolved.connect(
                    lambda *args: resources.append(args)
                )

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
                self.assertEqual(
                    resources,
                    [
                        ("smu", "ASRL/dev/ttyUSB0::INSTR", "FAKE SMU"),
                        ("pau", "ASRL/dev/ttyUSB1::INSTR", "FAKE PAU"),
                    ],
                )
                statuses = FakeIVRunner.last_instance.swm.statuses
                self.assertEqual(
                    [status["status"] for status in statuses],
                    ["starting", "running", "running", "completed"],
                )
                self.assertTrue(
                    all(status["kind"] == "IV" for status in statuses)
                )
                self.assertTrue(all(status["mode"] == mode for status in statuses))
                self.assertNotIn("voltage", statuses[-1])


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class CVWorkerTests(unittest.TestCase):
    def test_worker_dispatches_all_cv_measurement_modes(self):
        for mode, target in (("channel", 7), ("row", 2), ("column", 3)):
            with self.subTest(mode=mode):
                config = CVRunConfig(
                    port="ws://test:8765",
                    lcr_resource=None,
                    pau_resource=None,
                    sensor_name="sensor",
                    result_path="/tmp/result",
                    start_voltage=0,
                    end_voltage=-10,
                    voltage_step=1,
                    ac_level=0.1,
                    frequency=1000,
                    return_sweep=False,
                    dry_run=True,
                    measurement_mode=mode,
                    targets=(target,),
                )
                worker = CVWorker(config)
                points = []
                starts = []
                completions = []
                resources = []
                worker.point_measured.connect(lambda *args: points.append(args))
                worker.target_started.connect(lambda *args: starts.append(args))
                worker.completed.connect(lambda *args: completions.append(args))
                worker.instrument_resource_resolved.connect(
                    lambda *args: resources.append(args)
                )

                with patch("lgad_ivcv.gui.cv_worker.CV_sw", FakeCVRunner):
                    worker.run()

                self.assertEqual(starts, [(mode, target, 0, 1)])
                self.assertEqual(
                    points,
                    [(mode, target, -1.0, 2e-12, 3e6, 4e-9, 1, 1)],
                )
                self.assertEqual(
                    completions,
                    [(False, "/tmp/result/measurement")],
                )
                self.assertEqual(
                    resources,
                    [
                        ("lcr", "ASRL/dev/ttyUSB2::INSTR", "FAKE LCR"),
                    ],
                )
                statuses = FakeCVRunner.last_instance.swm.statuses
                self.assertEqual(
                    [status["status"] for status in statuses],
                    ["starting", "running", "running", "completed"],
                )
                self.assertTrue(
                    all(status["kind"] == "CV" for status in statuses)
                )
                self.assertTrue(all(status["mode"] == mode for status in statuses))
                self.assertNotIn("voltage", statuses[-1])


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
        self.assertTrue(window.live_cv_window.isWindow())
        self.assertIsNot(window.channel_grid.window(), window)
        self.assertIsNot(window.plot_widget.window(), window)
        self.assertIs(window.log_edit.window(), window)
        self.assertFalse(window.live_iv_window.isVisible())
        self.assertFalse(window.live_cv_window.isVisible())

        window._show_live_iv_window()
        self.assertTrue(window.live_iv_window.isVisible())

        window.close()

    def test_cv_tab_builds_valid_channel_measurement_config(self):
        window = MainWindow()
        window.measurement_tabs.setCurrentIndex(1)
        window.cv_measurement_mode_combo.setCurrentIndex(0)
        window.channel_grid.clear_all()
        window.channel_grid._buttons[1][2].setChecked(True)
        window.cv_sensor_edit.setText("cv_sensor")
        window.cv_lcr_edit.setText("GPIB0::10::INSTR")

        config = window._make_cv_config()

        self.assertEqual(config.targets, (18,))
        self.assertEqual(config.measurement_mode, "channel")
        self.assertEqual(config.sensor_name, "cv_sensor")
        self.assertEqual(config.lcr_resource, "GPIB0::10::INSTR")
        self.assertEqual(config.ac_level, 0.1)
        self.assertEqual(config.frequency, 1000.0)

        window.close()

    def test_cv_pau_enable_controls_resource_and_config(self):
        QSettings().remove("cv/pau_enabled")
        window = MainWindow()

        self.assertFalse(window.cv_pau_enable_check.isChecked())
        self.assertFalse(window.cv_pau_edit.isEnabled())
        self.assertFalse(window.cv_pau_find_button.isEnabled())
        self.assertIsNone(window._make_cv_config().pau_resource)

        window.cv_pau_enable_check.setChecked(True)
        self.assertTrue(window.cv_pau_edit.isEnabled())
        self.assertTrue(window.cv_pau_find_button.isEnabled())
        with self.assertRaisesRegex(ValueError, "Enter a PAU VISA resource"):
            window._make_cv_config()

        window.cv_pau_edit.setText("ASRL/dev/ttyUSB1::INSTR")
        self.assertEqual(
            window._make_cv_config().pau_resource,
            "ASRL/dev/ttyUSB1::INSTR",
        )

        window.cv_pau_enable_check.setChecked(False)
        self.assertFalse(window.cv_pau_edit.isEnabled())
        self.assertFalse(window.cv_pau_find_button.isEnabled())
        self.assertIsNone(window._make_cv_config().pau_resource)

        window.close()

    def test_cv_tab_selects_rows_and_columns_as_measurement_targets(self):
        window = MainWindow()
        window.measurement_tabs.setCurrentIndex(1)
        window.channel_grid.clear_all()

        window.cv_measurement_mode_combo.setCurrentIndex(1)
        self.assertEqual(window.measurement_mode_combo.currentData(), "row")
        window.channel_grid.toggle_row(2)
        row_config = window._make_cv_config()
        self.assertEqual(row_config.measurement_mode, "row")
        self.assertEqual(row_config.targets, (2,))

        window.channel_grid.clear_all()
        window.cv_measurement_mode_combo.setCurrentIndex(2)
        self.assertEqual(window.measurement_mode_combo.currentData(), "column")
        window.channel_grid.toggle_col(3)
        column_config = window._make_cv_config()
        self.assertEqual(column_config.measurement_mode, "column")
        self.assertEqual(column_config.targets, (3,))

        window.close()

    def test_iv_and_cv_share_one_environment_first_result_path(self):
        settings = QSettings()
        settings.clear()
        settings.setValue("result_path", "/saved/result")
        settings.setValue("iv/result_path", "/legacy/iv")
        settings.setValue("cv/result_path", "/legacy/cv")

        with patch.dict(
            os.environ,
            {"IVCV_RESULT_PATH": "/environment/result"},
        ):
            window = MainWindow()

        self.assertEqual(window.result_path_edit.text(), "/environment/result")
        self.assertEqual(window.cv_result_path_edit.text(), "/environment/result")

        window.cv_result_path_edit.setText("/shared/result")
        self.assertEqual(window.result_path_edit.text(), "/shared/result")
        window.sensor_edit.setText("shared_sensor,description")
        self.assertEqual(
            window.cv_sensor_edit.text(),
            "shared_sensor,description",
        )
        date = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(
            window.output_path_label.text(),
            f"/shared/result/{date}/shared_sensor",
        )
        self.assertEqual(
            window.cv_output_path_label.text(),
            f"/shared/result/{date}/shared_sensor",
        )
        self.assertEqual(
            window.output_path_label.parentWidget().title(),
            "Result path",
        )
        self.assertEqual(
            window.cv_output_path_label.parentWidget().title(),
            "Result path",
        )
        self.assertNotIn(
            "Initial value source",
            [label.text() for label in window.findChildren(QLabel)],
        )
        window._save_settings()
        self.assertEqual(settings.value("result_path"), "/shared/result")
        self.assertEqual(
            settings.value("sensor_name"),
            "shared_sensor,description",
        )
        self.assertFalse(settings.contains("iv/result_path"))
        self.assertFalse(settings.contains("cv/result_path"))
        self.assertFalse(settings.contains("iv/sensor"))
        self.assertFalse(settings.contains("cv/sensor"))

        window.close()
        settings.clear()

    def test_measurement_mode_channel_setup_and_sensor_are_shared(self):
        window = MainWindow()
        window.channel_grid.clear_all()

        window.measurement_mode_combo.setCurrentIndex(1)
        window.channel_grid.toggle_row(4)
        window.cv_sensor_edit.setText("shared_sensor")

        self.assertEqual(window.cv_measurement_mode_combo.currentData(), "row")
        self.assertEqual(window.sensor_edit.text(), "shared_sensor")
        self.assertEqual(window.channel_grid.selected_targets(), [4])
        self.assertEqual(window.selection_summary_label.text(), "1 rows selected")
        self.assertEqual(
            window.cv_selection_summary_label.text(),
            "1 rows selected",
        )

        iv_config = window._make_config()
        window.measurement_tabs.setCurrentIndex(1)
        cv_config = window._make_cv_config()
        self.assertEqual(iv_config.measurement_mode, cv_config.measurement_mode)
        self.assertEqual(iv_config.targets, cv_config.targets)
        self.assertEqual(iv_config.sensor_name, cv_config.sensor_name)

        window.close()

    def test_main_window_has_iv_and_cv_tabs_and_file_exit(self):
        window = MainWindow()

        self.assertEqual(window.measurement_tabs.count(), 2)
        self.assertEqual(
            [
                window.measurement_tabs.tabText(index)
                for index in range(window.measurement_tabs.count())
            ],
            ["I-V", "C-V"],
        )
        self.assertGreaterEqual(
            window.measurement_tabs.tabBar().tabSizeHint(0).width(),
            120,
        )
        self.assertEqual(window.measurement_tabs.currentIndex(), 0)
        file_menu = next(
            action.menu()
            for action in window.menuBar().actions()
            if action.text() == "File"
        )
        self.assertIn("Exit", [action.text() for action in file_menu.actions()])

        window.close()

    def test_switching_matrix_and_instruments_are_separate_groups(self):
        window = MainWindow()
        group_titles = [
            group.title() for group in window.findChildren(QGroupBox)
        ]

        self.assertEqual(group_titles.count("Switching matrix"), 2)
        self.assertEqual(group_titles.count("Instruments"), 2)
        self.assertNotIn("Instrument connection", group_titles)
        self.assertEqual(
            [
                window.smu_find_button.text(),
                window.pau_find_button.text(),
                window.cv_lcr_find_button.text(),
                window.cv_pau_find_button.text(),
            ],
            ["Find", "Find", "Find", "Find"],
        )
        self.assertIn(
            window.matrix_status_label.text(),
            ("Checking...", "Disconnected"),
        )
        self.assertIn(
            window.cv_matrix_status_label.text(),
            ("Checking...", "Disconnected"),
        )

        window._set_iv_matrix_status("Connected")
        self.assertEqual(window.matrix_status_label.text(), "Connected")
        window.port_edit.setText("ws://another-matrix:8765")
        self.assertEqual(window.matrix_status_label.text(), "Checking...")

        window.close()

    def test_find_button_populates_visa_resource(self):
        class FakeSMU:
            found_idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2400"

            def find_inst(self):
                return "ASRL/dev/ttyUSB0::INSTR"

        window = MainWindow()
        with patch.dict(
            "lgad_ivcv.gui.instrument_finder.INSTRUMENT_FACTORIES",
            {"smu": FakeSMU},
        ):
            window.smu_find_button.click()
            deadline = time.monotonic() + 2.0
            while (
                window._instrument_search is not None
                and time.monotonic() < deadline
            ):
                self.app.processEvents()

        self.assertIsNone(window._instrument_search)
        self.assertEqual(
            window.smu_edit.text(),
            "ASRL/dev/ttyUSB0::INSTR",
        )
        self.assertIn("Found SMU", window.log_edit.toPlainText())
        self.assertIn(
            "Instrument identity: KEITHLEY INSTRUMENTS INC.,MODEL 2400",
            window.log_edit.toPlainText(),
        )

        window.close()

    def test_automatically_discovered_resources_fill_gui_fields(self):
        window = MainWindow()

        window._iv_instrument_resource_resolved(
            "smu",
            "ASRL/dev/ttyUSB4::INSTR",
            "KEITHLEY MODEL 2400",
        )
        window._cv_instrument_resource_resolved(
            "lcr",
            "ASRL/dev/ttyUSB5::INSTR",
            "WAYNE KERR MODEL 4300",
        )

        self.assertEqual(window.smu_edit.text(), "ASRL/dev/ttyUSB4::INSTR")
        self.assertEqual(window.cv_lcr_edit.text(), "ASRL/dev/ttyUSB5::INSTR")
        self.assertIn(
            "Automatically discovered SMU",
            window.log_edit.toPlainText(),
        )
        self.assertIn(
            "Automatically discovered LCR meter",
            window.cv_log_edit.toPlainText(),
        )

        window.close()
        QSettings().clear()

    def test_visa_resources_are_not_persisted_in_qsettings(self):
        settings = QSettings()
        for key in MainWindow.VISA_RESOURCE_SETTING_KEYS:
            settings.setValue(key, "ASRL/dev/ttyUSB9::INSTR")

        window = MainWindow()

        self.assertEqual(window.smu_edit.text(), "")
        self.assertEqual(window.pau_edit.text(), "")
        self.assertEqual(window.cv_lcr_edit.text(), "")
        self.assertEqual(window.cv_pau_edit.text(), "")
        self.assertTrue(
            all(
                not settings.contains(key)
                for key in MainWindow.VISA_RESOURCE_SETTING_KEYS
            )
        )

        window.smu_edit.setText("ASRL/dev/ttyUSB0::INSTR")
        window.cv_lcr_edit.setText("ASRL/dev/ttyUSB1::INSTR")
        window._save_settings()
        self.assertTrue(
            all(
                not settings.contains(key)
                for key in MainWindow.VISA_RESOURCE_SETTING_KEYS
            )
        )

        window.close()
        settings.clear()

    def test_channel_window_title_does_not_follow_measurement_mode(self):
        window = MainWindow()
        expected_title = "Measurement channels"

        self.assertEqual(window.channel_window.windowTitle(), expected_title)
        window.measurement_mode_combo.setCurrentIndex(1)
        self.assertEqual(window.channel_window.windowTitle(), expected_title)
        window.measurement_mode_combo.setCurrentIndex(2)
        self.assertEqual(window.channel_window.windowTitle(), expected_title)
        window.measurement_tabs.setCurrentIndex(1)
        self.assertEqual(window.channel_window.windowTitle(), expected_title)

        window.close()

    def test_channel_grid_fits_without_scroll_bars(self):
        window = MainWindow()
        window.channel_window.show()
        self.app.processEvents()

        self.assertEqual(
            window.channel_scroll.horizontalScrollBarPolicy(),
            Qt.ScrollBarAlwaysOff,
        )
        self.assertEqual(
            window.channel_scroll.verticalScrollBarPolicy(),
            Qt.ScrollBarAlwaysOff,
        )
        self.assertGreaterEqual(
            window.channel_scroll.viewport().height(),
            window.channel_grid.minimumSizeHint().height(),
        )

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

    def test_completed_log_only_session_gets_logonly_suffix(self):
        window = MainWindow()

        with tempfile.TemporaryDirectory() as result_path:
            session = Path(result_path) / "IV_ROW_session"
            window._start_file_log(session)
            window._measurement_completed(False, str(session))

            renamed = Path(result_path) / "IV_ROW_session_logonly"
            self.assertFalse(session.exists())
            self.assertTrue(renamed.is_dir())
            self.assertEqual(window._log_file_path.parent, renamed)
            self.assertIn(
                f"Result path: {renamed}",
                window._log_file_path.read_text(encoding="utf-8"),
            )

        window.close()

    def test_session_with_measurement_data_keeps_its_name(self):
        window = MainWindow()

        with tempfile.TemporaryDirectory() as result_path:
            session = Path(result_path) / "CV_session"
            window._start_cv_file_log(session)
            (session / "CV_sensor_row00_col00_v0.txt").write_text(
                "measurement data\n",
                encoding="utf-8",
            )

            kept_path = window._mark_log_only_result(
                session,
                "_cv_log_file_path",
            )

            self.assertEqual(kept_path, str(session))
            self.assertTrue(session.is_dir())
            self.assertFalse(
                (Path(result_path) / "CV_session_logonly").exists()
            )

        window.close()


if __name__ == "__main__":
    unittest.main()
