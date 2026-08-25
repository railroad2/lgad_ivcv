import time
from numbers import Integral

from .IVMeasurement import IVMeasurement

from ..swmat import SWmat
from ..inst import Keithley2400, Keithley6487
from ..util.util import rowcol2nch


class IV_sw:

    def __init__(self, port=None, dryrun=False):
        self.port = port or 'ws://localhost:8765'
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

    def set_sweep(self, v0, v1, dv=1, return_swp=False):
        self.v0 = v0
        self.v1 = v1
        self.dv = dv
        self.return_swp = return_swp
    
    def set_compliance(self, Icomp):
        self.Icomp = Icomp
    
    def measure_Vsweep(self, row=0, col=0, target_label=None):
        v0, v1, dv = self.v0, self.v1, self.dv
        return_swp = self.return_swp
        rt_plot    = self.rt_plot
        Icomp      = self.Icomp

        iv = self.iv

        iv.set_measurement_target_label(target_label)
        iv.initialize_measurement(self.smu, self.pau, self.sname)
        iv.set_measurement_options(v0, v1, dv, Icomp, return_swp, col, row, rt_plot)
        iv.start_measurement()

        iv.measurement_thread.join()

    def measure_coord(self, coords, verbose=1):
        self.measure_channel(rowcol2nch(coords), verbose=verbose)

    def measure_channel(self, channels, verbose=1):
        self.iv.set_measurement_time()
        if isinstance(channels, Integral):
            channels = [int(channels)]

        swm = self.swm
        print('Turning off all switches.')
        swm.off_all()

        started = time.time()
        try:
            for channel in channels:
                channel = int(channel)
                if not 0 <= channel <= 255:
                    raise ValueError(f"Channel out of range: {channel}")
                row, col = divmod(channel, 16)

                if verbose:
                    print("-" * 60)
                    print(f"Switch channel: {channel} ({row}, {col})")

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

                print(
                    "*** Total time for measurement = "
                    f"{time.time() - started} s"
                )
        finally:
            try:
                swm.off_all()
            except Exception as exc:
                print(f"WARNING: failed to turn off all switches: {exc}")

    def measure_rows(self, rows=None, verbose=1):
        self.iv.set_measurement_time()

        if rows is None or len(rows) == 0:
            rows = list(range(16))

        swm = self.swm

        print('Turning off all switches.')
        swm.off_all()

        try:
            for row in rows:
                if not (0 <= row < 16):
                    raise ValueError(f"Row out of range: {row}")

                if verbose:
                    print("-"*60)
                    print(f"Switch row: {row}")

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

        finally:
            try:
                swm.off_all()
            except Exception as exc:
                print(f"WARNING: failed to turn off all switches: {exc}")

    def measure_col(self, cols=None, verbose=1):
        self.iv.set_measurement_time()

        if cols is None or len(cols) == 0:
            cols = list(range(16))

        swm = self.swm

        print('Turning off all switches.')
        swm.off_all()

        try:
            for col in cols:
                if not (0 <= col < 16):
                    raise ValueError(f"Column out of range: {col}")

                if verbose:
                    print("-"*60)
                    print(f"Switch col: {col}")

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

        finally:
            try:
                swm.off_all()
            except Exception as exc:
                print(f"WARNING: failed to turn off all switches: {exc}")

    def measure_all_channels(self):
        self.measure_channel(range(256))
