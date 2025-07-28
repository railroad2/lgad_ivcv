import os
import datetime
import serial
import re
import numpy as np


def mkdir(path):
    path = os.path.normpath(path)
    
    try: 
        os.mkdir(path)
    except FileExistsError: 
        return 
    except FileNotFoundError:
        mkdir(os.path.join(*path.split('/')[:-1]))

    mkdir(path)
    return


def getdate():
    return datetime.datetime.today().date().isoformat()


def make_unique_name(fn):
    uniq = 0

    while os.path.exists(fn):
        uniq += 1
        name, ext = os.path.splitext(fn)
        fn = f'{name}_{uniq}{ext}'

    return file_name


def round_to_significant_figures(x, sig_figs):
    if x == 0:
        return 0
    return round(x, sig_figs - int(np.floor(np.log10(abs(x)))) - 1)


def parse_voltage_steps(input_str):
    # Normalize the input by removing all spaces
    input_str = input_str.replace(' ', '')

    # Define the regular expression pattern
    # The pattern below captures the mandatory number and any number of tuples
    pattern = re.compile(r'^(\d+)(?:,(.*))?$')

    # Match the input string with the pattern
    match = pattern.match(input_str)

    if not match:
        raise ValueError("The input string does not match the expected format.")

    # Extract the mandatory number
    mandatory_number = int(match.group(1))

    # Extract the optional tuples part, if they exist
    tuple_values = []
    if match.group(2):
        tuples_str = match.group(2)
        # Split the tuples_str by '),(' to separate individual tuples
        tuples_str = tuples_str.strip()
        tuples_str = tuples_str.split('),(')

        # Clean up the first and last tuple to remove extra parentheses
        tuples_str[0] = tuples_str[0].strip('(')
        tuples_str[-1] = tuples_str[-1].strip(')')

        # Process each tuple string to convert it into a tuple of integers
        for t_str in tuples_str:
            numbers = list(map(float, t_str.split(',')))
            tuple_values.append(tuple(numbers))

    return mandatory_number, tuple_values

