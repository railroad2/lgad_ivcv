import os
import sys
import time
import datetime
import numpy as np

sys.path.append(
    os.path.dirname(
        os.path.abspath(
            os.path.dirname(
                os.path.abspath(
                    os.path.dirname(__file__)
                )
            )
        )
    )
)

from .CVMeasurement import CVMeasurement

from lgad_ivcv.swmat import swmat
from ..inst import WayneKerr4300, Keithley6487
from ..util.util import nch2rowcol, rowcol2nch


class CV_sw():
    # switching matrix
    port = 'ws://localhost:3001'
    swm = None
    cv = None

    # instruments
    lcr = WayneKerr4300()
    pau = Keithley6487()

    # filename
    sname = None

    # voltage sweep
    v0 = 0
    v1 = -10
    dv = 1
    Icomp = 1e-5
    return_swp = False

    # lcr parameters
    ac_level = 0.1
    freq = 1000

    # realtime plot
    rt_plot = False
    dryrun = False

    def __init__(self, port=None, dryrun=False):
        ## Setup switching matrix
        self.swm = swmat.SWmat(port)
        self.cv = CVMeasurement()

        self.dryrun = dryrun
        if port is not None:
            self.port = port

    def set_switching_matrix(self, port):
        self.port = port
        self.swm.open(port)

    def set_lcr(self, lcr_rsrc=None):
        if self.dryrun:
            self.lcr_rsrc = lcr_rsrc
            return

        if lcr_rsrc is None:
            print("Looking for the LCR meter")
            lcr_rsrc = self.lcr.find_inst()

        self.lcr_rsrc = lcr_rsrc
        if lcr_rsrc is not None:
            self.lcr.open(lcr_rsrc)

    def set_pau(self, pau_rsrc=None):
        if self.dryrun:
            self.pau_rsrc = pau_rsrc
            return

        if pau_rsrc is None:
            print("Looking for the Picoammeter")
            pau_rsrc = self.pau.find_inst()

        self.pau_rsrc = pau_rsrc
        if pau_rsrc is not None:
            self.pau.open(pau_rsrc)

    def set_sensor_name(self, sname):
        self.sname = sname

    def set_basepath(self, basepath):
        self.cv.base_path = basepath

    def set_sweep(self, v0, v1, dv=1, return_swp=False):
        self.v0 = v0
        self.v1 = v1
        self.dv = dv
        self.return_swp = return_swp

    def measure(self, row=0, col=0):
        v0, v1, dv = self.v0, self.v1, self.dv
        return_swp = self.return_swp
        rt_plot = self.rt_plot

        ac_level = self.ac_level
        freq = self.freq

        cv = self.cv

        if self.dryrun:
            print(f"   dry run CV: row={row}, col={col}")
            return

        cv.initialize_measurement(self.lcr, self.pau, self.sname)
        cv.set_measurement_options(
            v0, v1, dv,
            ac_level, freq, return_swp, col, row, rt_plot
        )
        cv.print_options()
        cv.start_measurement()
        cv.measurement_thread.join()
        time.sleep(0.5)

    def measure_coord(self, coords, verbose=1):
        swm = self.swm

        swm.off_all()

        try:
            for row, col in coords:
                swm.on(row, col)
                try:
                    if verbose:
                        print(swm.pinstat_all())

                    self.measure(row, col)

                finally:
                    swm.off(row, col)
                    if verbose:
                        print(swm.pinstat_all())

                time.sleep(0.5)

        finally:
            try:
                swm.off_all()
            except Exception:
                pass

    def measure_channel(self, channels):
        coords = nch2rowcol(channels)
        self.measure_coord(coords)

    def measure_all_channels(self):
        cols, rows = np.meshgrid(np.arange(16), np.arange(16))
        coords = np.array([rows.flatten(), cols.flatten()]).T
        self.measure_coord(coords)
