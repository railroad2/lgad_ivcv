import time
from numbers import Integral

from .CVMeasurement import CVMeasurement
from .config import resolve_switching_matrix_uri

from ..swmat import SWmat
from ..inst import WayneKerr4300, Keithley6487
from ..util.util import rowcol2nch


_DEFAULT_PORT = object()


class CV_sw:

    def __init__(self, port=_DEFAULT_PORT, dryrun=False):
        if port is _DEFAULT_PORT:
            port = resolve_switching_matrix_uri()
        self.port = port
        self.swm = SWmat(port)
        self.cv = CVMeasurement()
        self.lcr = WayneKerr4300()
        self.pau = None
        self.sname = None
        self.v0 = 0
        self.v1 = -10
        self.dv = 1
        self.Icomp = 1e-5
        self.return_swp = False
        self.ac_level = 0.1
        self.freq = 1000
        self.rt_plot = False
        self.dryrun = dryrun

    def set_switching_matrix(self, port):
        self.port = port
        self.swm.open(port)

    def close(self):
        if self.swm.comm is None:
            return
        try:
            self.swm.off_all()
        except Exception as exc:
            print(f"WARNING: failed to turn off all switches: {exc}")
        finally:
            self.swm.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

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
            #print("Looking for the Picoammeter")
            #pau_rsrc = self.pau.find_inst()
            print ("No picoammeter will be used.")

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

    def measure(self, row=0, col=0, target_label=None):
        v0, v1, dv = self.v0, self.v1, self.dv
        return_swp = self.return_swp
        rt_plot = self.rt_plot

        ac_level = self.ac_level
        freq = self.freq

        cv = self.cv
        cv.set_measurement_target_label(target_label)

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
        cv.measurement_thread.join_and_raise()
        time.sleep(0.5)

    def measure_coord(self, coords, verbose=1):
        self.measure_channel(rowcol2nch(coords), verbose=verbose)

    def measure_channel(self, channels, verbose=1):
        if isinstance(channels, Integral):
            channels = [int(channels)]

        swm = self.swm
        swm.off_all()

        try:
            for channel in channels:
                channel = int(channel)
                if not 0 <= channel <= 255:
                    raise ValueError(f"Channel out of range: {channel}")
                row, col = divmod(channel, 16)

                swm.on(channel)
                try:
                    if verbose:
                        print(swm.pinstat_all())
                    self.measure(row, col)
                finally:
                    swm.off(channel)
                    if verbose:
                        print(swm.pinstat_all())

                time.sleep(0.5)
        finally:
            try:
                swm.off_all()
            except Exception as exc:
                print(f"WARNING: failed to turn off all switches: {exc}")

    def measure_all_channels(self):
        self.measure_channel(range(256))
