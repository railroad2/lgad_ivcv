import numpy as np
import time

import numpy as np
import pylab as plt
import pyvisa
from .instbase import InstBase


class Keithley6487(InstBase):
    def __init__(self, rname=None):
        if rname is not None:
            self.open()

    def open(self, rname):
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(rname)

        if '6487' not in self.get_idn():
            print ('An incorrect device has been assigned...')
            self._inst = []
            return -1

        return 0
    
    def close(self):
        self._inst.close()
        return
    
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
        self.write("CURR:RANG 2e-6")  # for probecard test
        self.write("SYST:ZCH OFF")
        return

    def get_current_range(self):
        self.query("CURR:RANGE?")
        return
    
    def set_voltage(self, V):
        self.write(f":SOUR:VOLT {V}")
        self.sleep()
        return

    def set_current_range(self, I):
        self.write(f"CURR:RANGE {I}")
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

