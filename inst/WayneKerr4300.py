import numpy as np
import pyvisa

from .instbase import InstBase


class WayneKerr4300(InstBase):
    def __init__(self, rname=None):
        if rname is not None: 
            self.open(rname)
    
    def open(self, rname):
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(rname)
        if ('USB' in rname) or ('usb' in rname):
            self._inst.read_termination = '\n'
            self._inst.write_termination = '\n'

        if 'WAYNE' not in self.get_idn():
            print ('An incorrect device has been assigned...')
            self.inst = []
            return -1
    
    def close(self):
        self._inst.close()

    def initialize(self):
        self.onoff = 0
        self.reset()
        self.write(':MEAS:NUM-OF-TEST 1')
        self.write(':MEAS:FUNC1 C')
        self.write(':MEAS:FUNC2 R')
        self.write(':MEAS:LEV 0.1')
        self.write(':MEAS:EQU-CCT PAR')
        self.write(':MEAS:SPEED MED')

    def measure(self):
        self.sleep()
        val = self.query("meas:trig?")
        val = self.parse(val)
        return val

    def read_lcr(self):
        return self._inst.query("MEAS:TRIG?")
         
    ## set functions
    def set_freq(self, freq):
        self.write(f":MEAS:FREQ {freq}")

    def set_level(self, lev):
        self.write(f":MEAS:LEV {lev}")

    def set_dc_voltage(self, volt):
        self.write(f":MEAS:V-BIAS {volt}V")
        self.sleep()

    def set_output(self, onoff):
        if onoff.lower() == 'on':
            self.write(":MEAS:BIAS ON")
        elif onoff.lower() == 'off':
            self.write(":MEAS:BIAS OFF")
        else:
            print("Please input 'on' or 'off'.")
        self.sleep()

    ## get functions
    def get_freq(self):
        return float(self.query(f":MEAS:FREQ?"))

    def get_level(self):
        return self.query(f":MEAS:LEV?")

    def get_dc_voltage(self, volt):
        self.query(f":MEAS:V-BIAS?")

    def get_output(self):
        return self.query(":MEAS:BIAS?")

