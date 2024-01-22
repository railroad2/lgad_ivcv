import numpy as np
import time

import numpy as np
import pylab as plt
import pyvisa

class Keithley6487():
    def __init__(self, rname=None):
        if rname is not None:
            self.open()

    def open(self, rname):
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(rname)

        if '6487' not in self.get_idn():
            print ('Incorrect device is assigned...')
            self._inst = []
            return -1

        return 0
    
    def set_zero(self):
        self.write("FUNC 'curr'")
        self.write("SYST:ZCH ON")
        self.write("CURR:RANG 2e-9")
        self.write("INIT")
        self.write("SYST:ZCOR:STAT OFF")
        self.write("SYST:ZCOR:ACQ")
        self.write("SYST:ZCOR ON")
        self.write("CURR:RANG:AUTO ON")
        self.write("SYST:ZCH OFF")

    def initialize(self):
        self.reset()
        self.set_zero()

    def get_current_range(self):
        self.query("CURR:RANGE?")

    def set_current_range(self, I):
        self.write(f"CURR:RANGE {I}")

    """
    def plot_IV(self, varr, iarr, show=True, ofname=None):
        plt.plot(varr, iarr, '*-')
        plt.xlabel('bias voltage (V)')
        plt.ylabel('current (A)')
        plt.tight_layout()

        if ofname is not None:
            if '.png' not in ofname:
                ofname += ".png"
            plt.savefig(ofname)

        if show:
            plt.show()
    """

