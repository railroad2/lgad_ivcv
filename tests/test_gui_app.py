import os
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

from lgad_ivcv.gui import app


class GuiAppTests(unittest.TestCase):
    def test_allow_remote_is_hidden_and_qt_arguments_are_preserved(self):
        options, qt_arguments = app._parse_arguments(
            ["--allow-remote", "-platform", "offscreen"]
        )

        self.assertTrue(options.allow_remote)
        self.assertEqual(qt_arguments, ["-platform", "offscreen"])

        with self.assertRaises(SystemExit) as context:
            with patch("sys.stdout", new_callable=StringIO) as output:
                app._parse_arguments(["--help"])
        self.assertEqual(context.exception.code, 0)
        self.assertNotIn("--allow-remote", output.getvalue())

    def test_remote_session_is_rejected_before_qapplication_starts(self):
        with patch.dict(os.environ, {"SSH_CONNECTION": "client server"}, clear=True):
            with patch("lgad_ivcv.gui.app.QApplication") as application:
                with redirect_stderr(StringIO()) as error:
                    result = app.main([])

        self.assertEqual(result, 1)
        self.assertIn("disabled in remote SSH sessions", error.getvalue())
        application.assert_not_called()

    def test_allow_remote_bypasses_remote_session_guard(self):
        with patch.dict(os.environ, {"SSH_TTY": "/dev/pts/1"}, clear=True):
            with patch("lgad_ivcv.gui.app.QApplication") as application:
                with patch("lgad_ivcv.gui.app.MainWindow") as main_window:
                    application.instance.return_value.exec.return_value = 0
                    result = app.main(["--allow-remote"])

        self.assertEqual(result, 0)
        main_window.return_value.show.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
