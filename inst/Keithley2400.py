import numpy as np

from .instbase import InstBase


class Keithley2400(InstBase):
    _read_termination = '\r'
    _verify_msg = ("MODEL 2400", "MODEL 2410")

    _MODEL_2400_RANGES = (0.2, 2, 20, 200)
    _MODEL_2410_RANGES = (20, 100, 1000)

    def __init__(self, rname=None, read_termination=None, verify_msg=None):
        if read_termination:
            self._read_termination = read_termination

        if verify_msg:
            self._verify_msg = verify_msg

        if rname:
            self.open(rname, 
                      read_termination=self._read_termination)
    
    def initialize(self):
        self.onoff = 0
        self.set_output('off')
        self.write(":SOUR:VOLT:MODE FIXED")
        self.write(":SENS:FUNC \"VOLT\"")
        self.write(":SENS:FUNC \"CURR\"")
        self.write(":FORM:ELEM VOLT,CURR")

        self.set_voltage_range(self._voltage_ranges()[-1])
        self.set_current_limit(10E-6)
        self.sleep(0.5)
        self.set_voltage(0)

        return

    def _is_model_2410(self):
        return "MODEL 2410" in getattr(self, "found_idn", "").upper()

    def _voltage_ranges(self):
        if self._is_model_2410():
            return self._MODEL_2410_RANGES
        return self._MODEL_2400_RANGES

    def get_max_source_voltage(self):
        """Return the maximum allowed sweep magnitude for the connected model."""
        return 1100 if self._is_model_2410() else 200

    def configure_voltage_sweep(self, voltages):
        """Validate a sweep and select the smallest suitable source range."""
        requested = max((abs(float(voltage)) for voltage in voltages), default=0)
        maximum = self.get_max_source_voltage()
        if requested > maximum:
            model = "2410" if self._is_model_2410() else "2400"
            raise ValueError(
                f"Keithley {model} sweep exceeds its {maximum} V limit: "
                f"{requested} V requested"
            )

        ranges = self._voltage_ranges()
        selected_range = next(
            (voltage_range for voltage_range in ranges if requested <= voltage_range),
            ranges[-1],
        )
        self.set_voltage_range(selected_range)
        return selected_range
        
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

    def _set_voltage(self, volt):
        self.set_voltage_ramp(volt)
        return

    def set_voltage(self, volt):
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

    def set_voltage_ramp(self, target_voltage, step=1):
        if not np.isfinite(step) or step <= 0:
            raise ValueError("step must be greater than zero")

        start_voltage = self.get_voltage()
        delta = target_voltage - start_voltage
        if delta == 0:
            self.set_voltage(target_voltage)
            return

        direction = 1 if delta > 0 else -1
        signed_step = direction * abs(step)
        ramp_voltages = np.arange(
            start_voltage + signed_step,
            target_voltage,
            signed_step,
        )
        for voltage in ramp_voltages:
            self.set_voltage(voltage)
            self.sleep()

        self.set_voltage(target_voltage)
            
    def set_front_rear(self, opt):
        if opt.lower() == 'front':
            self.write(':ROUT:TERM FRONT')
        elif opt.lower() == 'rear':
            self.write(':ROUT:TERM REAR')
        else:
            print ('Invalid option for set_front_rear() function')
            return -1
            
