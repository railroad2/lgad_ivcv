import os
import sys
import time
import json
import serial
from serial.tools import list_ports

try:
    from print_utils import print_with_frame, parse_first_json_line
except ModuleNotFoundError:
    from .print_utils import print_with_frame, parse_first_json_line
    

def find_pico_ports():
    """Return a list of candidate serial device names for Pico/MicroPython."""
    candidates = []
    for i in list_ports.comports():
        m = (i.manufacturer or "").lower()
        d = (i.description or "").lower()
        vid = i.vid or 0
        pid = i.pid or 0
        # Heuristics: match on manufacturer/description or known VID/PID
        if (
            "micropython" in m
            or "raspberry" in m
            or "pico" in d
            or "rp2" in d
            or (vid, pid) in {(0x2E8A, 0x0005), (0x2E8A, 0x000A)}  # examples
            ):
            candidates.append(i.device)

    return candidates

def sw_onoff(ch, onoff, port=None):
    if ch is None:
        ch1 = "all"
    elif isinstance(ch, (list, tuple)):
        ch1 = [str(c) for c in ch]
        ch1 = ' '.join(ch1)
    else:
        ch1 = ch

    if port is None:
        port = find_pico_ports()[0] #'/dev/ttyACM0'

    ser = serial.Serial(port, 115200, timeout=5)

    if onoff:
        cmd = f"ON {ch1}" + '\n'
    else:
        cmd = f"OFF {ch1}" + '\n'

    ser.write(cmd.encode('utf-8'))
    res = ser.readline().decode().strip()
    #print (f'{res}')
    time.sleep(0.0)


def pinstat(ch=None, frame=True, color=True, port=None):
    if port is None:
        port = find_pico_ports()[0]

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


