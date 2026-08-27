import math
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QSettings, QThread, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
    QSizePolicy,
    QStatusBar,
    QTabWidget,
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
from .cv_worker import CVRunConfig, CVWorker
from .instrument_finder import InstrumentFinder
from .iv_worker import IVRunConfig, IVWorker
from .matrix_monitor import MatrixConnectionMonitor


class MainWindow(QMainWindow):
    VISA_RESOURCE_SETTING_KEYS = ("iv/smu", "iv/pau", "cv/lcr", "cv/pau")
    MODE_LABELS = {
        "channel": ("Channel", "channels"),
        "row": ("Row", "rows"),
        "column": ("Column", "columns"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LGAD IV/CV measurement")
        self.resize(770, 700)

        self._settings = QSettings()
        self._thread = None
        self._worker = None
        self._active_measurement = None
        self._plot_voltage = []
        self._plot_pau = []
        self._plot_smu = []
        self._cv_plot_voltage = []
        self._cv_plot_capacitance = []
        self._cv_plot_resistance = []
        self._log_file_path = None
        self._cv_log_file_path = None
        self._channel_window_shown = False
        self._matrix_monitors = []
        self._instrument_search = None

        self._build_ui()
        self.measurement_mode_combo.currentIndexChanged.connect(
            self._measurement_mode_changed
        )
        self.cv_measurement_mode_combo.currentIndexChanged.connect(
            self._cv_measurement_mode_changed
        )
        self.measurement_mode_combo.currentIndexChanged.connect(
            self.cv_measurement_mode_combo.setCurrentIndex
        )
        self.cv_measurement_mode_combo.currentIndexChanged.connect(
            self.measurement_mode_combo.setCurrentIndex
        )
        self.sensor_edit.textChanged.connect(self.cv_sensor_edit.setText)
        self.cv_sensor_edit.textChanged.connect(self.sensor_edit.setText)
        self.result_path_edit.textChanged.connect(self.cv_result_path_edit.setText)
        self.cv_result_path_edit.textChanged.connect(self.result_path_edit.setText)
        self.result_path_edit.textChanged.connect(self._update_output_paths)
        self.sensor_edit.textChanged.connect(self._update_output_paths)
        self.cv_sensor_edit.textChanged.connect(self._update_output_paths)
        self.port_edit.textChanged.connect(self._iv_matrix_address_changed)
        self.cv_port_edit.textChanged.connect(self._cv_matrix_address_changed)
        self.measurement_tabs.currentChanged.connect(self._measurement_tab_changed)
        self._load_settings()
        self._update_output_paths()
        self._measurement_tab_changed(self.measurement_tabs.currentIndex())
        self._set_running(False)
        self._start_matrix_monitors()

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)

        self.measurement_tabs = QTabWidget()
        self.measurement_tabs.setStyleSheet(
            "QTabBar::tab { min-width: 120px; }"
        )
        self.measurement_tabs.addTab(self._build_iv_tab(), "I-V")
        self.measurement_tabs.addTab(self._build_cv_tab(), "C-V")
        self.measurement_tabs.setCurrentIndex(0)
        root.addWidget(self.measurement_tabs)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        self.channel_window = self._create_auxiliary_window(
            "Measurement channels", self._build_channel_panel(), 575, 540
        )
        self.live_iv_window = self._create_auxiliary_window(
            "Live IV", self._build_live_iv_panel(), 760, 600
        )
        self.live_cv_window = self._create_auxiliary_window(
            "Live CV", self._build_live_cv_panel(), 760, 700
        )

        file_menu = self.menuBar().addMenu("File")
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction("Measurement channels", self._show_channel_window)
        view_menu.addAction("Live IV", self._show_live_iv_window)
        view_menu.addAction("Live CV", self._show_live_cv_window)

    def _build_iv_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addLayout(self._build_settings_row())
        layout.addWidget(self._build_status_log(), 1)
        layout.addLayout(self._build_control_row())
        return tab

    def _build_cv_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addLayout(self._build_cv_settings())
        layout.addWidget(self._build_cv_status_log(), 1)
        layout.addLayout(self._build_cv_control_row())
        return tab

    def _build_cv_settings(self):
        settings = QVBoxLayout()
        top_row = QHBoxLayout()

        connection = QWidget()
        connection_layout = QVBoxLayout(connection)
        connection_layout.setContentsMargins(0, 0, 0, 0)

        switching_matrix = QGroupBox("Switching matrix")
        switching_matrix_form = QFormLayout(switching_matrix)
        self.cv_port_edit = QLineEdit(resolve_switching_matrix_uri())
        self.cv_matrix_status_label = self._matrix_status_label()
        switching_matrix_form.addRow("WebSocket address", self.cv_port_edit)
        switching_matrix_form.addRow("Status", self.cv_matrix_status_label)

        instruments = QGroupBox("Instruments")
        instruments_form = QFormLayout(instruments)
        self.cv_lcr_edit = QLineEdit()
        self.cv_lcr_edit.setPlaceholderText("Leave blank for automatic discovery")
        self.cv_lcr_find_button = QPushButton("Find")
        self.cv_lcr_find_button.setFixedWidth(55)
        self.cv_lcr_find_button.clicked.connect(self._find_cv_lcr)
        self.cv_pau_edit = QLineEdit()
        self.cv_pau_edit.setPlaceholderText("Optional external bias source")
        self.cv_pau_find_button = QPushButton("Find")
        self.cv_pau_find_button.setFixedWidth(55)
        self.cv_pau_find_button.clicked.connect(self._find_cv_pau)
        self.cv_dry_run_check = QCheckBox("Dry run")
        cv_lcr_row = QHBoxLayout()
        cv_lcr_row.addWidget(self.cv_lcr_edit, 1)
        cv_lcr_row.addWidget(self.cv_lcr_find_button)
        cv_pau_row = QHBoxLayout()
        cv_pau_row.addWidget(self.cv_pau_edit, 1)
        cv_pau_row.addWidget(self.cv_pau_find_button)
        instruments_form.addRow("LCR VISA resource", cv_lcr_row)
        instruments_form.addRow("PAU VISA resource", cv_pau_row)
        instruments_form.addRow("", self.cv_dry_run_check)

        connection_layout.addWidget(switching_matrix)
        connection_layout.addWidget(instruments)
        connection_layout.addStretch(1)

        measurement = QGroupBox("CV measurement settings")
        measurement_form = QFormLayout(measurement)
        self.cv_measurement_mode_combo = QComboBox()
        self.cv_measurement_mode_combo.addItem("Individual channels", "channel")
        self.cv_measurement_mode_combo.addItem("Row-wise", "row")
        self.cv_measurement_mode_combo.addItem("Column-wise", "column")
        self.cv_measurement_mode_combo.setToolTip(
            "Row-wise and Column-wise modes connect all 16 channels in each "
            "selected row or column during one sweep."
        )
        self.cv_sensor_edit = QLineEdit("test")
        self.cv_open_channels_button = QPushButton("Select channels...")
        self.cv_open_channels_button.clicked.connect(self._show_channel_window)
        self.cv_selection_summary_label = QLabel()
        channel_row = QHBoxLayout()
        channel_row.addWidget(self.cv_open_channels_button)
        channel_row.addWidget(self.cv_selection_summary_label, 1)
        self.cv_start_voltage_spin = self._voltage_spin(0.0)
        self.cv_end_voltage_spin = self._voltage_spin(-10.0)
        self.cv_step_spin = QDoubleSpinBox()
        self.cv_step_spin.setDecimals(1)
        self.cv_step_spin.setRange(0.1, 1000.0)
        self.cv_step_spin.setSingleStep(0.1)
        self.cv_step_spin.setValue(1.0)
        self.cv_ac_level_spin = QDoubleSpinBox()
        self.cv_ac_level_spin.setDecimals(3)
        self.cv_ac_level_spin.setRange(0.001, 10.0)
        self.cv_ac_level_spin.setSingleStep(0.01)
        self.cv_ac_level_spin.setValue(0.1)
        self.cv_frequency_spin = QDoubleSpinBox()
        self.cv_frequency_spin.setDecimals(0)
        self.cv_frequency_spin.setRange(1.0, 10_000_000.0)
        self.cv_frequency_spin.setSingleStep(100.0)
        self.cv_frequency_spin.setValue(1000.0)
        self.cv_return_sweep_check = QCheckBox("Return sweep toward 0 V")
        measurement_form.addRow("Measurement mode", self.cv_measurement_mode_combo)
        measurement_form.addRow("Measurement targets", channel_row)
        measurement_form.addRow("Sensor name", self.cv_sensor_edit)
        measurement_form.addRow("Start voltage (V)", self.cv_start_voltage_spin)
        measurement_form.addRow("End voltage (V)", self.cv_end_voltage_spin)
        measurement_form.addRow("Voltage step (V)", self.cv_step_spin)
        measurement_form.addRow("AC level (V)", self.cv_ac_level_spin)
        measurement_form.addRow("Frequency (Hz)", self.cv_frequency_spin)
        measurement_form.addRow("", self.cv_return_sweep_check)

        output = QGroupBox("Result path")
        output_form = QFormLayout(output)
        self.cv_result_path_edit = QLineEdit(resolve_result_path())
        self.cv_browse_button = QPushButton("Browse...")
        self.cv_browse_button.clicked.connect(self._browse_cv_result_path)
        result_row = QHBoxLayout()
        result_row.addWidget(self.cv_result_path_edit, 1)
        result_row.addWidget(self.cv_browse_button)
        output_form.addRow("Base path", result_row)
        self.cv_output_path_label = QLabel()
        self.cv_output_path_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        self.cv_output_path_label.setWordWrap(True)
        self.cv_output_path_label.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Preferred,
        )
        output_form.addRow("Output path", self.cv_output_path_label)

        top_row.addWidget(connection, 1)
        top_row.addWidget(measurement, 1)
        settings.addLayout(top_row)
        settings.addWidget(output)
        return settings

    def _build_cv_status_log(self):
        log_group = QGroupBox("Status log")
        log_layout = QVBoxLayout(log_group)
        self.cv_log_edit = QTextEdit()
        self.cv_log_edit.setReadOnly(True)
        self.cv_log_edit.document().setMaximumBlockCount(1000)
        log_layout.addWidget(self.cv_log_edit)
        return log_group

    def _build_cv_control_row(self):
        row = QHBoxLayout()
        self.cv_start_button = QPushButton("Start measurement")
        self.cv_stop_button = QPushButton("Stop measurement")
        self.cv_stop_button.setStyleSheet("color: #b00020; font-weight: bold;")
        self.cv_channel_progress = QProgressBar()
        self.cv_point_progress = QProgressBar()
        self.cv_channel_progress.setFormat("Channel %v/%m")
        self.cv_point_progress.setFormat("Sweep %v/%m")
        self.cv_channel_progress.setRange(0, 256)
        self.cv_point_progress.setRange(0, 1)
        self.cv_start_button.clicked.connect(self._start_cv_measurement)
        self.cv_stop_button.clicked.connect(self._stop_cv_measurement)
        row.addWidget(self.cv_start_button)
        row.addWidget(self.cv_stop_button)
        row.addWidget(self.cv_channel_progress, 1)
        row.addWidget(self.cv_point_progress, 1)
        return row

    def _create_auxiliary_window(self, title, content, width, height):
        window = QWidget(self, Qt.Window)
        window.setWindowTitle(title)
        window.setAttribute(Qt.WA_QuitOnClose, False)
        layout = QVBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)
        window.resize(width, height)
        return window

    @staticmethod
    def _show_window(window):
        window.show()
        window.raise_()
        window.activateWindow()

    def _show_channel_window(self):
        self._show_window(self.channel_window)

    def _show_live_iv_window(self):
        self._show_window(self.live_iv_window)

    def _show_live_cv_window(self):
        self._show_window(self.live_cv_window)

    def _build_settings_row(self):
        settings = QVBoxLayout()
        top_row = QHBoxLayout()

        connection = QWidget()
        connection_layout = QVBoxLayout(connection)
        connection_layout.setContentsMargins(0, 0, 0, 0)

        switching_matrix = QGroupBox("Switching matrix")
        switching_matrix_form = QFormLayout(switching_matrix)
        self.port_edit = QLineEdit(resolve_switching_matrix_uri())
        self.matrix_status_label = self._matrix_status_label()
        switching_matrix_form.addRow("WebSocket address", self.port_edit)
        switching_matrix_form.addRow("Status", self.matrix_status_label)

        instruments = QGroupBox("Instruments")
        instruments_form = QFormLayout(instruments)
        self.smu_edit = QLineEdit()
        self.smu_edit.setPlaceholderText("Leave blank for automatic discovery")
        self.smu_find_button = QPushButton("Find")
        self.smu_find_button.setFixedWidth(55)
        self.smu_find_button.clicked.connect(self._find_iv_smu)
        self.pau_edit = QLineEdit()
        self.pau_edit.setPlaceholderText("Leave blank for automatic discovery")
        self.pau_find_button = QPushButton("Find")
        self.pau_find_button.setFixedWidth(55)
        self.pau_find_button.clicked.connect(self._find_iv_pau)
        self.dry_run_check = QCheckBox("Dry run")
        smu_row = QHBoxLayout()
        smu_row.addWidget(self.smu_edit, 1)
        smu_row.addWidget(self.smu_find_button)
        pau_row = QHBoxLayout()
        pau_row.addWidget(self.pau_edit, 1)
        pau_row.addWidget(self.pau_find_button)
        instruments_form.addRow("SMU VISA resource", smu_row)
        instruments_form.addRow("PAU VISA resource", pau_row)
        instruments_form.addRow("", self.dry_run_check)

        connection_layout.addWidget(switching_matrix)
        connection_layout.addWidget(instruments)
        connection_layout.addStretch(1)

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
        self.open_channels_button = QPushButton("Select channels...")
        self.open_channels_button.clicked.connect(self._show_channel_window)
        self.selection_summary_label = QLabel()
        channel_row = QHBoxLayout()
        channel_row.addWidget(self.open_channels_button)
        channel_row.addWidget(self.selection_summary_label, 1)
        measurement_form.addRow("Measurement targets", channel_row)
        measurement_form.addRow("Sensor name", self.sensor_edit)
        measurement_form.addRow("Start voltage (V)", self.start_voltage_spin)
        measurement_form.addRow("End voltage (V)", self.end_voltage_spin)
        measurement_form.addRow("Voltage step (V)", self.step_spin)
        measurement_form.addRow("Current compliance (A)", self.compliance_edit)
        measurement_form.addRow("", self.return_sweep_check)

        output = QGroupBox("Result path")
        output_form = QFormLayout(output)
        self.result_path_edit = QLineEdit(resolve_result_path())
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_result_path)
        result_row = QHBoxLayout()
        result_row.addWidget(self.result_path_edit, 1)
        result_row.addWidget(self.browse_button)
        output_form.addRow("Base path", result_row)
        self.output_path_label = QLabel()
        self.output_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.output_path_label.setWordWrap(True)
        self.output_path_label.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Preferred,
        )
        output_form.addRow("Output path", self.output_path_label)

        top_row.addWidget(connection, 1)
        top_row.addWidget(measurement, 1)
        settings.addLayout(top_row)
        settings.addWidget(output)
        return settings

    @classmethod
    def _matrix_status_label(cls):
        label = QLabel()
        cls._set_matrix_status(label, "Disconnected")
        return label

    @staticmethod
    def _set_matrix_status(label, status):
        colors = {
            "Connected": "#18763a",
            "Checking...": "#9a6700",
            "Disconnected": "#666666",
        }
        label.setText(status)
        label.setStyleSheet(
            f"color: {colors.get(status, '#666666')}; font-weight: bold;"
        )

    def _set_iv_matrix_status(self, status):
        self._set_matrix_status(self.matrix_status_label, status)

    def _set_cv_matrix_status(self, status):
        self._set_matrix_status(self.cv_matrix_status_label, status)

    def _start_matrix_monitors(self):
        specifications = (
            (self.port_edit, self._set_iv_monitored_status),
            (self.cv_port_edit, self._set_cv_monitored_status),
        )
        for address_edit, status_slot in specifications:
            monitor = MatrixConnectionMonitor(address_edit.text())
            monitor.status_changed.connect(status_slot, Qt.QueuedConnection)
            self._matrix_monitors.append(monitor)
            monitor.start()

    def _set_iv_monitored_status(self, address, status):
        if address.strip() == self.port_edit.text().strip():
            self._set_iv_matrix_status(status)

    def _set_cv_monitored_status(self, address, status):
        if address.strip() == self.cv_port_edit.text().strip():
            self._set_cv_matrix_status(status)

    def _iv_matrix_address_changed(self, address):
        self._set_iv_matrix_status("Checking...")
        if self._matrix_monitors:
            self._matrix_monitors[0].set_control_uri(address)

    def _cv_matrix_address_changed(self, address):
        self._set_cv_matrix_status("Checking...")
        if len(self._matrix_monitors) > 1:
            self._matrix_monitors[1].set_control_uri(address)

    def _stop_matrix_monitors(self):
        for monitor in self._matrix_monitors:
            monitor.request_stop()
        for monitor in self._matrix_monitors:
            monitor.stop()
        self._matrix_monitors.clear()

    def _instrument_search_specification(self, key):
        return {
            "iv_smu": ("smu", "SMU", self.smu_edit, self._append_log),
            "iv_pau": ("pau", "PAU", self.pau_edit, self._append_log),
            "cv_lcr": ("lcr", "LCR meter", self.cv_lcr_edit, self._append_cv_log),
            "cv_pau": ("pau", "PAU", self.cv_pau_edit, self._append_cv_log),
        }[key]

    def _instrument_find_buttons(self):
        return (
            self.smu_find_button,
            self.pau_find_button,
            self.cv_lcr_find_button,
            self.cv_pau_find_button,
        )

    def _find_iv_smu(self):
        self._start_instrument_search("iv_smu")

    def _find_iv_pau(self):
        self._start_instrument_search("iv_pau")

    def _find_cv_lcr(self):
        self._start_instrument_search("cv_lcr")

    def _find_cv_pau(self):
        self._start_instrument_search("cv_pau")

    def _start_instrument_search(self, key):
        if self._worker is not None or self._instrument_search is not None:
            return

        instrument_type, name, _field, logger = (
            self._instrument_search_specification(key)
        )
        logger(f"Searching for {name} VISA resource...")
        self.statusBar().showMessage(f"Searching for {name} VISA resource...")
        for button in self._instrument_find_buttons():
            button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.cv_start_button.setEnabled(False)

        finder = InstrumentFinder(instrument_type, self)
        finder.search_key = key
        finder.found.connect(self._instrument_found_from_search)
        finder.not_found.connect(self._instrument_not_found_from_search)
        finder.failed.connect(self._instrument_find_failed_from_search)
        finder.finished.connect(self._instrument_search_finished)

        self._instrument_search = finder
        finder.start()

    def _instrument_found_from_search(self, resource, device_name):
        self._instrument_found(
            self.sender().search_key,
            resource,
            device_name,
        )

    def _instrument_not_found_from_search(self):
        self._instrument_not_found(self.sender().search_key)

    def _instrument_find_failed_from_search(self, message):
        self._instrument_find_failed(self.sender().search_key, message)

    def _instrument_found(self, key, resource, device_name=""):
        _instrument_type, name, field, logger = (
            self._instrument_search_specification(key)
        )
        field.setText(resource)
        logger(f"Found {name}: {resource}")
        if device_name:
            logger(f"Instrument identity: {device_name}")
        self.statusBar().showMessage(f"Found {name}: {resource}")

    def _instrument_not_found(self, key):
        _instrument_type, name, _field, logger = (
            self._instrument_search_specification(key)
        )
        message = f"No compatible {name} VISA resource was found."
        logger(message)
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "Instrument not found", message)

    def _instrument_find_failed(self, key, error):
        _instrument_type, name, _field, logger = (
            self._instrument_search_specification(key)
        )
        message = f"Failed to search for {name}: {error}"
        logger(message)
        self.statusBar().showMessage(message)
        QMessageBox.critical(self, "Instrument search failed", message)

    def _instrument_search_finished(self):
        search = self._instrument_search
        self._instrument_search = None
        if search is not None:
            search.deleteLater()
        if self._worker is None:
            self.start_button.setEnabled(True)
            self.cv_start_button.setEnabled(True)
            for button in self._instrument_find_buttons():
                button.setEnabled(True)

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
        self.channel_scroll = QScrollArea()
        self.channel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.channel_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.channel_scroll.setWidget(self.channel_grid)
        self.channel_scroll.setWidgetResizable(True)
        layout.addWidget(self.channel_scroll, 1)
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

    def _build_live_cv_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.cv_capacitance_plot = pg.PlotWidget()
        self.cv_capacitance_plot.setLabel("bottom", "Bias voltage", units="V")
        self.cv_capacitance_plot.setLabel("left", "Capacitance", units="pF")
        self.cv_capacitance_plot.showGrid(x=True, y=True, alpha=0.3)
        self.cv_capacitance_curve = self.cv_capacitance_plot.plot(
            pen=pg.mkPen("#3daee9", width=2), symbol="o", symbolSize=5
        )
        self.cv_resistance_plot = pg.PlotWidget()
        self.cv_resistance_plot.setLabel("bottom", "Bias voltage", units="V")
        self.cv_resistance_plot.setLabel("left", "Resistance", units="Ohm")
        self.cv_resistance_plot.showGrid(x=True, y=True, alpha=0.3)
        self.cv_resistance_plot.setLogMode(y=True)
        self.cv_resistance_curve = self.cv_resistance_plot.plot(
            pen=pg.mkPen("#e6a23c", width=2), symbol="o", symbolSize=5
        )
        layout.addWidget(self.cv_capacitance_plot, 1)
        layout.addWidget(self.cv_resistance_plot, 1)
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
        self.stop_button = QPushButton("Stop measurement")
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

    def _channel_selection_changed(self, _count=None):
        mode = self.measurement_mode_combo.currentData() or "channel"
        plural = self.MODE_LABELS[mode][1]
        count = len(self.channel_grid.selected_targets())
        selection_text = f"{count} {plural} selected"
        self.channel_count_label.setText(selection_text)
        self.selection_summary_label.setText(selection_text)
        self.cv_selection_summary_label.setText(selection_text)

    def _measurement_mode_changed(self, _index=None):
        if self.measurement_tabs.currentIndex() != 0:
            return
        mode = self.measurement_mode_combo.currentData() or "channel"
        singular, plural = self.MODE_LABELS[mode]
        self.channel_grid.set_selection_mode(mode)
        self.channel_progress.setFormat(f"{singular} %v/%m")
        self._channel_selection_changed(
            len(self.channel_grid.selected_targets())
        )

    def _cv_measurement_mode_changed(self, _index=None):
        if self.measurement_tabs.currentIndex() != 1:
            return
        mode = self.cv_measurement_mode_combo.currentData() or "channel"
        singular, _plural = self.MODE_LABELS[mode]
        self.channel_grid.set_selection_mode(mode)
        self.cv_channel_progress.setFormat(f"{singular} %v/%m")
        self._channel_selection_changed(
            len(self.channel_grid.selected_targets())
        )

    def _measurement_tab_changed(self, index):
        if index == 1:
            self._cv_measurement_mode_changed()
        else:
            self._measurement_mode_changed()

    @staticmethod
    def _sensor_output_path(base_path, sensor_name):
        sensor_directory = sensor_name.split(",", 1)[0]
        return str(
            Path(base_path).expanduser()
            / datetime.now().strftime("%Y-%m-%d")
            / sensor_directory
        )

    def _update_output_paths(self, _value=None):
        base_path = self.result_path_edit.text().strip() or "."
        self.output_path_label.setText(
            self._sensor_output_path(base_path, self.sensor_edit.text().strip())
        )
        self.cv_output_path_label.setText(
            self._sensor_output_path(
                base_path,
                self.cv_sensor_edit.text().strip(),
            )
        )

    def _browse_result_path(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select result directory",
            self.result_path_edit.text() or ".",
        )
        if path:
            self.result_path_edit.setText(path)

    def _browse_cv_result_path(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select result directory",
            self.cv_result_path_edit.text() or ".",
        )
        if path:
            self.cv_result_path_edit.setText(path)

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

    def _make_cv_config(self):
        port = self.cv_port_edit.text().strip()
        sensor_name = self.cv_sensor_edit.text().strip()
        result_path = self.cv_result_path_edit.text().strip()
        measurement_mode = self.cv_measurement_mode_combo.currentData()
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

        start_voltage = self.cv_start_voltage_spin.value()
        end_voltage = self.cv_end_voltage_spin.value()
        if start_voltage > 0 or end_voltage > 0:
            raise ValueError("CV bias voltage must be 0 V or below.")
        pau_resource = self._optional_text(self.cv_pau_edit)
        if pau_resource is None and min(start_voltage, end_voltage) < -40:
            raise ValueError(
                "The LCR internal bias is limited to -40 V. "
                "Enter a PAU resource for a larger negative bias."
            )

        return CVRunConfig(
            port=port,
            lcr_resource=self._optional_text(self.cv_lcr_edit),
            pau_resource=pau_resource,
            sensor_name=sensor_name,
            result_path=result_path,
            start_voltage=start_voltage,
            end_voltage=end_voltage,
            voltage_step=self.cv_step_spin.value(),
            ac_level=self.cv_ac_level_spin.value(),
            frequency=self.cv_frequency_spin.value(),
            return_sweep=self.cv_return_sweep_check.isChecked(),
            dry_run=self.cv_dry_run_check.isChecked(),
            measurement_mode=measurement_mode,
            targets=targets,
        )

    def _start_measurement(self):
        if self._worker is not None:
            return
        try:
            config = self._make_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Check measurement settings", str(exc))
            return

        self._update_output_paths()
        self._save_settings()
        self._plot_voltage.clear()
        self._plot_pau.clear()
        self._plot_smu.clear()
        self._refresh_plot()
        self._log_file_path = None
        self.log_edit.clear()
        self.channel_progress.setRange(0, len(config.targets))
        self.channel_progress.setValue(0)
        self.point_progress.setRange(0, 1)
        self.point_progress.setValue(0)
        self.channel_grid.clear_completed()

        thread = QThread(self)
        worker = IVWorker(config)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_changed.connect(self.statusBar().showMessage)
        worker.log_message.connect(self._append_log)
        worker.target_started.connect(self._target_started)
        worker.target_completed.connect(self._target_completed)
        worker.point_measured.connect(self._point_measured)
        worker.instrument_resource_resolved.connect(
            self._iv_instrument_resource_resolved
        )
        worker.result_path_ready.connect(self._result_path_ready)
        worker.completed.connect(self._measurement_completed)
        worker.failed.connect(self._measurement_failed)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)

        self._thread = thread
        self._worker = worker
        self._active_measurement = "iv"
        self._set_running(True, "iv")
        self._show_live_iv_window()
        plural = self.MODE_LABELS[config.measurement_mode][1]
        self._append_log(
            f"Measurement started: {len(config.targets)} {plural}"
        )
        thread.start()

    def _start_cv_measurement(self):
        if self._worker is not None:
            return
        try:
            config = self._make_cv_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Check CV measurement settings", str(exc))
            return

        self._update_output_paths()
        self._save_settings()
        self._cv_plot_voltage.clear()
        self._cv_plot_capacitance.clear()
        self._cv_plot_resistance.clear()
        self._refresh_cv_plot()
        self._cv_log_file_path = None
        self.cv_log_edit.clear()
        self.cv_channel_progress.setRange(0, len(config.targets))
        self.cv_channel_progress.setValue(0)
        self.cv_point_progress.setRange(0, 1)
        self.cv_point_progress.setValue(0)
        self.channel_grid.clear_completed()

        thread = QThread(self)
        worker = CVWorker(config)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_changed.connect(self.statusBar().showMessage)
        worker.log_message.connect(self._append_cv_log)
        worker.target_started.connect(self._cv_target_started)
        worker.target_completed.connect(self._cv_target_completed)
        worker.point_measured.connect(self._cv_point_measured)
        worker.instrument_resource_resolved.connect(
            self._cv_instrument_resource_resolved
        )
        worker.result_path_ready.connect(self._cv_result_path_ready)
        worker.completed.connect(self._cv_measurement_completed)
        worker.failed.connect(self._cv_measurement_failed)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)

        self._thread = thread
        self._worker = worker
        self._active_measurement = "cv"
        self._set_running(True, "cv")
        self._show_live_cv_window()
        self._append_cv_log(
            f"CV measurement started: {len(config.targets)} "
            f"{self.MODE_LABELS[config.measurement_mode][1]}"
        )
        thread.start()

    def _result_path_ready(self, result_path):
        try:
            self._start_file_log(result_path)
        except OSError as exc:
            self._append_log(f"Cannot create status log: {exc}")
            return
        self._append_log(f"Status log: {self._log_file_path}")

    def _cv_result_path_ready(self, result_path):
        try:
            self._start_cv_file_log(result_path)
        except OSError as exc:
            self._append_cv_log(f"Cannot create status log: {exc}")
            return
        self._append_cv_log(f"Status log: {self._cv_log_file_path}")

    def _iv_instrument_resource_resolved(
        self,
        instrument_type,
        resource,
        identity,
    ):
        fields = {
            "smu": ("SMU", self.smu_edit),
            "pau": ("PAU", self.pau_edit),
        }
        name, field = fields[instrument_type]
        field.setText(resource)
        self._append_log(f"Automatically discovered {name}: {resource}")
        if identity:
            self._append_log(f"Instrument identity: {identity}")

    def _cv_instrument_resource_resolved(
        self,
        instrument_type,
        resource,
        identity,
    ):
        fields = {
            "lcr": ("LCR meter", self.cv_lcr_edit),
            "pau": ("PAU", self.cv_pau_edit),
        }
        name, field = fields[instrument_type]
        field.setText(resource)
        self._append_cv_log(f"Automatically discovered {name}: {resource}")
        if identity:
            self._append_cv_log(f"Instrument identity: {identity}")

    def _stop_measurement(self):
        if self._worker is None or self._active_measurement != "iv":
            return
        self.stop_button.setEnabled(False)
        self._append_log("Safe stop requested by user.")
        self._worker.request_stop()

    def _stop_cv_measurement(self):
        if self._worker is None or self._active_measurement != "cv":
            return
        self.cv_stop_button.setEnabled(False)
        self._append_cv_log("Safe stop requested by user.")
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
        self.channel_grid.mark_completed(mode, target)
        singular = self.MODE_LABELS[mode][0]
        self._append_log(f"{singular} {target} measurement completed.")

    def _cv_target_started(self, mode, target, index, total):
        self._cv_plot_voltage.clear()
        self._cv_plot_capacitance.clear()
        self._cv_plot_resistance.clear()
        self._refresh_cv_plot()
        self.cv_point_progress.setRange(0, 1)
        self.cv_point_progress.setValue(0)
        self.cv_channel_progress.setRange(0, total)
        self.cv_channel_progress.setValue(index)
        singular = self.MODE_LABELS[mode][0]
        self._append_cv_log(
            f"{singular} {target} CV measurement started ({index + 1}/{total})."
        )

    def _cv_target_completed(self, mode, target, index, total):
        self.cv_channel_progress.setValue(index + 1)
        self.channel_grid.mark_completed(mode, target)
        singular = self.MODE_LABELS[mode][0]
        self._append_cv_log(f"{singular} {target} CV measurement completed.")

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

    def _cv_point_measured(
        self,
        mode,
        target,
        voltage,
        capacitance,
        resistance,
        current_pau,
        index,
        total,
    ):
        self._cv_plot_voltage.append(voltage)
        self._cv_plot_capacitance.append(capacitance)
        self._cv_plot_resistance.append(resistance)
        self.cv_point_progress.setRange(0, max(total, 1))
        self.cv_point_progress.setValue(index)
        self._refresh_cv_plot()
        singular = self.MODE_LABELS[mode][0]
        self.statusBar().showMessage(
            f"{singular} {target}: {voltage:.1f} V, "
            f"C {capacitance * 1e12:.4g} pF, R {resistance:.4g} Ohm, "
            f"PAU {current_pau:.4g} A"
        )

    def _refresh_cv_plot(self):
        capacitance_pf = np.asarray(self._cv_plot_capacitance, dtype=float) * 1e12
        resistance = np.abs(np.asarray(self._cv_plot_resistance, dtype=float))
        self.cv_capacitance_curve.setData(self._cv_plot_voltage, capacitance_pf)
        self.cv_resistance_curve.setData(self._cv_plot_voltage, resistance)

    def _measurement_completed(self, stopped, result_path):
        result_path = self._mark_log_only_result(
            result_path,
            "_log_file_path",
        )
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
        self._mark_log_only_result_from_log("_log_file_path")
        self._append_log(f"Measurement failed: {message}")
        self.statusBar().showMessage(
            "Measurement failed — safe output shutdown was attempted."
        )
        QMessageBox.critical(
            self,
            "IV measurement failed",
            f"{message}\n\nAttempted 0 V, output off, and switch off_all.",
        )

    def _cv_measurement_completed(self, stopped, result_path):
        result_path = self._mark_log_only_result(
            result_path,
            "_cv_log_file_path",
        )
        message = (
            "CV measurement stopped safely."
            if stopped
            else "All CV measurements completed."
        )
        self._append_cv_log(message)
        self._append_cv_log(f"Result path: {result_path}")
        self.statusBar().showMessage(message)

    def _cv_measurement_failed(self, message):
        self._mark_log_only_result_from_log("_cv_log_file_path")
        self._append_cv_log(f"CV measurement failed: {message}")
        self.statusBar().showMessage(
            "CV measurement failed — safe output shutdown was attempted."
        )
        QMessageBox.critical(
            self,
            "CV measurement failed",
            f"{message}\n\nAttempted 0 V, output off, and switch off_all.",
        )

    def _thread_finished(self):
        thread = self._thread
        self._worker = None
        self._thread = None
        self._active_measurement = None
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

    def _append_cv_log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message.rstrip()}"
        self.cv_log_edit.append(entry)
        if self._cv_log_file_path is not None:
            with self._cv_log_file_path.open("a", encoding="utf-8") as log_file:
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

    def _start_cv_file_log(self, result_path):
        self._cv_log_file_path = None
        directory = Path(result_path).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")

        version = 0
        while True:
            path = directory / f"CV_GUI_{timestamp}_v{version}.log"
            try:
                path.touch(exist_ok=False)
            except FileExistsError:
                version += 1
                continue
            self._cv_log_file_path = path
            existing_log = self.cv_log_edit.toPlainText()
            if existing_log:
                path.write_text(existing_log + "\n", encoding="utf-8")
            return path

    def _mark_log_only_result_from_log(self, log_path_attribute):
        log_path = getattr(self, log_path_attribute)
        if log_path is None:
            return None
        return self._mark_log_only_result(log_path.parent, log_path_attribute)

    def _mark_log_only_result(self, result_path, log_path_attribute):
        directory = Path(result_path).expanduser()
        log_path = getattr(self, log_path_attribute)
        if not directory.is_dir() or log_path is None:
            return str(directory)

        entries = list(directory.iterdir())
        if not entries or any(
            not entry.is_file() or entry.suffix.lower() != ".log"
            for entry in entries
        ):
            return str(directory)

        candidate = directory.with_name(f"{directory.name}_logonly")
        version = 1
        while candidate.exists():
            candidate = directory.with_name(
                f"{directory.name}_v{version}_logonly"
            )
            version += 1

        try:
            directory.rename(candidate)
        except OSError:
            return str(directory)

        setattr(self, log_path_attribute, candidate / log_path.name)
        return str(candidate)

    def _set_running(self, running, active_measurement=None):
        self.start_button.setEnabled(not running)
        self.cv_start_button.setEnabled(not running)
        self.stop_button.setEnabled(running and active_measurement == "iv")
        self.cv_stop_button.setEnabled(running and active_measurement == "cv")
        self.measurement_tabs.tabBar().setEnabled(not running)
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
            self.cv_port_edit,
            self.cv_lcr_edit,
            self.cv_lcr_find_button,
            self.cv_pau_edit,
            self.cv_pau_find_button,
            self.cv_dry_run_check,
            self.cv_measurement_mode_combo,
            self.cv_sensor_edit,
            self.cv_start_voltage_spin,
            self.cv_end_voltage_spin,
            self.cv_step_spin,
            self.cv_ac_level_spin,
            self.cv_frequency_spin,
            self.cv_return_sweep_check,
            self.cv_result_path_edit,
            self.cv_browse_button,
            self.channel_grid,
            self.select_all_button,
            self.clear_all_button,
            self.open_channels_button,
            self.cv_open_channels_button,
            self.smu_find_button,
            self.pau_find_button,
        ):
            widget.setEnabled(not running)

    def _load_settings(self):
        for key in self.VISA_RESOURCE_SETTING_KEYS:
            self._settings.remove(key)
        if SWITCHING_MATRIX_URI_ENV not in os.environ:
            self.port_edit.setText(
                self._settings.value("iv/port", resolve_switching_matrix_uri())
            )
        self.smu_edit.clear()
        self.pau_edit.clear()
        sensor_name = self._settings.value("sensor_name")
        if sensor_name is None:
            sensor_name = self._settings.value(
                "iv/sensor",
                self._settings.value("cv/sensor", "test"),
            )
        self.sensor_edit.setText(sensor_name)
        if "IVCV_RESULT_PATH" in os.environ:
            result_path = resolve_result_path()
        else:
            result_path = self._settings.value("result_path")
            if result_path is None:
                result_path = self._settings.value(
                    "iv/result_path",
                    self._settings.value(
                        "cv/result_path",
                        resolve_result_path(),
                    ),
                )
        self.result_path_edit.setText(result_path)
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
        if SWITCHING_MATRIX_URI_ENV not in os.environ:
            self.cv_port_edit.setText(
                self._settings.value("cv/port", resolve_switching_matrix_uri())
            )
        self.cv_lcr_edit.clear()
        self.cv_pau_edit.clear()
        self.cv_start_voltage_spin.setValue(
            self._settings.value("cv/start_voltage", 0.0, type=float)
        )
        self.cv_end_voltage_spin.setValue(
            self._settings.value("cv/end_voltage", -10.0, type=float)
        )
        self.cv_step_spin.setValue(
            self._settings.value("cv/voltage_step", 1.0, type=float)
        )
        self.cv_ac_level_spin.setValue(
            self._settings.value("cv/ac_level", 0.1, type=float)
        )
        self.cv_frequency_spin.setValue(
            self._settings.value("cv/frequency", 1000.0, type=float)
        )
        self.cv_return_sweep_check.setChecked(
            self._settings.value("cv/return_sweep", False, type=bool)
        )
        self.cv_dry_run_check.setChecked(
            self._settings.value("cv/dry_run", False, type=bool)
        )
        saved_mode = self._settings.value("measurement_mode")
        if saved_mode is None:
            saved_mode = self._settings.value(
                "iv/measurement_mode",
                self._settings.value("cv/measurement_mode", "channel"),
            )
        mode_index = self.measurement_mode_combo.findData(saved_mode)
        self.measurement_mode_combo.setCurrentIndex(max(mode_index, 0))
        geometry = self._settings.value("gui/main_window_geometry_v3")
        if geometry is not None:
            self.restoreGeometry(geometry)
        channel_geometry = self._settings.value("gui/channel_window_geometry_v3")
        if channel_geometry is not None:
            self.channel_window.restoreGeometry(channel_geometry)
        live_iv_geometry = self._settings.value("gui/live_iv_window_geometry")
        if live_iv_geometry is not None:
            self.live_iv_window.restoreGeometry(live_iv_geometry)
        live_cv_geometry = self._settings.value("gui/live_cv_window_geometry")
        if live_cv_geometry is not None:
            self.live_cv_window.restoreGeometry(live_cv_geometry)

    def _save_settings(self):
        self._settings.setValue("iv/port", self.port_edit.text())
        for key in self.VISA_RESOURCE_SETTING_KEYS:
            self._settings.remove(key)
        self._settings.setValue("sensor_name", self.sensor_edit.text())
        self._settings.remove("iv/sensor")
        self._settings.remove("cv/sensor")
        self._settings.setValue("result_path", self.result_path_edit.text())
        self._settings.remove("iv/result_path")
        self._settings.remove("cv/result_path")
        self._settings.setValue("iv/start_voltage", self.start_voltage_spin.value())
        self._settings.setValue("iv/end_voltage", self.end_voltage_spin.value())
        self._settings.setValue("iv/voltage_step", self.step_spin.value())
        self._settings.setValue("iv/current_compliance", self.compliance_edit.text())
        self._settings.setValue("iv/return_sweep", self.return_sweep_check.isChecked())
        self._settings.setValue("iv/dry_run", self.dry_run_check.isChecked())
        self._settings.setValue(
            "measurement_mode",
            self.measurement_mode_combo.currentData(),
        )
        self._settings.remove("iv/measurement_mode")
        self._settings.remove("cv/measurement_mode")
        self._settings.setValue("cv/port", self.cv_port_edit.text())
        self._settings.setValue(
            "cv/start_voltage", self.cv_start_voltage_spin.value()
        )
        self._settings.setValue("cv/end_voltage", self.cv_end_voltage_spin.value())
        self._settings.setValue("cv/voltage_step", self.cv_step_spin.value())
        self._settings.setValue("cv/ac_level", self.cv_ac_level_spin.value())
        self._settings.setValue("cv/frequency", self.cv_frequency_spin.value())
        self._settings.setValue(
            "cv/return_sweep", self.cv_return_sweep_check.isChecked()
        )
        self._settings.setValue("cv/dry_run", self.cv_dry_run_check.isChecked())
        self._settings.setValue("gui/main_window_geometry_v3", self.saveGeometry())
        self._settings.setValue(
            "gui/channel_window_geometry_v3", self.channel_window.saveGeometry()
        )
        self._settings.setValue(
            "gui/live_iv_window_geometry", self.live_iv_window.saveGeometry()
        )
        self._settings.setValue(
            "gui/live_cv_window_geometry", self.live_cv_window.saveGeometry()
        )

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        if not self._channel_window_shown:
            self._channel_window_shown = True
            self._show_channel_window()

    def closeEvent(self, event: QCloseEvent):
        if self._instrument_search is not None:
            QMessageBox.information(
                self,
                "Instrument search in progress",
                "Wait for the VISA resource search to finish before closing.",
            )
            event.ignore()
            return
        if self._worker is not None:
            if self._active_measurement == "cv":
                self._stop_cv_measurement()
            else:
                self._stop_measurement()
            QMessageBox.information(
                self,
                "Stopping measurement",
                "Wait for safe output shutdown before closing the window.",
            )
            event.ignore()
            return
        self._save_settings()
        self._stop_matrix_monitors()
        self.channel_window.close()
        self.live_iv_window.close()
        self.live_cv_window.close()
        event.accept()
