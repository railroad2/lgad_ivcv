import numpy as np
import pyvisa

from .instbase import InstBase


class Keithley2400(InstBase):
    _read_termination = '\r'
    _verify_msg = "KEITHLEY INSTRUMENTS INC.,MODEL 24"

    def __init__(self, rname=None, read_termination=None, verify_msg=None):
        if read_termination:
            self._read_termination = read_termination

        if verify_msg:
            self._verify_msg = verify_msg

        if rname:
            self.open(rname, self._read_termination)
    
    def initialize(self):
        self.onoff = 0
        self.write(":SOUR:VOLT:MODE FIXED")
        self.write(":SENS:FUNC \"VOLT\"")
        self.write(":SENS:FUNC \"CURR\"")
        self.write(":FORM:ELEM VOLT,CURR")

        self.set_voltage_range(1000)
        self.set_current_limit(10E-6)
        self.set_voltage(0)
        return
        
    ## get functions 
    def get_voltage(self):
        return float(self._inst.query(":SOUR:VOLT:LEV?"))

    def get_output(self):
        return self.query(":OUTP?")

    def get_current_limit(self):
        return self.query(":SENS:CURR:PROT?")

    def get_voltage_range(self):
        return self.query(":SOUR:VOLT:RANG?")

    ## set functions
    def set_voltage_range(self, V):
        self.write(f":SOUR:VOLT:RANG {V}")
        return

    def set_current_limit(self, I):
        self.write(f":SENS:CURR:PROT {I}")
        return

    def set_voltage(self, volt):
        self.set_source_voltage_ramp(volt)
        return

    def _set_voltage(self, volt):
        self.write(f":SOUR:VOLT:LEV {volt}")
        self.sleep()
        return

    def set_output(self, onoff):
        if onoff=='on' or onoff=='On' or onoff=='ON':
            self.write(":OUTP ON")
        elif onoff=='off' or onoff=='Off' or onoff=='OFF':
            self.write(":OUTP OFF")
        else:
            print('Please input \'on\' or \'off\'')
        self.sleep()
        return

    def set_source_voltage_ramp(self, v1, step=1):
        v0 = self.get_voltage()

        if (v1 - v0 > step):
            varr = np.arange(v0, v1, step)

            for v in varr:
                self._set_source_voltage(v) 

        self._set_source_voltage(v1)
        return
            

