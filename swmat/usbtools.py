import serial
from .print_pinstat import print_with_frame

def sw_onoff(ch, onoff):
    if ch is None:
        ch1 = "all"
    else:
        ch1 = ch

    port = '/dev/ttyACM0'
    ser = serial.Serial(port, 115200, timeout=5)

    for c in ch1:
        if onoff:
            cmd = f"ON {c}" + '\n'
        else:
            cmd = f"OFF {c}" + '\n'

        ser.write(cmd.encode('utf-8'))
        res = ser.readline().decode().strip()
        print (res)


def pinstat(ch=None, frame=True, color=True):
    port = '/dev/ttyACM0'
    ser = serial.Serial(port, 115200, timeout=5)

    cmd = f"PINSTAT all"+ '\n'
    ser.write(cmd.encode('utf-8'))

    res = ser.readline().decode().strip()
    res = res.split()
    try:
        res = [int(i) for i in res]
        print_with_frame(res, ch, frame, color)
    except ValueError:
        print(res)

