"""Keep instrument connections only for the duration of a measurement call."""
from functools import wraps


def measurement_session(method):
    """Nested sweeps share the outer channel/row/column measurement session."""
    @wraps(method)
    def run(self, *args, **kwargs):
        depth = getattr(self, "_measurement_session_depth", 0)
        self._measurement_session_depth = depth + 1
        try:
            return method(self, *args, **kwargs)
        finally:
            self._measurement_session_depth = depth
            if depth == 0:
                self._close_instruments()
    return run
