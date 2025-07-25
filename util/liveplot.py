from matplotlib import animation as ani
from matplotlib import pyplot as plt


class FuncAnimationDisposable(ani.FuncAnimation):
    def __init__(self, fig, func, **kwargs):
        print("use custom FuncAnimation...")
        if "auto_close" in kwargs:
            self._automatic_close = kwargs["auto_close"]
            del kwargs["auto_close"]
            print("set auto close True")
        else:
            self._automatic_close = False
        super().__init__(fig, func, **kwargs)

    def _step(self, *args):
        still_going = ani.Animation._step(self, *args)
        if not still_going:
            if self._automatic_close:
                print("close window")
                plt.close()
                return False
            else:
                return True
        else:
            self.event_source.interval = self._interval
            return still_going

    def _stop(self, *args):
        if self._blit:
            self._fig.canvas.mpl_disconnect(self._resize_id)
        self._fig.canvas.mpl_disconnect(self._close_id)

