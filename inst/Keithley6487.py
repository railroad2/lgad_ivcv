import sys
import time
import numpy as np

import numpy as np
import pylab as plt
import pyvisa
from .instbase import InstBase, InstError

DEBUG=0

class Keithley6487(InstBase):
    _read_termination = '\r'
    _verify_msg = "KEITHLEY INSTRUMENTS INC.,MODEL 6487"

    current_range = 2e-6
    min_range = 2e-9  # minimum range = 2 nA
    max_range = 20e-3 # maximum range = 20 mA

    def __init__(self, rname=None, read_termination=None, verify_msg=None):
        if read_termination:
            self._read_termination = read_termination

        if verify_msg:
            self._verify_msg = verify_msg

        if rname:
            self.open(rname, self._read_termination)
    
    def set_zero(self):
        self.write("FUNC 'curr'")

        self.write("SYST:ZCH ON")
        self.write("CURR:RANG 2e-9")
        self.write("INIT")
        self.write("SYST:ZCOR:STAT OFF")
        self.write("SYST:ZCOR:ACQ")
        self.write("SYST:ZCOR ON")

        self.write("CURR:RANG:AUTO OFF")
        self.write("SYST:ZCH OFF")
        return

    def initialize_full(self):  # use this for CV measuremnet, not clear why
        self.reset()
        self.set_zero()
        self.write("SOUR:VOLT:STAT OFF")
        self.write("SOUR:VOLT:RANG 500")
        self.write("FORM:ELEM READ,UNIT,STAT,VSO")
        return

    def initialize(self):
        self.reset()
        self.write("FUNC 'curr'")  # just to be sure
        self.write("INIT")  # TODO check without this line
        self.write("CURR:RANG:AUTO OFF")
        self.write("CURR:RANG 2e-9")  # for probecard test
        self.write("SENS:CURR:NPLC 1")
        self.write("SYST:AZER OFF")
        self.write("SYST:ZCH OFF")
        self.sleep(0.5)
        return

    def get_current_range(self):
        val = self.query("CURR:RANGE?")
        return val
    
    def set_voltage(self, V):
        self.write(f":SOUR:VOLT {V}")
        self.sleep()
        return

    def set_current_range(self, I):
        self.write(f"CURR:RANGE {I}")
        self.current_range = I
        return

    def set_current_limit(self, I):
        self.write(f":SOUR:VOLT:ILIM {I}")
        return 0

    def set_output(self, onoff):
        if onoff=='on' or onoff=='On' or onoff=='ON':
            self.write(':SOUR:VOLT:STAT ON')
        elif onoff=='off' or onoff=='Off' or onoff=='OFF':
            self.write(':SOUR:VOLT:STAT OFF')
        else:
            print('Please input \'on\' or \'off\'')
        self.sleep()
        return


    def read_autorange(self, attempts=10):
        val = 0
        last = np.nan
        underflow_factor = 1e-4
        overflow_threshold = 1e30

        def _clip_and_set(new_r):
            new_r = max(new_r, self.min_range)
            new_r = min(new_r, self.max_range)
            cur_r = self.current_range
            if abs(new_r - cur_r) / max(cur_r, 1e-30) > 1e-6:
                self.set_current_range(new_r)
                self.sleep()

        for _ in range(attempts):
            try:
                raw = self.read()
                val = raw.split(',', 1)[0].strip()

                if val and val[-1].isalpha():
                    val = val[:-1]

                val = float(val)
            except Exception as e:
                raise InstError(f"Reading pau failed: {e}") from e

            if abs(val) > overflow_threshold:
                print (f"  overflow: {val}, current range: {self.current_range}")
                _clip_and_set(self.current_range * 10.0) 
                last = raw
            elif abs(val) < underflow_factor * self.current_range:
                print (f"  underflow: {val}, current range: {self.current_range}")
                _clip_and_set(self.current_range * 0.10)
                last = raw
            else:
                return raw

        print (f"Failed to obtain valid current range within {attempts} attempts. Last is {last}", file=sys.stderr)   

        return last

