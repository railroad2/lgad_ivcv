import threading


# thread with callback function
class BaseThread(threading.Thread):
    def __init__(self, target, args=(), callback=None, callback_args=()):
        super().__init__(target=self.target_with_callback)
        self.target = target
        self.target_args = args
        self.callback = callback
        self.callback_args = callback_args

    def target_with_callback(self):
        self.target(*self.target_args)
        if self.callback is not None:
            self.callback(*self.callback_args)

