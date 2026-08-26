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
    instrument_resource_resolved = Signal(str, str, str)
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
            kind="CV",
            mode=self.config.measurement_mode,
            target=target,
            completed=(
                self._completed_targets if completed is None else completed
            ),
            total=len(self.config.targets) if total is None else total,
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
        runner = None
        try:
            self.status_changed.emit(
                "Connecting to the LCR meter and switching matrix..."
            )
            runner = CV_sw(config.port, config.dry_run)
            self._runner = runner
            self._publish_measurement_status("starting")
            runner.cv.set_data_callback(self._point_measured)
            runner.set_basepath(config.result_path)
            runner.set_sensor_name(config.sensor_name)
            result_dir = runner.prepare_output_directory(config.measurement_mode)
            self.result_path_ready.emit(result_dir)

            runner.set_lcr(config.lcr_resource)
            if config.lcr_resource is None:
                resource = getattr(runner, "lcr_rsrc", None)
                if resource:
                    self.instrument_resource_resolved.emit(
                        "lcr",
                        str(resource),
                        str(getattr(runner.lcr, "found_idn", "") or ""),
                    )
            if self._stop_event.is_set():
                runner.request_stop()
            runner.set_pau(config.pau_resource)
            if config.pau_resource is None:
                resource = getattr(runner, "pau_rsrc", None)
                pau = getattr(runner, "pau", None)
                if resource and pau is not None:
                    self.instrument_resource_resolved.emit(
                        "pau",
                        str(resource),
                        str(getattr(pau, "found_idn", "") or ""),
                    )
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
            self._publish_measurement_status(
                "stopped" if stopped else "completed",
                self._current_target if self._current_target >= 0 else None,
            )
            runner.close()
            runner = None
            self.completed.emit(stopped, result_dir or config.result_path)
        except BaseException as exc:
            if runner is not None:
                self._publish_measurement_status(
                    "failed",
                    self._current_target if self._current_target >= 0 else None,
                )
            details = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            self.log_message.emit(details)
            self.failed.emit(str(exc) or type(exc).__name__)
        finally:
            if runner is not None:
                runner.close()
            self._runner = None
