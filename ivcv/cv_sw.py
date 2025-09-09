import os
import sys
import time
import datetime
import numpy as np

sys.path.append( os.path.dirname( os.path.abspath( os.path.dirname( os.path.abspath( os.path.dirname(__file__))))))

from .CVMeasurement import CVMeasurement

from .. import swmat
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
    basepath = None

    # voltage sweep
    v0 = 0
    v1 = -10
    dv = 1
    Icomp = 1e-5
    return_swp = False
    
    # lcr parameters
    ac_level = 0.1
    freq = 1000

    def __init__(self):
        ## Setup switching matrix
        self.swm = swmat.SWmat()
        self.cv  = CVMeasurement()

        ## output path
        self.basepath = f"../../result/{datetime.datetime.now().date().isoformat()}/{datetime.datetime.now().isoformat().split('.')[0].replace(':','')}"
        self.cv.basepath = self.basepath

    def set_switching_matrix(self, port):
        self.port = port
        self.swm.open(port)

    def set_lcr(self, lcr_rsrc=None):
        if lcr_rsrc is None:
            print ("Looking for the LCR meter")
            lcr_rsrc = self.lcr.find_inst()

        self.lcr_rsrc = lcr_rsrc
        self.lcr.open(lcr_rsrc)

    def set_pau(self, pau_rsrc=None):
        if pau_rsrc is None:
            print ("Looking for the Picoammeter")
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
    
    def measure(self, row=0, col=0):
        v0, v1, dv = self.v0, self.v1, self.dv
        return_swp = self.return_swp
        rt_plot    = self.rt_plot

        ac_level   = self.ac_level
        frequency  = self.freq

        cv = self.cv

        cv.initialize_measurement(self.lcr, self.pau, self.sname)
        cv.set_measurement_options(v0, v1, dv, 
                                   ac_level, freq, return_swp, col, row, rt_plot)
        cv.start_measurement()
        cv.measurement_thread.join()
        time.sleep(0.5)

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




