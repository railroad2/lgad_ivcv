import os
import sys
import time
import datetime
import argparse
import ast
import numpy as np
from ast import literal_eval
from collections.abc import Iterable

import lgad_ivcv
from lgad_ivcv.ivcv import iv_sw

def measure_all(smport, v0, v1, dv, Icomp, 
                basepath, sensor_name, 
                rsmu=None, rpau=None
                channels=[], return_swp=False, dryrun=False):
    ivsw = iv_sw.IV_sw(smport, dryrun)

    ivsw.set_smu(rsmu)
    ivsw.set_pau(rpau)
    ivsw.basepath = basepath
    ivsw.set_sensor_name(sensor_name)
    ivsw.set_sweep(v0, v1, dv, return_swp)
    ivsw.set_compliance(Icomp)

    if len(channels) == 0:
        ivsw.measure_all_channels()
    else:
        if isinstance(channels[0], Iterable):
            ivsw.measure_coord(channels)
        else:
            ivsw.measure_channel(channels)
    

def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('items',        nargs="*",      default=[],     help="Channel numbers") 
    parser.add_argument('--Vstart',     required=False, default=0,      help="Start voltage")
    parser.add_argument('--Vend',       required=False, default=-10,    help="End voltage")
    parser.add_argument('--Vstep',      required=False, default=1,      help="Voltage step")
    parser.add_argument('--sensorname', required=False, default='test', help="Sensor name")
    parser.add_argument('--basepath',   required=False, default=None,   help="Base path for result output")
    parser.add_argument('--return_swp', required=False, action="store_true", help="Return sweep")
    parser.add_argument('--dryrun',     required=False, action="store_true", help="Dry run with only switching matrix operation")
    parser.add_argument('--smu',        required=False, default=None,   help="SMU resource")
    parser.add_argument('--pau',        required=False, default=None,   help="PAU resource")

    parser.add_argument('-p', '--port', required=False, default='ws://localhost:3001', help="Switching matrix port")
    parser.add_argument('-I', '--Icompliance', required=False, default=1e-5, help="SMU current compliance")

    args = parser.parse_args()

    channels = [literal_eval(i) for i in args.items]
    port = args.port

    v0 = float(args.Vstart)
    v1 = float(args.Vend)
    dv = float(args.Vstep)

    Icomp = float(args.Icompliance)

    sensor_name = args.sensorname
    return_swp = args.return_swp
    dryrun = args.dryrun
    rsmu = args.smu
    rpau = args.pau

    if args.basepath == None:
        now = datetime.datetime.now().isoformat()
        basepath = f"../../result/{now[:10]}/{now.split('.')[0].replace(':','')}"
    else:
        args.basepath = basepath

    measure_all(port, v0, v1, dv, Icomp, 
                basepath, sensor_name, 
                rsmu, rpau, 
                channels, return_swp, dryrun)

if __name__=="__main__":
    main()

