import numpy as np
import pyvisa

from .instbase import InstBase


class WayneKerr4300(InstBase):
    _delay = 0.1
    _read_termination = '\n'
    _verify_msg = "WAYNE KERR, 43"

    def __init__(self, rname=None, read_termination=None, verify_msg=None):
        if read_termination:
            self._read_termination = read_termination

        if verify_msg:
            self._verify_msg = verify_msg

        if rname:
            self.open(rname, self._read_termination)

    def initialize(self):
        self.onoff = 0
        self.write(':MEAS:NUM-OF-TEST 1')
        self.write(':MEAS:FUNC1 C')
        self.write(':MEAS:FUNC2 R')
        self.write(':MEAS:LEV 0.1')
        self.write(':MEAS:EQU-CCT PAR')
        self.write(':MEAS:SPEED MED')
        self.sleep(1)

    def measure(self):
        self.sleep()
        val = self.query(":MEAS:TRIG?")
        val = self.parse(val)
        return val

    def read_lcr(self):
        return self._inst.query(":MEAS:RES?")
         
    ## set functions
    def set_freq(self, freq):
        self.write(f":MEAS:FREQ {freq}")
        self.sleep(0)

    def set_level(self, lev):
        self.write(f":MEAS:LEV {lev}")
        self.sleep()

    def set_dc_voltage(self, volt):
        self.write(f":MEAS:V-BIAS {volt}V")
        self.sleep()

    def set_output(self, onoff):
        if onoff.lower() == 'on':
            self.write(":MEAS:BIAS ON")
            self.sleep()
            print ('LCR meter DC bias is turned on')
        elif onoff.lower() == 'off':
            self.write(":MEAS:BIAS OFF")
            self.sleep()
            print ('LCR meter DC bias is turned off')
        else:
            print("Please input 'on' or 'off'.")

    ## get functions
    def get_freq(self):
        return float(self.query(f":MEAS:FREQ?"))

    def get_level(self):
        return self.query(f":MEAS:LEV?")

    def get_dc_voltage(self, volt):
        self.query(f":MEAS:V-BIAS?")

    def get_output(self):
        return self.query(":MEAS:BIAS?")

