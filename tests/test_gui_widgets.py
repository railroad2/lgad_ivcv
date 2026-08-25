import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    from lgad_ivcv.gui.channel_grid import ChannelGrid
    from lgad_ivcv.gui.iv_worker import IVRunConfig, IVWorker
except ImportError:
    QApplication = None
    ChannelGrid = None
    IVRunConfig = None
    IVWorker = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class ChannelGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

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

    def set_sweep(self, *_args):
        pass

    def set_compliance(self, _value):
        pass

    def measure_channel(self, channels, on_channel_start, on_channel_complete):
        channel = channels[0]
        on_channel_start(channel, 0, 1)
        self.iv.output_arr.append([-1.0, -2e-9, -3e-6])
        self.iv.callback(self.iv.output_arr[-1])
        on_channel_complete(channel, 0, 1)

    def stop_requested(self):
        return False

    def request_stop(self):
        pass


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class IVWorkerTests(unittest.TestCase):
    def test_worker_forwards_channel_data_and_completion(self):
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
            channels=(7,),
        )
        worker = IVWorker(config)
        points = []
        completions = []
        worker.point_measured.connect(lambda *args: points.append(args))
        worker.completed.connect(lambda *args: completions.append(args))

        with patch("lgad_ivcv.gui.iv_worker.IV_sw", FakeIVRunner):
            worker.run()

        self.assertEqual(points, [(7, -1.0, -2e-9, -3e-6, 1, 1)])
        self.assertEqual(completions, [(False, "/tmp/result/measurement")])


if __name__ == "__main__":
    unittest.main()
