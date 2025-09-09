import os
import sys
import time
import datetime
import argparse
import serial

import numpy as np

import lgad_ivcv
from lgad_ivcv.ivcv.CVMeasurement import CVMeasurement

parser = argparse.ArgumentParser(description='')
parser.add_argument('--sensorname',  required=False, default='test', help='Sensor name')
parser.add_argument('--Icompliance', required=False, default=1e-5, help='Current compliance')
parser.add_argument('--Vstart',      required=False, default=0,    help='Start voltage')
parser.add_argument('--Vstep',       required=False, default=1,    help='Voltage step')
parser.add_argument('--Vend',        required=False, default=-40, help='End voltage')
parser.add_argument('--returnsweep', required=False, default=False, help='Return sweep')

args = parser.parse_args()

basepath = f"/home/lgad/lgad_test/result/{datetime.datetime.now().date().isoformat()}/{datetime.datetime.now().isoformat().split('.')[0].replace(':','')}"
sname = args.sensorname

v0 = float(args.Vstart) #0
v1 = float(args.Vend) #-40
dv = float(args.Vstep) #1
Icomp = float(args.Icompliance)
return_swp = args.returnsweep

lcr_rsrc = None
pau_rsrc = None

def get_idn(port, baudrate=9600):
    ser = serial.Serial(
            port = port,
            baudrate = baudrate,
            timeout = 3)
    ser.isOpen()
    cmd = "*idn?\n"
    ser.write(cmd.encode())
    time.sleep(0.15)
    response = ser.read_all().decode("utf-8")[:-1]

    return response


def find_inst():
    path = '/dev'
    lst = os.listdir(path)
    lst = [l for l in lst if 'USB' in l]

    global lcr_rsrc, pau_rsrc

    for l in lst:
        idn = get_idn(os.path.join(path, l)) 

        if 'WAYNE KERR, 43' in idn:
            lcr_rsrc = 'ASRL'+os.path.join(path, l)
            print (lcr_rsrc)
        elif 'KEITHLEY INSTRUMENTS INC.,MODEL 6487' in idn:
            pau_rsrc = 'ASRL'+os.path.join(path, l)
            print (pau_rsrc)
        else:
            pass


def just_measure(row, col):
    cv = CVMeasurement() 
    cv.base_path = basepath
    pau_rsrc = None

    print (f"{sname=      }")
    print (f"{v0=         }")
    print (f"{v1=         }")
    print (f"{dv=         }")
    print (f"{Icomp=      }")
    print (f"{return_swp= }")
    print (f"{lcr_rsrc=   }")
    print (f"{pau_rsrc=   }")

    ac_level = 0.1
    frequency = 1000
    cv.initialize_measurement(lcr_rsrc, pau_rsrc, sname)
    cv.set_measurement_options(v0, v1, dv, 
                               ac_level, frequency, return_swp, col, row, False)
    cv.start_measurement()
    cv.measurement_thread.join()
    time.sleep(1)


def main():
    find_inst()
    #just_measure(0,0)


if __name__=="__main__":
    main()

