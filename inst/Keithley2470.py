import numpy as np

from .instbase import InstBase, InstError


class Keithley2470(InstBase):
    """SCPI driver for a Keithley 2470 High Voltage SourceMeter."""

    _read_termination = "\n"
    _write_termination = "\n"
    _verify_msg = "MODEL 2470"

    def __init__(self, rname=None, read_termination=None, verify_msg=None):
        if read_termination is not None:
            self._read_termination = read_termination
        if verify_msg is not None:
            self._verify_msg = verify_msg

        if rname is not None:
            self.open(rname, read_termination=self._read_termination)

    def _ensure_scpi_mode(self):
        command_set = self.query("*LANG?").strip().upper()
        if command_set != "SCPI":
            raise InstError(
                "Keithley 2470 is not in SCPI mode. Set the command set to "
                "SCPI with '*LANG SCPI', then reboot the instrument."
            )

    def initialize(self):
        self._ensure_scpi_mode()
        self.set_output("off")
        self.write(":SOUR:FUNC VOLT")
        self.write(':SENS:FUNC "CURR"')
        self.write(":SOUR:VOLT:READ:BACK ON")
        self.write(":SENS:CURR:RANG:AUTO ON")

        self.set_voltage_range(1000)
        self.set_current_limit(10e-6)
        self.sleep(0.5)
        self.set_voltage(0)

    def get_voltage(self):
        return float(self.query(":SOUR:VOLT?"))

    def get_output(self):
        return self.query(":OUTP?")

    def get_current_limit(self):
        return self.query(":SOUR:VOLT:ILIM?")

    def get_voltage_range(self):
        return self.query(":SOUR:VOLT:RANG?")

    def set_voltage_range(self, voltage):
        self.write(f":SOUR:VOLT:RANG {voltage}")

    def set_current_limit(self, current):
        self.write(f":SOUR:VOLT:ILIM {current}")

    def _set_voltage(self, voltage):
        self.set_voltage_ramp(voltage)

    def set_voltage(self, voltage):
        self.write(f":SOUR:VOLT {voltage}")
        self.sleep()

    def set_output(self, onoff):
        state = str(onoff).lower()
        if state == "on":
            self.write(":OUTP ON")
        elif state == "off":
            self.write(":OUTP OFF")
        else:
            print("Please input 'on' or 'off'")
        self.sleep()

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

    def set_front_rear(self, option):
        option = option.lower()
        if option == "front":
            self.write(":ROUT:TERM FRONT")
        elif option == "rear":
            self.write(":ROUT:TERM REAR")
        else:
            print("Invalid option for set_front_rear() function")
            return -1
        return None

    def read(self):
        """Return source readback voltage and measured current as CSV text."""
        return self.query(':READ? "defbuffer1", SOUR, READ')
