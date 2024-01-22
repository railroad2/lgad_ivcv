import numpy as np
import pyvisa

from gpibbase import GPIBBase

class Keithley2400(GPIBBase):
    _delay = 0.005

    def __init__(self, rname=None):
         
        if rname is not None: 
            self.open(rname)

    def open(self, rname):
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(rname)

        if '24' not in self.get_idn:
            print ('Incorrect device is assigned...')
            self._inst = []

            return -1

        return 0
    
    def initialize(self):
        self.onoff = 0
        self.write(":SOUR:VOLT:MODE FIXED")
        self.write(":SENS:FUNC \"VOLT\"")
        self.write(":SENS:FUNC \"CURR\"")
        self.write(":FORM:ELEM VOLT,CURR")

        self.set_voltage_range(1000)
        self.set_current_limit(10E-6)
        self.set_voltage(0)
        
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
        return 0

    def set_current_limit(self, I):
        self.write(f":SENS:CURR:PROT {I}")
        return 0

    def set_voltage(self, volt):
        self.write(f":SOUR:VOLT:LEV {volt}")
        self.sleep()

    def set_output(self, onoff):
        if onoff:
            self.write(":OUTP ON")
        else:
            self.write(":OUTP OFF")

        self.sleep()

    def set_source_voltage_ramp(self, v1):
        v0 = get_source_voltage()
        varr = np.arange(v0, v1, 1)

        for v in varr:
            self.set_source_voltage(v) 
        
        self.set_source_voltage(v1)
            

    """
    def measure_IV(self, vstart, vstop, npts=11, navg=1, ofname=None, reverse=True, rtplot=True):
        vset_arr = np.linspace(vstart, vstop, npts)
        if reverse:
            vset_arr = np.concatenate([vset_arr, vset_arr[::-1]])
            
        vmeas_arr = []
        imeas_arr = []
        vstd_arr = []
        istd_arr = []
        self.initialize()
        self.inst.write(":FORM:ELEM VOLT,CURR")
        self.set_source_volt(0)
        self.output_on()
         
        if rtplot:
            #plt.ion()
            fig, ax = plt.subplots()
            line1, = ax.plot([0], [0])

        for vset in vset_arr:
            self.set_source_volt(vset)
            vmeas_list = []
            imeas_list = []
            for i in range(navg):
                vmeas, imeas = self.read()
                vmeas_list.append(vmeas)
                imeas_list.append(imeas)
                
            vmeas = np.average(vmeas_list)
            vstd = np.std(vmeas_list)
            imeas = np.average(imeas_list)
            istd = np.std(imeas_list)
            
            print (vset, vmeas, imeas, vstd, istd)

            if rtplot:
                line1.set_xdata(vmeas)
                line1.set_ydata(imeas)
                fig.canvas.draw()
                fig.canvas.flush_events()
                plt.pause(0.001)

            vmeas_arr.append(vmeas)
            imeas_arr.append(imeas)
            vstd_arr.append(vstd)
            istd_arr.append(istd)

        self.output_off()
        self.varr = vmeas_arr
        self.iarr = imeas_arr
        if rtplot:
            plt.show()

        if ofname is not None:
            if '.txt' not in ofname:
                ofname += ".txt"

            data = np.array([vset_arr, vmeas_arr, imeas_arr, vstd_arr, istd_arr]).T
            hdr = f"I-V measurement using Keithley 2400, Navg={navg}\n" 
            hdr += f"V_set, V_meas, I_meas, V_std, I_std"
            np.savetxt(ofname, data, header=hdr, fmt="%+.8e")

        return vset_arr, vmeas_arr, imeas_arr

    def plot_IV(self, varr=None, iarr=None, show=True, ofname=None):
        if varr is None:
            varr = self.varr

        if iarr is None:
            iarr = self.iarr

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

