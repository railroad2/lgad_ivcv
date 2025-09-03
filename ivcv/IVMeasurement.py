import sys
import time

import numpy as np

from .Measurement  import Measurement
from ..inst.Keithley2400 import Keithley2400
from ..inst.Keithley6487 import Keithley6487
from ..util.thread import BaseThread 
from ..util.util   import parse_voltage_steps

class IVMeasurement(Measurement):
    def __init__(self, 
                 smu_visa_resource=None, pau_visa_resource=None,
                 sensor_name=None):
        super(IVMeasurement, self).__init__()

        self.smu = None
        self.pau = None
        self.smu_visa_resouce = smu_visa_resource
        self.pau_visa_resouce = pau_visa_resource
        self.sensor_name = sensor_name

        self.initial_voltage = 0
        self.final_voltage = -250
        self.voltage_step = 1  # TODO do not allow too big voltage_step such as 100 V
        self.data_points = -1
        self.col_number = 0
        self.row_number = 0
        self.return_sweep = True
        self.live_plot = True
        self.current_compliance = 1e-5
        self.pau_current_range = 2e-6

        self.x_axis_label = 'Bias Voltage (V)'
        self.y_axis_label = 'Current (I)'

        self.out_txt_header = 'Vinput(V)\tVsmu(V)\tIsmu(A)\tIpau(A)'
        self.base_path += r'/I-V_test'

    def initialize_measurement(self, smu_visa_resource=None, pau_visa_resource=None, sensor_name=None):
        if sensor_name:
            self.sensor_name = sensor_name

        self.measurement_arr.clear()
        self.output_arr.clear()
        self.data_points = -1
        self._make_out_dir()

        self.set_smu(smu_visa_resource)
        self.set_pau(smu_visa_resource)

        if self.smu is not None:
            self.resources_closed = False

    def set_smu(self, smu_visa_resource=None):
        if isinstance(smu_visa_resource, Keithley2400):
            self.smu = smu_visa_resource
            self._initialize_smu()
        elif isinstance(smu_visa_resource, str):
            self.smu_visa_resource = smu_visa_resource
            self.smu = Keithley2400()
            self.smu.open(self.smu_visa_resouce)
            self._initialize_smu()
        else:
            print ('An invalid resouce is assigned for SMU.')
            self.smu = None

    def _initialize_smu(self):
        self.smu.initialize()
        self.smu.set_voltage(0)
        self.smu.set_voltage_range(1000)
        self.smu.set_current_limit(10e-6)
        self.smu.sleep(0.5)
        self.smu.set_voltage(0)
        self.smu.set_front_rear('rear')
    
    def set_pau(self, pau_visa_resource=None):
        if isinstance(pau_visa_resource, Keithley6487):
            self.pau = pau_visa_resource
            self._initialize_pau()
        elif isinstance(pau_visa_resource, str):
            self.pau_visa_resource= pau_visa_resource
            self.pau = Keithley6487()
            self.pau.open(self.pau_visa_resouce)
            self._initialize_pau()
        else:
            print ('An invalid resouce is assigned for Picoammeter.')
            self.pau = None
    
    def _initialize_pau(self):
        self.pau.initialize()
        self.pau_current_range = float(self.pau.get_current_range())

    def set_measurement_options(self, initial_voltage, final_voltage, voltage_step,
                                current_compliance, return_sweep, col_number, row_number, live_plot):
        self.initial_voltage = initial_voltage
        self.final_voltage = final_voltage

        if self.initial_voltage > 0 or self.final_voltage > 0:
            raise Exception('Positive voltages not allowed.')

        if isinstance(voltage_step, (int, float)):
            self.voltage_step = voltage_step
            self.ranges_with_steps = [(self.initial_voltage, self.final_voltage, self.voltage_step)]
        else:
            self.voltage_step, self.ranges_with_steps = parse_voltage_steps(voltage_step)

        self.current_compliance = current_compliance
        self.return_sweep = return_sweep
        self.live_plot = live_plot
        self.col_number = col_number
        self.row_number = row_number

    def _safe_escaper(self):
        print("User interrupt...")
        self.smu.set_voltage(0)
        self.smu.set_output('off')
        self.smu.close()
        if (self.pau):
            self.pau.close()
        self.resources_closed = True
        print("WARNING: Please make sure the output is turned off!")
        # exit(1)

    def _update_measurement_array(self, voltage, index, is_forced_return=False, verbose=0):
        self.smu.set_voltage(voltage)

        voltage_smu, current_smu = self.smu.read().split(',')
        voltage_smu = float(voltage_smu)
        current_smu = float(current_smu)

        if (self.pau):
            current_pau, _, _ = self.pau.read_autorange().split(',')
            current_pau = float(current_pau[:-1])
        else:
            current_pau = 0

        if (verbose > 0):
            print(voltage, voltage_smu, current_smu, current_pau)  

        self.measurement_arr.append([voltage, voltage_smu, current_smu, current_pau])
        self.output_arr.append([voltage, current_pau, current_smu])
        self.set_status_str(index, is_forced_return)


    def start_measurement(self):
        self._make_voltage_array(self.initial_voltage, self.final_voltage)
        # print(self.voltage_array)
        self.smu.set_current_limit(self.current_compliance)
        # signal.signal(signal.SIGINT, self._safe_escaper)

        self.smu.set_voltage(0)
        self.smu.set_output('on')

        time.sleep(1)

        self.event.clear()
        self.measurement_thread = BaseThread(target=self._measure,
                                             callback=self.save_results)
        self.measurement_thread.start()

    def stop_measurement(self):
        self.event.set()  # set internal flag as true
        # self.measurement_thread.join()

    def save_results(self):
        if self.resources_closed is False:
            self.smu.set_voltage_ramp(0)
            self.smu.set_output('off')
            self.smu.close()
            if (self.pau):
                self.pau.close()
            self.resources_closed = True

            file_name = self.make_out_file_name()
            out_file_name = self.get_unique_file_path(file_name)

            np.savetxt(out_file_name + '.txt', self.measurement_arr, header=self.out_txt_header)
            self.save_as_plot(out_file_name + '.png')

