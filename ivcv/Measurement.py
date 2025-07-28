import os
import re
from Util.util import mkdir, getdate, round_to_significant_figures
import matplotlib.pyplot as plt
import numpy as np
from Util.threading import Event


class Measurement:
    def __init__(self):
        self.sensor_name = ''
        self.initial_voltage = 0
        self.final_voltage = -250
        self.voltage_step = 1
        self.ranges_with_steps = []
        self.data_points = -1
        self.col_number = 1
        self.row_number = 1
        self.return_sweep = True
        self.live_plot = True
        self.resources_closed = True
        self.voltage_array = None

        self.event = Event()  # to control measurement thread
        self.measurement_thread = None

        self.n_measurement_points = 0
        self.data_index_to_draw = 0
        self.n_data_drawn = 0
        self.measurement_arr = []  # to save as output txt
        self.output_arr = []  # for live plot

        self.return_sweep_started = False
        self.measurement_in_progress = False
        self.status = ''
        self.out_txt_header = ''
        self.base_path = r'LGAD_test'
        self.date = ''
        self.out_dir_path = ''

        # for live plot
        self.y_axis_label = ''
        self.x_axis_label = ''

    def _make_out_dir(self):
        self.date = getdate()
        # self.out_dir_path = os.path.join(self.base_path, f'{self.date}_{self.sensor_name}')
        separator = ','

        if separator in self.sensor_name:
            dir_name, _ = self.sensor_name.split(separator, 1)
        else:
            dir_name = self.sensor_name

        self.out_dir_path = os.path.join(self.base_path, f'{dir_name}')
        mkdir(self.out_dir_path)

    def make_out_file_name(self):
        separator = ','

        if separator in self.sensor_name:
            sensor_name, descr = self.sensor_name.split(separator, 1)
            # FIXME use different prefix for IV and CV
            file_name = (f'IV_SMU+PAU_{sensor_name}_{descr}_{self.date}'
                         f'_col{self.col_number}_row{self.row_number}')
        else:
            file_name = (f'IV_SMU+PAU_{self.sensor_name}_{self.date}'
                         f'_col{self.col_number}_row{self.row_number}')
        return file_name

    def get_unique_file_path(self, file_name, extension='.txt'):
        # Regular expression to find files with the given prefix and a version number
        version_pattern = re.compile(rf'^{re.escape(file_name)}_v(\d+){re.escape(extension)}$')

        # Get all files in the directory that match the pattern
        matching_files = [f for f in os.listdir(self.out_dir_path) if version_pattern.match(f)]

        # If no matching files are found, return the first version
        if not matching_files:
            return os.path.join(self.out_dir_path, f"{file_name}_v0")

        # Extract the version numbers from the matching files
        version_numbers = [int(version_pattern.match(f).group(1)) for f in matching_files]

        # Determine the next version number
        next_version = max(version_numbers) + 1

        # Return the new filename with the incremented version number
        return os.path.join(self.out_dir_path, f"{file_name}_v{next_version}")

    def get_status_str(self):
        return self.status

    def is_measurement_in_progress(self):
        return self.measurement_in_progress

    def is_return_sweep_started(self):
        return self.return_sweep_started

    def get_data(self):
        if len(self.output_arr) == self.n_measurement_points:
            return None
        else:
            return self.output_arr

    def get_x_axis_label(self):
        return self.x_axis_label

    def get_y_axis_label(self):
        return self.y_axis_label

    def is_data_exists(self):
        if len(self.output_arr) > 0:
            return True
        else:
            return False

    def _reorder_ranges_with_steps(self, step_sign):
        normalized_ranges = []
        for start, end, step in self.ranges_with_steps:
            if start > 0 or end > 0:
                continue  # positive voltage is not allowed, so just ignore

            if step_sign < 0:
                step = -abs(step)

                if start < end:
                    start, end = end, start
            else:
                step = abs(step)

                if start > end:
                    start, end = end, start

            normalized_ranges.append((start, end, step))

        reverse = False

        if step_sign < 0:
            reverse = True

        normalized_ranges = sorted(normalized_ranges, key=lambda x: x[0], reverse=reverse)

        return normalized_ranges

    def _generate_series(self, initial_value, final_value):
        series = []
        current_value = initial_value

        # Determine the sign of the step based on the initial and final values
        step_sign = 1 if final_value > initial_value else -1
        default_step = abs(self.voltage_step) * step_sign

        # Rearrange ranges according to step sign
        normalized_ranges = self._reorder_ranges_with_steps(step_sign)

        for start, end, step in normalized_ranges:
            # Add numbers using the default step until the specific range starts
            if (step_sign > 0 and current_value < start) or (step_sign < 0 and current_value > start):
                generated_values = np.arange(current_value, start, default_step)
                series.extend([round_to_significant_figures(x, 4) for x in generated_values])
                current_value = start

            # Add numbers using the specific step within the given range
            if ((step_sign > 0 and current_value >= start and current_value < end) or
                    (step_sign < 0 and current_value <= start and current_value > end)):
                    
                generated_values = np.arange(current_value, end, step)
                series.extend([round_to_significant_figures(x, 4) for x in generated_values])
                current_value = end

        # Add remaining numbers using the default step
        if (step_sign > 0 and current_value < final_value) or (step_sign < 0 and current_value > final_value):
            generated_values = np.arange(current_value, final_value, default_step)
            series.extend([round_to_significant_figures(x, 4) for x in generated_values])

        # Ensure the final value is included in the series if needed
        if series and ((step_sign > 0 and series[-1] < final_value) or (step_sign < 0 and series[-1] > final_value)):
            series.append(round_to_significant_figures(final_value, 4))
        elif not series:  # Handle case where no steps have been added
            series.append(round_to_significant_figures(final_value, 4))

        return np.array(series)

    def _make_voltage_array(self, initial_voltage, final_voltage, initial_call=True):
        self.voltage_array = self._generate_series(initial_voltage, final_voltage)

        # append return sweep voltages only for the initial array creation
        if initial_call and self.return_sweep:
            self.voltage_array = np.concatenate([self.voltage_array, self.voltage_array[::-1]])
            self.data_index_to_draw = 0  # index to draw of self.output_arr

        self.n_measurement_points = len(self.voltage_array)
        self.n_data_drawn = 0

    def _update_measurement_array(self, voltage, index, is_forced_return=False):
        # defined in each measurement
        pass

    def _measure(self):
        self.measurement_in_progress = True
        last_voltage = 0
        for index, voltage in enumerate(self.voltage_array):
            self._update_measurement_array(voltage, index)

            if self.event.is_set():  # flag in Evnet is set true, when measurement stopped by user
                last_voltage = voltage
                break

        # start "forced return sweep" if the measurement stopped by user 
        if self.event.is_set():
            if last_voltage < 0:  # 
                self._make_voltage_array(last_voltage, 0, False)

                for index, voltage in enumerate(self.voltage_array):
                    self._update_measurement_array(voltage, index, True)

            # self._safe_escaper()
        self.measurement_in_progress = False
        self.return_sweep_started = False

    def get_data_point(self):
        if self.is_data_exists():
            if self.data_index_to_draw < len(self.output_arr):
                data_to_draw = self.output_arr[self.data_index_to_draw]
                self.data_index_to_draw += 1
                self.n_data_drawn += 1

                return data_to_draw
            else:
                return self.output_arr[self.data_index_to_draw-1]
        else:
            return [None, None]

    def get_out_dir(self):
        return self.out_dir_path

    def all_data_drawn(self):
        if self.n_data_drawn == self.n_measurement_points:
            return True
        else:
            return False

    def set_status_str(self, index, forced_return_sweep=False):
        self.status = f'{index + 1}/{len(self.voltage_array)} processed'
        if forced_return_sweep:
            self.return_sweep_started = True
        else:
            if self.return_sweep and index > len(self.voltage_array) / 2:
                self.return_sweep_started = True

    def save_as_plot(self, out_file_name):
        plt.ioff()
        fig = plt.Figure()
        ax = fig.add_subplot()
        output_arr_trans = np.array(self.output_arr).T
        ax.plot(output_arr_trans[0], output_arr_trans[1])
        fig.savefig(out_file_name)
        plt.close()

