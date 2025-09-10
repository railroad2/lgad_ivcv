import os
import sys
import time
import datetime
import numpy as np

import lgad_ivcv
from lgad_ivcv.ivcv import cv_sw

def measure_all(smport, v0, v1, dv, basepath, return_swp=False):
    cvsw = cv_sw.CV_sw()

    cvsw.set_switching_matrix(port)
    cvsw.set_lcr()
    cvsw.set_pau()
    cvsw.basepath = basepath
    cvsw.set_sweep(v0, v1, dv, return_swp)

    #cvsw.measure_all_channels()

def main():
    port = 'ws://localhost:3001'
    sensor_name = 'w5a'

    now = datetime.datetime.now().isoformat()
    basepath = f"../../result/{now[:10]}/{now.split('.')[0].replace(':','_')}"

    v0 = 0
    v1 = -40
    dv = 1
    return_swp = False

    measure_all(port, v0, v1, dv, basepath, return_swp)


if __name__=="__main__":
    main()

