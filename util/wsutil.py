#!/usr/bin/env python3
import time
import json 
import websockets
import asyncio
from collections.abc import Iterable

uri = 'ws://localhost:3001'
timeout = 5

GREEN = "\033[1;32m"
RED   = "\033[31m"
BLUE  = "\033[1;34m"
RESET = "\033[0m"

delay=1

def print_colored(pin, end=None):
    if pin:
        print (GREEN + f"{pin}" + RESET, end=' ')
    else:
        print (RED   + f"{pin}" + RESET, end=' ');

def print_with_frame(pins, ch=None, frame=True, colored=True, cols=16):
    noheadflg  = True
    noprintflg = True
    
    for i, pin in enumerate(pins):
        if (ch is not None) and (i//cols not in ch): 
            continue

        if (noheadflg and frame):
            print (' '*3+'| ', end='')

            for j in range(cols):
                print (f"{j:2d} ", end='')

            print ('\n'+'-'*53)
            noheadflg = False

        if i%cols == 0 and frame:
            print (f"{i//16:2d} |  ", end='')

        if colored:
            print_colored(pin, end='')
        else: 
            print (f"{pin} ", end='')

        if frame: print (end=' ')

        noprintflg = False

        if i%cols == cols - 1:
            print ()

    if (noprintflg):
        print ("The pcfid out of range.")

def conv_pinstat(datain):
    pinstat = [int(i) for i in datain]
    return pinstat

async def send_data_once(data):
    async with websockets.connect(uri, ping_interval=None, open_timeout=timeout) as ws:
        await asyncio.wait_for(ws.send(data), timeout=timeout)
        await asyncio.sleep(0.1)
        response = await asyncio.wait_for(ws.recv(), timeout=timeout)

    responsed = json.loads(response)['pins']
    
    pins = conv_pinstat(responsed)
    
    return pins

async def sw_onoff(ch, onoff):
    val = True if onoff else False

    payload = {"cmd":"get"}
    res = await send_data_once(json.dumps(payload))

    for c in ch:
        payload = {"cmd":"set", "ch":c, "val":val}
        res = await send_data_once(json.dumps(payload))
        time.sleep(0.1)

async def pinstat(ch, frame=True, color=True):
    payload = {"cmd":"get"}
    res = await send_data_once(json.dumps(payload))
    time.sleep(0.1)
    print_with_frame(res)


