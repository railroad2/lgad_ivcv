import os
import sys
import time
import datetime
import numpy as np

sys.path.append( os.path.dirname(os.path.abspath( os.path.dirname(os.path.abspath( os.path.dirname(__file__))))))

import lgad_ivcv
from lgad_ivcv.util import usbcomm
from lgad_ivcv.ivcv.IVMeasurement import IVMeasurement

port = '/dev/ttyACM0'
usb = usbcomm.USBComm(port)
usb.connect()

smu_rsrc = 'ASRL/dev/ttyUSB1'
pau_rsrc = 'ASRL/dev/ttyUSB0'

sname = 'w5a'
basepath = f"../../result/{datetime.datetime.now().date().isoformat()}/{datetime.datetime.now().isoformat().split('.')[0].replace(':','')}"

v0 = 0
v1 = -40
dv = 1
Icomp = 3e-4
return_swp = False


def measure_coord(coords):
    iv = IVMeasurement() 
    iv.base_path = basepath
    print (iv.base_path)
    off_all()

    for row, col in coords:
        on(row, col)
        print (pinstat_all()) 
        iv.initialize_measurement(smu_rsrc, pau_rsrc, sname )
        iv.set_measurement_options(v0, v1, dv, Icomp, return_swp, col, row, False)
        iv.start_measurement()
        iv.measurement_thread.join()
        off(row, col)
        print (pinstat_all()) 
        time.sleep(0.5)

    return

def measure_channel(channels):
    iv = IVMeasurement() 
    iv.base_path = basepath
    print (iv.base_path)
    off_all()

    for nch in channels:
        row = nch // 16
        col = nch % 16
        on(row, col)
        print (pinstat_all()) 
        iv.initialize_measurement(smu_rsrc, pau_rsrc, sname )
        iv.set_measurement_options(v0, v1, dv, Icomp, return_swp, col, row, False)
        iv.start_measurement()
        iv.measurement_thread.join()
        off(row, col)
        print (pinstat_all()) 
        time.sleep(0.5)

    return

def all_channel():
    cols, rows = np.meshgrid(np.arange(16), np.arange(16))
    coords = np.array([rows.flatten(), cols.flatten()]).T
    measure_coord(coords)

def selected_coords():
    coords = [(0, 3),(1, 2),(1, 3),(5, 0),(5, 1),(5, 9),(6, 0),(6, 1),(6, 6),(6, 7),(6, 11),(6, 15),(7, 0),(7, 6),(7, 10)]

    measure_coord(coords)

def selected_channels():
    channels = np.arange(13*16+12, 256)
    measure_channel(channels)

def just_measure(row, col):
    iv = IVMeasurement() 
    iv.base_path = basepath

    print (pinstat_all()) 
    iv.initialize_measurement(smu_rsrc, pau_rsrc, sname )
    iv.set_measurement_options(v0, v1, dv, Icomp, return_swp, col, row, False)
    iv.start_measurement()
    iv.measurement_thread.join()
    time.sleep(1)

def main():
    


if __name__=="__main__":
    main()

