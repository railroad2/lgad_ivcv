import time
import threading
from numbers import Integral

from .IVMeasurement import IVMeasurement
from .config import resolve_switching_matrix_uri

from ..swmat import SWmat
from ..inst import Keithley2400, Keithley6487
from ..util.util import rowcol2nch


_DEFAULT_PORT = object()


class IV_sw:

    def __init__(self, port=_DEFAULT_PORT, dryrun=False):
        if port is _DEFAULT_PORT:
            port = resolve_switching_matrix_uri()
        self.port = port
        self.swm = SWmat(port)
        self.iv = IVMeasurement()
        self.smu = Keithley2400()
        self.pau = Keithley6487()
        self.sname = None
        self.v0 = 0
        self.v1 = -10
        self.dv = 1
        self.Icomp = 1e-5
        self.return_swp = False
        self.rt_plot = False
        self.dryrun = dryrun
        self.iv.base_path = "./IV_test"
        self._stop_requested = threading.Event()

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

    def set_smu(self, smu_rsrc=None):
        if self.dryrun:
            return 

        if smu_rsrc is None:
            print ('Looking for the SMU')
            smu_rsrc = self.smu.find_inst()

        self.smu_rsrc = smu_rsrc
        if smu_rsrc is not None:
            self.smu.open(smu_rsrc)
            print (f'SMU is connected: {smu_rsrc}')

    def set_pau(self, pau_rsrc=None):
        if self.dryrun:
            return 

        if pau_rsrc is None:
            print ('Looking for the PAU')
            pau_rsrc = self.pau.find_inst()

        self.pau_rsrc = pau_rsrc
        if pau_rsrc is not None:
            self.pau.open(pau_rsrc)
            print (f'PAU is connected: {pau_rsrc}')

    def set_sensor_name(self, sname):
        self.sname = sname

    def set_basepath(self, basepath):
        self.iv.base_path = basepath

    def prepare_output_directory(self):
        """Create the IV session directory before instruments start measuring."""
        if not self.iv.get_out_dir():
            self.iv.set_measurement_time()
            self.iv.prepare_output_directory(prefix="IV")
        return self.iv.get_out_dir()

    def set_sweep(self, v0, v1, dv=1, return_swp=False):
        self.v0 = v0
        self.v1 = v1
        self.dv = dv
        self.return_swp = return_swp
    
    def set_compliance(self, Icomp):
        self.Icomp = Icomp

    def request_stop(self):
        """Request a safe stop from another thread."""
        if not hasattr(self, "_stop_requested"):
            self._stop_requested = threading.Event()
        self._stop_requested.set()
        if hasattr(self.iv, "event"):
            self.iv.event.set()

    def reset_stop(self):
        if not hasattr(self, "_stop_requested"):
            self._stop_requested = threading.Event()
        self._stop_requested.clear()
        if hasattr(self.iv, "event"):
            self.iv.event.clear()

    def stop_requested(self):
        return getattr(self, "_stop_requested", None) is not None and self._stop_requested.is_set()
    
    def measure_Vsweep(self, row=0, col=0, target_label=None):
        v0, v1, dv = self.v0, self.v1, self.dv
        return_swp = self.return_swp
        rt_plot    = self.rt_plot
        Icomp      = self.Icomp

        iv = self.iv

        iv.set_measurement_target_label(target_label)
        iv.initialize_measurement(self.smu, self.pau, self.sname)
        iv.set_measurement_options(v0, v1, dv, Icomp, return_swp, col, row, rt_plot)
        if self.stop_requested():
            return
        iv.event.clear()
        if self.stop_requested():
            return
        iv.start_measurement(reset_event=False)

        iv.measurement_thread.join_and_raise()

    def measure_coord(self, coords, verbose=1):
        self.measure_channel(rowcol2nch(coords), verbose=verbose)

    def measure_channel(
        self,
        channels,
        verbose=1,
        on_channel_start=None,
        on_channel_complete=None,
    ):
        self.prepare_output_directory()
        if isinstance(channels, Integral):
            channels = [int(channels)]
        else:
            channels = list(channels)

        swm = self.swm
        print('Turning off all switches.')
        swm.off_all()

        started = time.time()
        try:
            for index, channel in enumerate(channels):
                if self.stop_requested():
                    break

                channel = int(channel)
                if not 0 <= channel <= 255:
                    raise ValueError(f"Channel out of range: {channel}")
                row, col = divmod(channel, 16)

                if verbose:
                    print("-" * 60)
                    print(f"Switch channel: {channel} ({row}, {col})")

                if on_channel_start is not None:
                    on_channel_start(channel, index, len(channels))

                if self.stop_requested():
                    break

                swm.on(channel)
                try:
                    if verbose:
                        print("Pinstat:")
                        print(swm.pinstat_all())

                    if self.dryrun:
                        print("   dry run.")
                    else:
                        sweep_started = time.time()
                        self.measure_Vsweep(row, col)
                        print(
                            "   Elapsed time for sweep = "
                            f"{time.time() - sweep_started} s"
                        )
                finally:
                    swm.off(channel)

                if on_channel_complete is not None:
                    on_channel_complete(channel, index, len(channels))

                print(
                    "*** Total time for measurement = "
                    f"{time.time() - started} s"
                )

                if self.stop_requested():
                    break
        finally:
            try:
                swm.off_all()
            except Exception as exc:
                print(f"WARNING: failed to turn off all switches: {exc}")

    def measure_rows(
        self,
        rows=None,
        verbose=1,
        on_row_start=None,
        on_row_complete=None,
    ):
        self.prepare_output_directory()

        if rows is None or len(rows) == 0:
            rows = list(range(16))
        else:
            rows = list(rows)

        swm = self.swm

        print('Turning off all switches.')
        swm.off_all()

        try:
            for index, row in enumerate(rows):
                if self.stop_requested():
                    break

                if not (0 <= row < 16):
                    raise ValueError(f"Row out of range: {row}")

                if verbose:
                    print("-"*60)
                    print(f"Switch row: {row}")

                if on_row_start is not None:
                    on_row_start(row, index, len(rows))

                if self.stop_requested():
                    break

                swm.on_row(row)
                try:
                    if verbose:
                        print("Pinstat:")
                        print(swm.pinstat_all())

                    if self.dryrun:
                        print(f'   dry run row: {row}')
                    else:
                        t0 = time.time()
                        self.measure_Vsweep(row, 0, target_label=f'row{row:02d}_allcol')
                        t1 = time.time()
                        print(f'   Elapsed time for row sweep = {t1 - t0} s')
                finally:
                    swm.off_row(row)

                if on_row_complete is not None:
                    on_row_complete(row, index, len(rows))

                if self.stop_requested():
                    break

        finally:
            try:
                swm.off_all()
            except Exception as exc:
                print(f"WARNING: failed to turn off all switches: {exc}")

    def measure_col(
        self,
        cols=None,
        verbose=1,
        on_col_start=None,
        on_col_complete=None,
    ):
        self.prepare_output_directory()

        if cols is None or len(cols) == 0:
            cols = list(range(16))
        else:
            cols = list(cols)

        swm = self.swm

        print('Turning off all switches.')
        swm.off_all()

        try:
            for index, col in enumerate(cols):
                if self.stop_requested():
                    break

                if not (0 <= col < 16):
                    raise ValueError(f"Column out of range: {col}")

                if verbose:
                    print("-"*60)
                    print(f"Switch col: {col}")

                if on_col_start is not None:
                    on_col_start(col, index, len(cols))

                if self.stop_requested():
                    break

                swm.on_col(col)
                try:
                    if verbose:
                        print("Pinstat:")
                        print(swm.pinstat_all())

                    if self.dryrun:
                        print(f'   dry run col: {col}')
                    else:
                        t0 = time.time()
                        self.measure_Vsweep(0, col, target_label=f'allrow_col{col:02d}')
                        t1 = time.time()
                        print(f'   Elapsed time for col sweep = {t1 - t0} s')
                finally:
                    swm.off_col(col)

                if on_col_complete is not None:
                    on_col_complete(col, index, len(cols))

                if self.stop_requested():
                    break

        finally:
            try:
                swm.off_all()
            except Exception as exc:
                print(f"WARNING: failed to turn off all switches: {exc}")

    def measure_all_channels(self):
        self.measure_channel(range(256))
