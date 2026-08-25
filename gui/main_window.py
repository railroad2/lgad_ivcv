import math
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QSettings, QThread, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..ivcv.config import (
    SWITCHING_MATRIX_URI_ENV,
    resolve_result_path,
    resolve_switching_matrix_uri,
)
from .channel_grid import ChannelGrid
from .iv_worker import IVRunConfig, IVWorker


class MainWindow(QMainWindow):
    MODE_LABELS = {
        "channel": ("Channel", "channels"),
        "row": ("Row", "rows"),
        "column": ("Column", "columns"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LGAD IV measurement")
        self.resize(1420, 900)

        self._settings = QSettings()
        self._thread = None
        self._worker = None
        self._plot_voltage = []
        self._plot_pau = []
        self._plot_smu = []
        self._log_file_path = None

        self._build_ui()
        self.measurement_mode_combo.currentIndexChanged.connect(
            self._measurement_mode_changed
        )
        self._load_settings()
        self._measurement_mode_changed()
        self._set_running(False)

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.addLayout(self._build_settings_row())
        root.addWidget(self._build_status_log(), 1)
        root.addLayout(self._build_control_row())

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")
        self.setDockNestingEnabled(True)

        self.channel_dock = self._create_dock(
            "Measurement channels",
            "measurementChannelsDock",
            self._build_channel_panel(),
            Qt.LeftDockWidgetArea,
        )
        self.live_iv_dock = self._create_dock(
            "Live IV",
            "liveIvDock",
            self._build_live_iv_panel(),
            Qt.RightDockWidgetArea,
        )
        self.resizeDocks(
            [self.channel_dock, self.live_iv_dock],
            [760, 600],
            Qt.Horizontal,
        )

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.channel_dock.toggleViewAction())
        view_menu.addAction(self.live_iv_dock.toggleViewAction())

    def _create_dock(self, title, object_name, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(object_name)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _build_settings_row(self):
        row = QHBoxLayout()

        connection = QGroupBox("Instrument connection")
        connection_form = QFormLayout(connection)
        self.port_edit = QLineEdit(resolve_switching_matrix_uri())
        self.smu_edit = QLineEdit()
        self.smu_edit.setPlaceholderText("Leave blank for automatic discovery")
        self.pau_edit = QLineEdit()
        self.pau_edit.setPlaceholderText("Leave blank for automatic discovery")
        self.dry_run_check = QCheckBox("Dry run")
        connection_form.addRow("Switching matrix", self.port_edit)
        connection_form.addRow("SMU VISA resource", self.smu_edit)
        connection_form.addRow("PAU VISA resource", self.pau_edit)
        connection_form.addRow("", self.dry_run_check)

        measurement = QGroupBox("IV measurement settings")
        measurement_form = QFormLayout(measurement)
        self.measurement_mode_combo = QComboBox()
        self.measurement_mode_combo.addItem("Individual channels", "channel")
        self.measurement_mode_combo.addItem("Row-wise", "row")
        self.measurement_mode_combo.addItem("Column-wise", "column")
        self.measurement_mode_combo.setToolTip(
            "Row-wise and Column-wise modes connect all 16 channels in each "
            "selected row or column during one sweep."
        )
        self.sensor_edit = QLineEdit("test")
        self.start_voltage_spin = self._voltage_spin(0.0)
        self.end_voltage_spin = self._voltage_spin(-10.0)
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setDecimals(1)
        self.step_spin.setRange(0.1, 1000.0)
        self.step_spin.setSingleStep(0.1)
        self.step_spin.setValue(1.0)
        self.compliance_edit = QLineEdit("1e-5")
        self.return_sweep_check = QCheckBox("Return sweep toward 0 V")
        measurement_form.addRow("Measurement mode", self.measurement_mode_combo)
        measurement_form.addRow("Sensor name", self.sensor_edit)
        measurement_form.addRow("Start voltage (V)", self.start_voltage_spin)
        measurement_form.addRow("End voltage (V)", self.end_voltage_spin)
        measurement_form.addRow("Voltage step (V)", self.step_spin)
        measurement_form.addRow("Current compliance (A)", self.compliance_edit)
        measurement_form.addRow("", self.return_sweep_check)

        output = QGroupBox("Result storage")
        output_form = QFormLayout(output)
        self.result_path_edit = QLineEdit(resolve_result_path())
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_result_path)
        result_row = QHBoxLayout()
        result_row.addWidget(self.result_path_edit, 1)
        result_row.addWidget(self.browse_button)
        output_form.addRow("Result path", result_row)
        env_path = os.environ.get("IVCV_RESULT_PATH")
        source = "IVCV_RESULT_PATH" if env_path else "Default: ./result"
        output_form.addRow("Initial value source", QLabel(source))

        row.addWidget(connection, 1)
        row.addWidget(measurement, 1)
        row.addWidget(output, 1)
        return row

    @staticmethod
    def _voltage_spin(value):
        spin = QDoubleSpinBox()
        spin.setDecimals(1)
        spin.setRange(-1000.0, 0.0)
        spin.setSingleStep(0.1)
        spin.setValue(value)
        return spin

    def _build_channel_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        controls = QHBoxLayout()
        self.select_all_button = QPushButton("Select all")
        self.clear_all_button = QPushButton("Clear all")
        self.channel_count_label = QLabel("256 selected")
        self.select_all_button.clicked.connect(self.channel_grid_select_all)
        self.clear_all_button.clicked.connect(self.channel_grid_clear_all)
        controls.addWidget(self.select_all_button)
        controls.addWidget(self.clear_all_button)
        controls.addStretch(1)
        controls.addWidget(self.channel_count_label)
        layout.addLayout(controls)

        self.channel_grid = ChannelGrid()
        self.channel_grid.selection_changed.connect(self._channel_selection_changed)
        scroll = QScrollArea()
        scroll.setWidget(self.channel_grid)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)
        return panel

    def channel_grid_select_all(self):
        self.channel_grid.select_all()

    def channel_grid_clear_all(self):
        self.channel_grid.clear_all()

    def _build_live_iv_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("bottom", "Bias voltage", units="V")
        self.plot_widget.setLabel("left", "Current", units="A")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.pau_curve = self.plot_widget.plot(
            pen=pg.mkPen("#3daee9", width=2), name="PAU"
        )
        self.smu_curve = self.plot_widget.plot(
            pen=pg.mkPen("#e6a23c", width=2), name="SMU"
        )
        self.log_scale_check = QCheckBox("Log Y axis (absolute values)")
        self.log_scale_check.toggled.connect(self._refresh_plot)
        layout.addWidget(self.plot_widget, 1)
        layout.addWidget(self.log_scale_check)
        return panel

    def _build_status_log(self):
        log_group = QGroupBox("Status log")
        log_layout = QVBoxLayout(log_group)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.document().setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_edit)
        return log_group

    def _build_control_row(self):
        row = QHBoxLayout()
        self.start_button = QPushButton("Start measurement")
        self.stop_button = QPushButton("Stop measurement / Output Off")
        self.stop_button.setStyleSheet("color: #b00020; font-weight: bold;")
        self.channel_progress = QProgressBar()
        self.point_progress = QProgressBar()
        self.channel_progress.setFormat("Channel %v/%m")
        self.point_progress.setFormat("Sweep %v/%m")
        self.channel_progress.setRange(0, 256)
        self.point_progress.setRange(0, 1)
        self.start_button.clicked.connect(self._start_measurement)
        self.stop_button.clicked.connect(self._stop_measurement)
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        row.addWidget(self.channel_progress, 1)
        row.addWidget(self.point_progress, 1)
        return row

    def _channel_selection_changed(self, count):
        mode = self.measurement_mode_combo.currentData() or "channel"
        plural = self.MODE_LABELS[mode][1]
        self.channel_count_label.setText(f"{count} {plural} selected")

    def _measurement_mode_changed(self, _index=None):
        mode = self.measurement_mode_combo.currentData() or "channel"
        singular, plural = self.MODE_LABELS[mode]
        self.channel_grid.set_selection_mode(mode)
        self.channel_dock.setWindowTitle(f"Measurement {plural}")
        self.channel_progress.setFormat(f"{singular} %v/%m")
        self._channel_selection_changed(
            len(self.channel_grid.selected_targets())
        )

    def _browse_result_path(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select result directory",
            self.result_path_edit.text() or ".",
        )
        if path:
            self.result_path_edit.setText(path)

    @staticmethod
    def _optional_text(widget):
        value = widget.text().strip()
        return value or None

    def _make_config(self):
        port = self.port_edit.text().strip()
        sensor_name = self.sensor_edit.text().strip()
        result_path = self.result_path_edit.text().strip()
        measurement_mode = self.measurement_mode_combo.currentData()
        targets = tuple(self.channel_grid.selected_targets())

        if not port:
            raise ValueError("Enter a switching matrix port.")
        if not sensor_name:
            raise ValueError("Enter a sensor name.")
        if not result_path:
            raise ValueError("Enter a result path.")
        if not targets:
            plural = self.MODE_LABELS[measurement_mode][1]
            raise ValueError(f"Select at least one measurement {plural[:-1]}.")

        try:
            compliance = float(self.compliance_edit.text())
        except ValueError as exc:
            raise ValueError("Current compliance must be numeric.") from exc
        if not math.isfinite(compliance) or compliance <= 0:
            raise ValueError("Current compliance must be a finite positive value.")

        start_voltage = self.start_voltage_spin.value()
        end_voltage = self.end_voltage_spin.value()
        if start_voltage > 0 or end_voltage > 0:
            raise ValueError("IV bias voltage must be 0 V or below.")

        return IVRunConfig(
            port=port,
            smu_resource=self._optional_text(self.smu_edit),
            pau_resource=self._optional_text(self.pau_edit),
            sensor_name=sensor_name,
            result_path=result_path,
            start_voltage=start_voltage,
            end_voltage=end_voltage,
            voltage_step=self.step_spin.value(),
            current_compliance=compliance,
            return_sweep=self.return_sweep_check.isChecked(),
            dry_run=self.dry_run_check.isChecked(),
            measurement_mode=measurement_mode,
            targets=targets,
        )

    def _start_measurement(self):
        try:
            config = self._make_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Check measurement settings", str(exc))
            return

        self._save_settings()
        self._plot_voltage.clear()
        self._plot_pau.clear()
        self._plot_smu.clear()
        self._refresh_plot()
        self.log_edit.clear()
        self.channel_progress.setRange(0, len(config.targets))
        self.channel_progress.setValue(0)
        self.point_progress.setRange(0, 1)
        self.point_progress.setValue(0)

        thread = QThread(self)
        worker = IVWorker(config)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_changed.connect(self.statusBar().showMessage)
        worker.log_message.connect(self._append_log)
        worker.target_started.connect(self._target_started)
        worker.target_completed.connect(self._target_completed)
        worker.point_measured.connect(self._point_measured)
        worker.result_path_ready.connect(self._result_path_ready)
        worker.completed.connect(self._measurement_completed)
        worker.failed.connect(self._measurement_failed)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)

        self._thread = thread
        self._worker = worker
        self._set_running(True)
        plural = self.MODE_LABELS[config.measurement_mode][1]
        self._append_log(
            f"Measurement started: {len(config.targets)} {plural}"
        )
        thread.start()

    def _result_path_ready(self, result_path):
        try:
            self._start_file_log(result_path)
        except OSError as exc:
            self._append_log(f"Cannot create status log: {exc}")
            return
        self._append_log(f"Status log: {self._log_file_path}")

    def _stop_measurement(self):
        if self._worker is None:
            return
        self.stop_button.setEnabled(False)
        self._append_log("Safe stop requested by user.")
        self._worker.request_stop()

    def _target_started(self, mode, target, index, total):
        self._plot_voltage.clear()
        self._plot_pau.clear()
        self._plot_smu.clear()
        self._refresh_plot()
        self.point_progress.setRange(0, 1)
        self.point_progress.setValue(0)
        self.channel_progress.setRange(0, total)
        self.channel_progress.setValue(index)
        singular = self.MODE_LABELS[mode][0]
        self._append_log(
            f"{singular} {target} measurement started ({index + 1}/{total})."
        )

    def _target_completed(self, mode, target, index, total):
        self.channel_progress.setValue(index + 1)
        singular = self.MODE_LABELS[mode][0]
        self._append_log(f"{singular} {target} measurement completed.")

    def _point_measured(
        self,
        mode,
        target,
        voltage,
        current_pau,
        current_smu,
        index,
        total,
    ):
        self._plot_voltage.append(voltage)
        self._plot_pau.append(current_pau)
        self._plot_smu.append(current_smu)
        self.point_progress.setRange(0, max(total, 1))
        self.point_progress.setValue(index)
        self._refresh_plot()
        singular = self.MODE_LABELS[mode][0]
        self.statusBar().showMessage(
            f"{singular} {target}: {voltage:.1f} V, PAU {current_pau:.4g} A, "
            f"SMU {current_smu:.4g} A"
        )

    def _refresh_plot(self):
        pau = np.asarray(self._plot_pau, dtype=float)
        smu = np.asarray(self._plot_smu, dtype=float)
        if self.log_scale_check.isChecked():
            pau = np.abs(pau)
            smu = np.abs(smu)
        self.plot_widget.setLogMode(y=self.log_scale_check.isChecked())
        self.pau_curve.setData(self._plot_voltage, pau)
        self.smu_curve.setData(self._plot_voltage, smu)

    def _measurement_completed(self, stopped, result_path):
        if stopped:
            message = "Measurement stopped safely."
        else:
            message = "All IV measurements completed."
        self._append_log(message)
        self._append_log(f"Result path: {result_path}")
        self.statusBar().showMessage(
            "Measurement stopped safely."
            if stopped
            else "All IV measurements completed."
        )

    def _measurement_failed(self, message):
        self._append_log(f"Measurement failed: {message}")
        self.statusBar().showMessage(
            "Measurement failed — safe output shutdown was attempted."
        )
        QMessageBox.critical(
            self,
            "IV measurement failed",
            f"{message}\n\nAttempted 0 V, output off, and switch off_all.",
        )

    def _thread_finished(self):
        thread = self._thread
        self._worker = None
        self._thread = None
        self._set_running(False)
        if thread is not None:
            thread.deleteLater()

    def _append_log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message.rstrip()}"
        self.log_edit.append(entry)
        if self._log_file_path is not None:
            with self._log_file_path.open("a", encoding="utf-8") as log_file:
                log_file.write(entry + "\n")

    def _start_file_log(self, result_path):
        self._log_file_path = None
        directory = Path(result_path).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")

        version = 0
        while True:
            path = directory / f"IV_GUI_{timestamp}_v{version}.log"
            try:
                path.touch(exist_ok=False)
            except FileExistsError:
                version += 1
                continue
            self._log_file_path = path
            existing_log = self.log_edit.toPlainText()
            if existing_log:
                path.write_text(existing_log + "\n", encoding="utf-8")
            return path

    def _set_running(self, running):
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        for widget in (
            self.port_edit,
            self.smu_edit,
            self.pau_edit,
            self.dry_run_check,
            self.measurement_mode_combo,
            self.sensor_edit,
            self.start_voltage_spin,
            self.end_voltage_spin,
            self.step_spin,
            self.compliance_edit,
            self.return_sweep_check,
            self.result_path_edit,
            self.browse_button,
            self.channel_grid,
            self.select_all_button,
            self.clear_all_button,
        ):
            widget.setEnabled(not running)

    def _load_settings(self):
        if SWITCHING_MATRIX_URI_ENV not in os.environ:
            self.port_edit.setText(
                self._settings.value("iv/port", resolve_switching_matrix_uri())
            )
        self.smu_edit.setText(self._settings.value("iv/smu", ""))
        self.pau_edit.setText(self._settings.value("iv/pau", ""))
        self.sensor_edit.setText(self._settings.value("iv/sensor", "test"))
        self.result_path_edit.setText(
            self._settings.value("iv/result_path", self.result_path_edit.text())
        )
        self.start_voltage_spin.setValue(
            self._settings.value("iv/start_voltage", 0.0, type=float)
        )
        self.end_voltage_spin.setValue(
            self._settings.value("iv/end_voltage", -10.0, type=float)
        )
        self.step_spin.setValue(
            self._settings.value("iv/voltage_step", 1.0, type=float)
        )
        self.compliance_edit.setText(
            self._settings.value("iv/current_compliance", "1e-5")
        )
        self.return_sweep_check.setChecked(
            self._settings.value("iv/return_sweep", False, type=bool)
        )
        self.dry_run_check.setChecked(
            self._settings.value("iv/dry_run", False, type=bool)
        )
        saved_mode = self._settings.value("iv/measurement_mode", "channel")
        mode_index = self.measurement_mode_combo.findData(saved_mode)
        self.measurement_mode_combo.setCurrentIndex(max(mode_index, 0))
        geometry = self._settings.value("gui/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        dock_state = self._settings.value("gui/dock_state")
        if dock_state is not None:
            self.restoreState(dock_state)

    def _save_settings(self):
        self._settings.setValue("iv/port", self.port_edit.text())
        self._settings.setValue("iv/smu", self.smu_edit.text())
        self._settings.setValue("iv/pau", self.pau_edit.text())
        self._settings.setValue("iv/sensor", self.sensor_edit.text())
        self._settings.setValue("iv/result_path", self.result_path_edit.text())
        self._settings.setValue("iv/start_voltage", self.start_voltage_spin.value())
        self._settings.setValue("iv/end_voltage", self.end_voltage_spin.value())
        self._settings.setValue("iv/voltage_step", self.step_spin.value())
        self._settings.setValue("iv/current_compliance", self.compliance_edit.text())
        self._settings.setValue("iv/return_sweep", self.return_sweep_check.isChecked())
        self._settings.setValue("iv/dry_run", self.dry_run_check.isChecked())
        self._settings.setValue(
            "iv/measurement_mode",
            self.measurement_mode_combo.currentData(),
        )
        self._settings.setValue("gui/geometry", self.saveGeometry())
        self._settings.setValue("gui/dock_state", self.saveState())

    def closeEvent(self, event: QCloseEvent):
        if self._worker is not None:
            self._stop_measurement()
            QMessageBox.information(
                self,
                "Stopping measurement",
                "Wait for safe output shutdown before closing the window.",
            )
            event.ignore()
            return
        self._save_settings()
        event.accept()
