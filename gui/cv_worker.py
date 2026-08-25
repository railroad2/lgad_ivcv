import threading
import traceback
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from ..ivcv.cv_sw import CV_sw


@dataclass(frozen=True)
class CVRunConfig:
    port: str
    lcr_resource: Optional[str]
    pau_resource: Optional[str]
    sensor_name: str
    result_path: str
    start_voltage: float
    end_voltage: float
    voltage_step: float
    ac_level: float
    frequency: float
    return_sweep: bool
    dry_run: bool
    measurement_mode: str
    targets: tuple


class CVWorker(QObject):
    """Run the blocking CV API outside the Qt GUI thread."""

    status_changed = Signal(str)
    log_message = Signal(str)
    target_started = Signal(str, int, int, int)
    target_completed = Signal(str, int, int, int)
    point_measured = Signal(str, int, float, float, float, float, int, int)
    result_path_ready = Signal(str)
    completed = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._stop_event = threading.Event()
        self._runner = None
        self._current_target = -1

    def request_stop(self):
        self._stop_event.set()
        runner = self._runner
        if runner is not None:
            runner.request_stop()
        self.status_changed.emit("Stopping the CV measurement safely...")

    def _target_started(self, target, index, total):
        self._current_target = target
        mode = self.config.measurement_mode
        self.target_started.emit(mode, target, index, total)
        target_name = {"channel": "channel", "row": "row", "column": "column"}[
            mode
        ]
        self.status_changed.emit(
            f"Measuring CV {target_name} {target} ({index + 1}/{total})"
        )

    def _target_completed(self, target, index, total):
        self.target_completed.emit(
            self.config.measurement_mode,
            target,
            index,
            total,
        )

    def _point_measured(self, point):
        voltage, capacitance, resistance, current_pau = point
        measurement = self._runner.cv
        self.point_measured.emit(
            self.config.measurement_mode,
            self._current_target,
            float(voltage),
            float(capacitance),
            float(resistance),
            float(current_pau),
            len(measurement.output_arr),
            measurement.n_measurement_points,
        )

    @Slot()
    def run(self):
        config = self.config
        try:
            self.status_changed.emit(
                "Connecting to the LCR meter and switching matrix..."
            )
            with CV_sw(config.port, config.dry_run) as runner:
                self._runner = runner
                runner.cv.set_data_callback(self._point_measured)
                runner.set_basepath(config.result_path)
                runner.set_sensor_name(config.sensor_name)
                result_dir = runner.prepare_output_directory(
                    config.measurement_mode
                )
                self.result_path_ready.emit(result_dir)

                runner.set_lcr(config.lcr_resource)
                if self._stop_event.is_set():
                    runner.request_stop()
                runner.set_pau(config.pau_resource)
                runner.set_sweep(
                    config.start_voltage,
                    config.end_voltage,
                    config.voltage_step,
                    config.return_sweep,
                )
                runner.ac_level = config.ac_level
                runner.freq = config.frequency

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
                result_dir = runner.cv.get_out_dir()

            self.completed.emit(stopped, result_dir or config.result_path)
        except BaseException as exc:
            details = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            self.log_message.emit(details)
            self.failed.emit(str(exc) or type(exc).__name__)
        finally:
            self._runner = None
