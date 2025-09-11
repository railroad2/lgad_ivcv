import os
import sys
import time
import json
import serial
#sys.path.append( os.path.dirname(os.path.abspath( os.path.dirname(os.path.abspath( os.path.dirname(__file__))))))
#try:
#    from print_utils import print_with_frame, parse_first_json_line
#except ModuleNotFoundError:
#    from .print_utils import print_with_frame, parse_first_json_line

#sys.path.insert(0, '..')
from print_utils import print_with_frame, parse_first_json_line
    

def sw_onoff(ch, onoff):
    if ch is None:
        ch1 = "all"
    elif isinstance(ch, (list, tuple)):
        ch1 = [str(c) for c in ch]
        ch1 = ' '.join(ch1)
    else:
        ch1 = ch

    port = '/dev/ttyACM0'
    ser = serial.Serial(port, 115200, timeout=5)

    if onoff:
        cmd = f"ON {ch1}" + '\n'
    else:
        cmd = f"OFF {ch1}" + '\n'

    ser.write(cmd.encode('utf-8'))
    res = ser.readline().decode().strip()
    #print (f'{res}')
    time.sleep(0.0)


def pinstat(ch=None, frame=True, color=True):
    port = '/dev/ttyACM0'
    ser = serial.Serial(port, 115200, timeout=5)

    cmd = f"PINSTAT all"+ '\n'
    ser.write(cmd.encode('utf-8'))

    res = ser.readline().decode().strip()
    pins = None
    try:
        pins = parse_first_json_line(res)['pins']
    except ValueError:
        pass

    try:
        pins = [int(i) for i in pins]
        print_with_frame(pins, ch, frame, color)
    except (ValueError, TypeError) as e:
        print (e)
        print(res)


