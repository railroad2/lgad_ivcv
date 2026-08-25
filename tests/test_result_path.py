import os
import unittest
from unittest.mock import patch

from lgad_ivcv.ivcv.config import resolve_result_path


class ResultPathTests(unittest.TestCase):
    def test_uses_environment_before_local_default(self):
        with patch.dict(os.environ, {"IVCV_RESULT_PATH": "/data/ivcv"}):
            self.assertEqual(resolve_result_path(), "/data/ivcv")

    def test_uses_local_default_without_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_result_path(), "./result")

    def test_command_line_value_overrides_environment(self):
        with patch.dict(os.environ, {"IVCV_RESULT_PATH": "/data/ivcv"}):
            self.assertEqual(resolve_result_path("/tmp/run"), "/tmp/run")


if __name__ == "__main__":
    unittest.main()
