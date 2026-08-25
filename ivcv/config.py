import os


DEFAULT_RESULT_PATH = "./result"
RESULT_PATH_ENV = "IVCV_RESULT_PATH"
DEFAULT_SWITCHING_MATRIX_URI = "ws://localhost:8765"
SWITCHING_MATRIX_URI_ENV = "IVCV_SWITCHING_MATRIX_URI"


def resolve_result_path(command_line_value=None):
    """Resolve CLI override, environment setting, then local default."""
    if command_line_value is not None:
        return command_line_value
    return os.environ.get(RESULT_PATH_ENV, DEFAULT_RESULT_PATH)


def resolve_switching_matrix_uri(command_line_value=None):
    """Resolve CLI override, environment setting, then localhost default."""
    if command_line_value is not None:
        return command_line_value
    return os.environ.get(
        SWITCHING_MATRIX_URI_ENV,
        DEFAULT_SWITCHING_MATRIX_URI,
    )
