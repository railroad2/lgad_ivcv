import os
import sys
import time
import datetime
import numpy as np

import lgad_ivcv
from lgad_ivcv.ivcv import iv_sw

def measure_all(smport, v0, v1, dv, Icomp, basepath, return_swp=False):
    ivsw = iv_sw.IV_sw()

    ivsw.set_switching_matrix(smport)
    ivsw.set_smu()
    ivsw.set_pau()
    ivsw.basepath = basepath
    ivsw.set_sweep(v0, v1, dv, return_swp)
    ivsw.set_compliance(Icomp)

    #ivsw.measure_all_channels()

def main():
    port = 'ws://localhost:3001'
    sensor_name = 'w5a'

    now = datetime.datetime.now().isoformat()
    basepath = f"../../result/{now[:10]}/{now.split('.')[0].replace(':','')}"

    v0 = 0
    v1 = -40
    dv = 1
    Icomp = 3e-4
    return_swp = False

    measure_all(port, v0, v1, dv, Icomp, basepath, return_swp)

if __name__=="__main__":
    main()

