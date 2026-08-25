import os


DEFAULT_RESULT_PATH = "./result"
RESULT_PATH_ENV = "IVCV_RESULT_PATH"


def resolve_result_path(command_line_value=None):
    """Resolve CLI override, environment setting, then local default."""
    if command_line_value is not None:
        return command_line_value
    return os.environ.get(RESULT_PATH_ENV, DEFAULT_RESULT_PATH)
