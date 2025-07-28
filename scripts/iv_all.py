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

smu_rsrc = 'ASRL/dev/ttyUSB0'
pau_rsrc = 'ASRL/dev/ttyUSB3'

sname = 'w5a'

v0 = 0
v1 = -40
dv = 1
Icomp = 2e-4
return_swp = False

def pinstat_all():
    pinstat = usb.send_data('PINSTAT ALL')
    pinstat = np.array([int(i) for i in pinstat.split()]).reshape(16,16)

    return pinstat

def on(row, col):
    nch = row*16 + col
    recv = usb.send_data(f"ON {nch}")
    print (recv)

def off(row, col):
    nch = row*16 + col
    recv = usb.send_data(f"OFF {nch}")
    print (recv)

def off_all():
    stat = pinstat_all()
    for i in range(16):
        for j in range(16):
            if stat[i][j] == 1:
                off(i, j)

def measure_all():
    iv = IVMeasurement() 
    iv.base_path = "../result/"
    iv.base_path += f"{datetime.datetime.now().isoformat().split('.')[0].replace(':','')}"
    off_all()

    # loop over switches
    rows = np.arange(2)
    cols = np.arange(2)

    for row in rows:
        for col in cols:
            on(row, col)
            print (pinstat_all()) 
            iv.initialize_measurement(smu_rsrc, pau_rsrc, sname )
            iv.set_measurement_options(v0, v1, dv, Icomp, return_swp, col, row, False)
            iv.start_measurement()
            iv.measurement_thread.join()
            off(row, col)
            print (pinstat_all()) 
            time.sleep(1)

    return

def main():
    measure_all()

if __name__=="__main__":
    main()
