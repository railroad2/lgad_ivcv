import unittest
from unittest.mock import MagicMock, patch

from scripts import cv_all, iv_all, iv_col, iv_row, iv_selected


class ScriptLifecycleTests(unittest.TestCase):
    @staticmethod
    def _runner():
        runner = MagicMock()
        runner.__enter__.return_value = runner
        runner.__exit__.return_value = False
        return runner

    def test_iv_channel_script_closes_on_measurement_failure(self):
        runner = self._runner()
        runner.measure_channel.side_effect = RuntimeError("IV failed")

        with patch.object(iv_all, "IV_sw", return_value=runner):
            with self.assertRaisesRegex(RuntimeError, "IV failed"):
                iv_all.measure_all(
                    "ws://test:8765", 0, -10, 1, 1e-5,
                    "/tmp/result", "sensor",
                    channels=[17], dryrun=True,
                )

        runner.measure_channel.assert_called_once_with([17])
        runner.__exit__.assert_called_once()

    def test_cv_channel_script_closes_on_measurement_failure(self):
        runner = self._runner()
        runner.measure_channel.side_effect = RuntimeError("CV failed")

        with patch.object(cv_all, "CV_sw", return_value=runner):
            with self.assertRaisesRegex(RuntimeError, "CV failed"):
                cv_all.measure_all(
                    "ws://test:8765", 0, -10, 1,
                    "/tmp/result", "sensor",
                    channels=[18], dryrun=True,
                )

        runner.measure_channel.assert_called_once_with([18])
        runner.__exit__.assert_called_once()

    def test_row_and_column_scripts_use_integer_lists(self):
        row_runner = self._runner()
        with patch.object(iv_row, "IV_sw", return_value=row_runner):
            iv_row.measure_rows(
                "ws://test:8765", 0, -10, 1, 1e-5,
                "/tmp/result", "sensor", rows=[1, 2], dryrun=True,
            )
        row_runner.measure_rows.assert_called_once_with([1, 2])
        row_runner.__exit__.assert_called_once()

        col_runner = self._runner()
        with patch.object(iv_col, "IV_sw", return_value=col_runner):
            iv_col.measure_col(
                "ws://test:8765", 0, -10, 1, 1e-5,
                "/tmp/result", "sensor", cols=[3, 4], dryrun=True,
            )
        col_runner.measure_col.assert_called_once_with([3, 4])
        col_runner.__exit__.assert_called_once()

    def test_selected_script_measures_only_requested_channels(self):
        runner = self._runner()
        with patch.object(iv_selected, "IV_sw", return_value=runner):
            iv_selected.measure_selected(
                "ws://test:8765", 0, -10, 1, 1e-5,
                "/tmp/result", "sensor", [3, 17, 255],
                dryrun=True,
            )

        runner.measure_channel.assert_called_once_with([3, 17, 255])
        runner.measure_all_channels.assert_not_called()
        runner.__exit__.assert_called_once()

    def test_selected_script_requires_channels(self):
        with self.assertRaisesRegex(ValueError, "at least one channel"):
            iv_selected.measure_selected(
                "ws://test:8765", 0, -10, 1, 1e-5,
                "/tmp/result", "sensor", [],
                dryrun=True,
            )

    def test_selected_channel_argument_range(self):
        self.assertEqual(iv_selected.channel_number("255"), 255)
        with self.assertRaisesRegex(Exception, "between 0 and 255"):
            iv_selected.channel_number("256")


if __name__ == "__main__":
    unittest.main()
