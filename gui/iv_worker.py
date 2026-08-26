import threading
import traceback
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from ..ivcv.iv_sw import IV_sw


@dataclass(frozen=True)
class IVRunConfig:
    port: str
    smu_resource: Optional[str]
    pau_resource: Optional[str]
    sensor_name: str
    result_path: str
    start_voltage: float
    end_voltage: float
    voltage_step: float
    current_compliance: float
    return_sweep: bool
    dry_run: bool
    measurement_mode: str
    targets: tuple


class IVWorker(QObject):
    """Run the blocking IV API outside the Qt GUI thread."""

    status_changed = Signal(str)
    matrix_status_changed = Signal(str)
    log_message = Signal(str)
    target_started = Signal(str, int, int, int)
    target_completed = Signal(str, int, int, int)
    point_measured = Signal(str, int, float, float, float, int, int)
    result_path_ready = Signal(str)
    completed = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._stop_event = threading.Event()
        self._runner = None
        self._current_target = -1
        self._completed_targets = 0

    def request_stop(self):
        """Set stop flags only; hardware cleanup remains in the worker threads."""
        self._stop_event.set()
        runner = self._runner
        if runner is not None:
            runner.request_stop()
        self.status_changed.emit("Stopping the measurement safely...")

    @staticmethod
    def _target_name(mode, target):
        names = {"channel": "channel", "row": "row", "column": "column"}
        return f"{names[mode]} {target}"

    def _target_started(self, target, index, total):
        mode = self.config.measurement_mode
        self._current_target = target
        self.target_started.emit(mode, target, index, total)
        self.status_changed.emit(
            f"Measuring {self._target_name(mode, target)} "
            f"({index + 1}/{total})"
        )
        self._publish_measurement_status("running", target, index, total)

    def _target_completed(self, target, index, total):
        self._completed_targets = index + 1
        self.target_completed.emit(
            self.config.measurement_mode,
            target,
            index,
            total,
        )
        self._publish_measurement_status("running", target, index + 1, total)

    def _publish_measurement_status(
        self,
        status,
        target=None,
        completed=None,
        total=None,
    ):
        runner = self._runner
        swm = getattr(runner, "swm", None)
        publisher = getattr(swm, "publish_measurement_status", None)
        if publisher is None:
            return
        publisher(
            status=status,
            kind="IV",
            mode=self.config.measurement_mode,
            target=target,
            completed=(
                self._completed_targets if completed is None else completed
            ),
            total=len(self.config.targets) if total is None else total,
        )

    def _point_measured(self, point):
        voltage, current_pau, current_smu = point
        measurement = self._runner.iv
        self.point_measured.emit(
            self.config.measurement_mode,
            self._current_target,
            float(voltage),
            float(current_pau),
            float(current_smu),
            len(measurement.output_arr),
            measurement.n_measurement_points,
        )

    @Slot()
    def run(self):
        config = self.config
        runner = None
        matrix_connected = False
        try:
            self.matrix_status_changed.emit("Connecting...")
            self.status_changed.emit(
                "Connecting to the instruments and switching matrix..."
            )
            runner = IV_sw(config.port, config.dry_run)
            self._runner = runner
            matrix_connected = True
            self.matrix_status_changed.emit("Connected")
            self._publish_measurement_status("starting")
            runner.iv.set_data_callback(self._point_measured)

            runner.set_basepath(config.result_path)
            runner.set_sensor_name(config.sensor_name)
            result_dir = runner.prepare_output_directory(config.measurement_mode)
            self.result_path_ready.emit(result_dir)

            runner.set_smu(config.smu_resource)
            if self._stop_event.is_set():
                runner.request_stop()
            runner.set_pau(config.pau_resource)
            runner.set_sweep(
                config.start_voltage,
                config.end_voltage,
                config.voltage_step,
                config.return_sweep,
            )
            runner.set_compliance(config.current_compliance)

            if self._stop_event.is_set():
                runner.request_stop()

            if config.measurement_mode == "channel":
                runner.measure_channel(
                    config.targets,
                    on_channel_start=self._target_started,
                    on_channel_complete=self._target_completed,
                )
            elif config.measurement_mode == "row":
                runner.measure_rows(
                    config.targets,
                    on_row_start=self._target_started,
                    on_row_complete=self._target_completed,
                )
            elif config.measurement_mode == "column":
                runner.measure_col(
                    config.targets,
                    on_col_start=self._target_started,
                    on_col_complete=self._target_completed,
                )
            else:
                raise ValueError(
                    f"Unknown measurement mode: {config.measurement_mode}"
                )
            stopped = self._stop_event.is_set() or runner.stop_requested()
            result_dir = runner.iv.get_out_dir()
            self._publish_measurement_status(
                "stopped" if stopped else "completed",
                self._current_target if self._current_target >= 0 else None,
            )
            runner.close()
            runner = None
            self.completed.emit(stopped, result_dir or config.result_path)
        except BaseException as exc:
            if not matrix_connected:
                self.matrix_status_changed.emit("Connection failed")
            if runner is not None:
                self._publish_measurement_status(
                    "failed",
                    self._current_target if self._current_target >= 0 else None,
                )
            details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            self.log_message.emit(details)
            self.failed.emit(str(exc) or type(exc).__name__)
        finally:
            if runner is not None:
                runner.close()
            if matrix_connected:
                self.matrix_status_changed.emit("Disconnected")
            self._runner = None
