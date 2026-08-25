import threading


# thread with callback function
class BaseThread(threading.Thread):
    def __init__(self, target, args=(), callback=None, callback_args=()):
        super().__init__(target=self.target_with_callback)
        self.target = target
        self.target_args = args
        self.callback = callback
        self.callback_args = callback_args
        self.exception = None

    def target_with_callback(self):
        try:
            self.target(*self.target_args)
        except BaseException as exc:
            self.exception = exc
            return

        if self.callback is not None:
            try:
                self.callback(*self.callback_args)
            except BaseException as exc:
                self.exception = exc

    def join_and_raise(self, timeout=None):
        """Wait for the thread and re-raise a measurement/callback failure."""
        self.join(timeout)
        if self.is_alive():
            return
        if self.exception is not None:
            raise self.exception
