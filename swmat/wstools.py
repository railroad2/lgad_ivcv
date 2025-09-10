#!/usr/bin/env python3
import time
import json 
import websockets
import asyncio

from .print_pinstat import print_with_frame

uri = 'ws://localhost:3001'
timeout = 5

delay=1

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


