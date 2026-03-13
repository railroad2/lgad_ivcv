import time
import numpy as np

from . import swmat
from .cv import CVMeasurement
from .wk import WayneKerr4300
from .kei6487 import Keithley6487


class CV_sw():
    port = 'ws://localhost:3001'
    swm = None
    cv = None

    lcr = WayneKerr4300()
    pau = Keithley6487()

    sname = None

    v0 = 0
    v1 = -10
    dv = 1
    Icomp = 1e-5
    return_swp = False

    ac_level = 0.1
    freq = 1000

    rt_plot = False
    dryrun = False

    def __init__(self, port=None, dryrun=False):
        self.port = port
        self.dryrun = dryrun
        self.swm = swmat.SWmat(port)
        self.cv = CVMeasurement()

    def set_switching_matrix(self, port):
        self.port = port
        self.swm.open(port)

    def open(self, port=None):
        if port is not None:
            self.port = port

        if self.port is None:
            raise ValueError("Switching matrix port is not set")

        self.swm.open(self.port)

    def close(self):
        if self.swm is not None and hasattr(self.swm, "close"):
            self.swm.close()

    def off_all(self):
        self.swm.off_all()

    def on(self, row, col):
        self.swm.on(row, col)

    def off(self, row, col):
        self.swm.off(row, col)

    def pinstat_all(self):
        return self.swm.pinstat_all()