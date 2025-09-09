import os
import sys
import time
import datetime
import numpy as np

sys.path.append( os.path.dirname( os.path.abspath( os.path.dirname( os.path.abspath( os.path.dirname(__file__))))))

from .IVMeasurement import IVMeasurement

from .. import swmat
from ..inst import Keithley2400, Keithley6487
from ..util.util import nch2rowcol, rowcol2nch


class IV_sw():
    # switching matrix
    port = 'ws://localhost:3001'
    swm = None
    iv = None

    # instruments 
    smu = Keithley2400()
    pau = Keithley6487()

    # filename
    sname = None
    basepath = None

    # voltage sweep
    v0 = 0
    v1 = -10
    dv = 1
    Icomp = 1e-5
    return_swp = False
    
    def __init__(self):
        ## Setup switching matrix
        self.swm = swmat.SWmat()
        self.iv  = IVMeasurement()

        ## output path
        self.basepath = f"../../result/{datetime.datetime.now().date().isoformat()}/{datetime.datetime.now().isoformat().split('.')[0].replace(':','')}"
        self.iv.basepath = self.basepath

    def set_switching_matrix(self, port):
        self.port = port
        self.swm.open(port)

    def set_smu(self, smu_rsrc=None):
        if smu_rsrc is None:
            print ('Looking for the SMU')
            smu_rsrc = self.smu.find_inst()

        self.smu_rsrc = smu_rsrc
        if smu_rsrc is not None:
            self.smu.open(smu_rsrc)

    def set_pau(self, pau_rsrc=None):
        if pau_rsrc is None:
            print ('Looking for the PAU')
            pau_rsrc = self.pau.find_inst()

        self.pau_rsrc = pau_rsrc
        if pau_rsrc is not None:
            self.pau.open(pau_rsrc)

    def set_sensor_name(self, sname):
        self.sname = sname

    def set_result_path(self, basepath):
        self.basepath = basepath
        self.iv.basepath = pasepath

    def set_sweep(self, v0, v1, dv=1, return_swp=False):
        self.v0 = v0
        self.v1 = v1
        self.dv = dv
        self.return_swp = return_swp
    
    def set_compliance(self, Icomp):
        self.Icomp = Icomp

    def measure(self, row=0, col=0):
        v0, v1, dv = self.v0, self.v1, self.dv
        return_swp = self.return_swp
        rt_plot    = self.rt_plot
        Icomp      = self.Icomp

        iv = self.iv

        iv.initialize_measurement(self.smu, self.pau, self.sname)
        iv.set_measurement_options(v0, v1, dv, Icomp, return_swp, col, row, rt_plot)
        iv.start_measurement()
        iv.measurement_thread.join()

    def measure_coord(self, coords, verbose=1):
        swm = self.swm

        swm.off_all()

        for row, col in coords:
            swm.on(row, col)
            if verbose: print (swm.pinstat_all()) 
            
            self.measure(row, col) 

            swm.off(row, col)
            if verbose: print (swm.pinstat_all()) 

            time.sleep(0.5)

    def measure_channel(self, channels):
        coords = nch2rowcol(channels)
        self.measure_coord(coords)

    def measure_all_channels(self):
        cols, rows = np.meshgrid(np.arange(16), np.arange(16))
        coords = np.array([rows.flatten(), cols.flatten()]).T
        self.measure_coord(coords)




