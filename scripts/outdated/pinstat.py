#!/usr/bin/env python3

import sys
import time
import serial

def pinstat(frame=True, port='/dev/ttyACM0'):
    PORT = port
    try:
        ch = sys.argv[1]
    except IndexError:
        ch = 'all'

    ser = serial.Serial(PORT, 115200, timeout=0.1)

    cmd = f"PINSTAT {ch}"
    cmd += '\n'

    ser.write(cmd.encode("utf-8"))

    res = ser.readline().decode().strip()
    res = res.split()
 
    if (frame):
        print (' '*3+'| ', end='')
        for i in range(16):
            print (f"{i:2d} ", end='')

        print()
        print ('-'*53)

    for i, r in enumerate(res):
        if (frame):
            if i%16 == 0:
                try:
                    ch = int(ch)
                    print (f"{ch:2d} |  ", end='')
                except ValueError:
                    print (f"{i//16:2d} |  ", end='')


        print (f"{r}  ", end='')
        if i%16 == 15:
            print ()

    #print()

if __name__=="__main__":

    pinstat(1)


