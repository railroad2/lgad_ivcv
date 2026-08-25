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
    channels: tuple


class IVWorker(QObject):
    """Run the blocking IV API outside the Qt GUI thread."""

    status_changed = Signal(str)
    log_message = Signal(str)
    channel_started = Signal(int, int, int)
    channel_completed = Signal(int, int, int)
    point_measured = Signal(int, float, float, float, int, int)
    completed = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._stop_event = threading.Event()
        self._runner = None
        self._current_channel = -1

    def request_stop(self):
        """Set stop flags only; hardware cleanup remains in the worker threads."""
        self._stop_event.set()
        runner = self._runner
        if runner is not None:
            runner.request_stop()
        self.status_changed.emit("Stopping the measurement safely...")

    def _channel_started(self, channel, index, total):
        self._current_channel = channel
        self.channel_started.emit(channel, index, total)
        self.status_changed.emit(
            f"Measuring channel {channel} ({index + 1}/{total})"
        )

    def _channel_completed(self, channel, index, total):
        self.channel_completed.emit(channel, index, total)

    def _point_measured(self, point):
        voltage, current_pau, current_smu = point
        measurement = self._runner.iv
        self.point_measured.emit(
            self._current_channel,
            float(voltage),
            float(current_pau),
            float(current_smu),
            len(measurement.output_arr),
            measurement.n_measurement_points,
        )

    @Slot()
    def run(self):
        config = self.config
        try:
            self.status_changed.emit(
                "Connecting to the instruments and switching matrix..."
            )
            with IV_sw(config.port, config.dry_run) as runner:
                self._runner = runner
                runner.iv.set_data_callback(self._point_measured)

                runner.set_smu(config.smu_resource)
                if self._stop_event.is_set():
                    runner.request_stop()
                runner.set_pau(config.pau_resource)
                runner.set_basepath(config.result_path)
                runner.set_sensor_name(config.sensor_name)
                runner.set_sweep(
                    config.start_voltage,
                    config.end_voltage,
                    config.voltage_step,
                    config.return_sweep,
                )
                runner.set_compliance(config.current_compliance)

                if self._stop_event.is_set():
                    runner.request_stop()

                runner.measure_channel(
                    config.channels,
                    on_channel_start=self._channel_started,
                    on_channel_complete=self._channel_completed,
                )
                stopped = self._stop_event.is_set() or runner.stop_requested()
                result_dir = runner.iv.get_out_dir()

            self.completed.emit(stopped, result_dir or config.result_path)
        except BaseException as exc:
            details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            self.log_message.emit(details)
            self.failed.emit(str(exc) or type(exc).__name__)
        finally:
            self._runner = None
