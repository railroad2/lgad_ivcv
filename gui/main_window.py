import math
import os

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QSettings, QThread, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
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
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..ivcv.config import resolve_result_path
from .channel_grid import ChannelGrid
from .iv_worker import IVRunConfig, IVWorker


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LGAD IV channel measurement")
        self.resize(1420, 900)

        self._settings = QSettings()
        self._thread = None
        self._worker = None
        self._plot_voltage = []
        self._plot_pau = []
        self._plot_smu = []

        self._build_ui()
        self._load_settings()
        self._set_running(False)

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.addLayout(self._build_settings_row())

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_channel_panel())
        splitter.addWidget(self._build_output_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)
        root.addLayout(self._build_control_row())

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("준비")

    def _build_settings_row(self):
        row = QHBoxLayout()

        connection = QGroupBox("장비 연결")
        connection_form = QFormLayout(connection)
        self.port_edit = QLineEdit("ws://210.119.41.69:8765")
        self.smu_edit = QLineEdit()
        self.smu_edit.setPlaceholderText("비워 두면 자동 검색")
        self.pau_edit = QLineEdit()
        self.pau_edit.setPlaceholderText("비워 두면 자동 검색")
        self.dry_run_check = QCheckBox("Dry run")
        connection_form.addRow("Switching matrix", self.port_edit)
        connection_form.addRow("SMU VISA resource", self.smu_edit)
        connection_form.addRow("PAU VISA resource", self.pau_edit)
        connection_form.addRow("", self.dry_run_check)

        measurement = QGroupBox("IV 측정 설정")
        measurement_form = QFormLayout(measurement)
        self.sensor_edit = QLineEdit("test")
        self.start_voltage_spin = self._voltage_spin(0.0)
        self.end_voltage_spin = self._voltage_spin(-10.0)
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setDecimals(4)
        self.step_spin.setRange(0.0001, 1000.0)
        self.step_spin.setValue(1.0)
        self.compliance_edit = QLineEdit("1e-5")
        self.return_sweep_check = QCheckBox("0 V 방향 return sweep 수행")
        measurement_form.addRow("Sensor name", self.sensor_edit)
        measurement_form.addRow("Start voltage (V)", self.start_voltage_spin)
        measurement_form.addRow("End voltage (V)", self.end_voltage_spin)
        measurement_form.addRow("Voltage step (V)", self.step_spin)
        measurement_form.addRow("Current compliance (A)", self.compliance_edit)
        measurement_form.addRow("", self.return_sweep_check)

        output = QGroupBox("결과 저장")
        output_form = QFormLayout(output)
        self.result_path_edit = QLineEdit(resolve_result_path())
        self.browse_button = QPushButton("폴더 선택...")
        self.browse_button.clicked.connect(self._browse_result_path)
        result_row = QHBoxLayout()
        result_row.addWidget(self.result_path_edit, 1)
        result_row.addWidget(self.browse_button)
        output_form.addRow("Result path", result_row)
        env_path = os.environ.get("IVCV_RESULT_PATH")
        source = "IVCV_RESULT_PATH" if env_path else "기본값 ./result"
        output_form.addRow("초기값 출처", QLabel(source))

        row.addWidget(connection, 1)
        row.addWidget(measurement, 1)
        row.addWidget(output, 1)
        return row

    @staticmethod
    def _voltage_spin(value):
        spin = QDoubleSpinBox()
        spin.setDecimals(4)
        spin.setRange(-1000.0, 0.0)
        spin.setValue(value)
        return spin

    def _build_channel_panel(self):
        group = QGroupBox("측정 채널")
        layout = QVBoxLayout(group)

        controls = QHBoxLayout()
        self.select_all_button = QPushButton("전체 선택")
        self.clear_all_button = QPushButton("전체 해제")
        self.channel_count_label = QLabel("256개 선택")
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
        return group

    def channel_grid_select_all(self):
        self.channel_grid.select_all()

    def channel_grid_clear_all(self):
        self.channel_grid.clear_all()

    def _build_output_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        graph_group = QGroupBox("실시간 IV")
        graph_layout = QVBoxLayout(graph_group)
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
        self.log_scale_check = QCheckBox("Y축 log (절댓값)")
        self.log_scale_check.toggled.connect(self._refresh_plot)
        graph_layout.addWidget(self.plot_widget, 1)
        graph_layout.addWidget(self.log_scale_check)

        log_group = QGroupBox("상태 로그")
        log_layout = QVBoxLayout(log_group)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.document().setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_edit)

        layout.addWidget(graph_group, 3)
        layout.addWidget(log_group, 2)
        return widget

    def _build_control_row(self):
        row = QHBoxLayout()
        self.start_button = QPushButton("측정 시작")
        self.stop_button = QPushButton("측정 중단 / Output Off")
        self.stop_button.setStyleSheet("color: #b00020; font-weight: bold;")
        self.channel_progress = QProgressBar()
        self.point_progress = QProgressBar()
        self.channel_progress.setFormat("채널 %v/%m")
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
        self.channel_count_label.setText(f"{count}개 선택")

    def _browse_result_path(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "결과 저장 폴더",
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
        channels = tuple(self.channel_grid.selected_channels())

        if not port:
            raise ValueError("Switching matrix port를 입력해 주세요.")
        if not sensor_name:
            raise ValueError("Sensor name을 입력해 주세요.")
        if not result_path:
            raise ValueError("Result path를 입력해 주세요.")
        if not channels:
            raise ValueError("측정할 채널을 하나 이상 선택해 주세요.")

        try:
            compliance = float(self.compliance_edit.text())
        except ValueError as exc:
            raise ValueError("Current compliance는 숫자여야 합니다.") from exc
        if not math.isfinite(compliance) or compliance <= 0:
            raise ValueError("Current compliance는 유한한 양수여야 합니다.")

        start_voltage = self.start_voltage_spin.value()
        end_voltage = self.end_voltage_spin.value()
        if start_voltage > 0 or end_voltage > 0:
            raise ValueError("IV bias voltage는 0 V 이하여야 합니다.")

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
            channels=channels,
        )

    def _start_measurement(self):
        try:
            config = self._make_config()
        except ValueError as exc:
            QMessageBox.warning(self, "측정 설정 확인", str(exc))
            return

        self._save_settings()
        self._plot_voltage.clear()
        self._plot_pau.clear()
        self._plot_smu.clear()
        self._refresh_plot()
        self.log_edit.clear()
        self.channel_progress.setRange(0, len(config.channels))
        self.channel_progress.setValue(0)
        self.point_progress.setRange(0, 1)
        self.point_progress.setValue(0)

        thread = QThread(self)
        worker = IVWorker(config)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_changed.connect(self.statusBar().showMessage)
        worker.log_message.connect(self._append_log)
        worker.channel_started.connect(self._channel_started)
        worker.channel_completed.connect(self._channel_completed)
        worker.point_measured.connect(self._point_measured)
        worker.completed.connect(self._measurement_completed)
        worker.failed.connect(self._measurement_failed)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)

        self._thread = thread
        self._worker = worker
        self._set_running(True)
        self._append_log(f"측정 시작: {len(config.channels)}개 채널")
        thread.start()

    def _stop_measurement(self):
        if self._worker is None:
            return
        self.stop_button.setEnabled(False)
        self._append_log("사용자가 안전 중단을 요청했습니다.")
        self._worker.request_stop()

    def _channel_started(self, channel, index, total):
        self._plot_voltage.clear()
        self._plot_pau.clear()
        self._plot_smu.clear()
        self._refresh_plot()
        self.point_progress.setRange(0, 1)
        self.point_progress.setValue(0)
        self.channel_progress.setRange(0, total)
        self.channel_progress.setValue(index)
        self._append_log(f"채널 {channel} 측정 시작 ({index + 1}/{total})")

    def _channel_completed(self, channel, index, total):
        self.channel_progress.setValue(index + 1)
        self._append_log(f"채널 {channel} 측정 완료")

    def _point_measured(self, channel, voltage, current_pau, current_smu, index, total):
        self._plot_voltage.append(voltage)
        self._plot_pau.append(current_pau)
        self._plot_smu.append(current_smu)
        self.point_progress.setRange(0, max(total, 1))
        self.point_progress.setValue(index)
        self._refresh_plot()
        self.statusBar().showMessage(
            f"채널 {channel}: {voltage:g} V, PAU {current_pau:.4g} A, "
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
            message = "측정이 안전하게 중단되었습니다."
        else:
            message = "모든 IV 측정이 완료되었습니다."
        self._append_log(message)
        self._append_log(f"결과 위치: {result_path}")
        self.statusBar().showMessage(message)

    def _measurement_failed(self, message):
        self._append_log(f"측정 실패: {message}")
        self.statusBar().showMessage("측정 실패 — 출력 안전 종료를 수행했습니다.")
        QMessageBox.critical(
            self,
            "IV 측정 실패",
            f"{message}\n\n0 V, output off 및 switch off_all을 시도했습니다.",
        )

    def _thread_finished(self):
        thread = self._thread
        self._worker = None
        self._thread = None
        self._set_running(False)
        if thread is not None:
            thread.deleteLater()

    def _append_log(self, message):
        self.log_edit.append(message.rstrip())

    def _set_running(self, running):
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        for widget in (
            self.port_edit,
            self.smu_edit,
            self.pau_edit,
            self.dry_run_check,
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
        self.port_edit.setText(self._settings.value("iv/port", self.port_edit.text()))
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

    def closeEvent(self, event: QCloseEvent):
        if self._worker is not None:
            self._stop_measurement()
            QMessageBox.information(
                self,
                "측정 중단 중",
                "출력을 안전하게 종료한 뒤 창을 닫아 주세요.",
            )
            event.ignore()
            return
        self._save_settings()
        event.accept()
