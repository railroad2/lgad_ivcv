#!/usr/bin/env python3
from swm_ctrl.websocket_client import parse_pin_tokens

try:
    from .print_utils import print_with_frame
    from .protocol import col_pins, row_pins
    from .wscomm import WSComm
except ImportError:
    from print_utils import print_with_frame
    from protocol import col_pins, row_pins
    from wscomm import WSComm

uri = 'ws://localhost:3001'
timeout = 5

def conv_pinstat(datain):
    return [int(i) for i in datain]


async def send_data_once(data):
    return await WSComm(uri=uri, timeout=timeout).send_data_once(data)


async def sw_onoff(ch, onoff):
    if isinstance(ch, str) and ch.strip().lower() == "all":
        if onoff:
            raise ValueError("Turning all pins on is not supported")
        command = {"cmd": "ALLOFF"}
    else:
        tokens = (ch,) if isinstance(ch, (str, int)) else tuple(ch)
        pins = parse_pin_tokens(tokens)
        command = {"cmd": "ON" if onoff else "OFF", "pins": pins}

    return await send_data_once(command)


async def on_row(row):
    return await sw_onoff(row_pins(row), True)


async def off_row(row):
    return await sw_onoff(row_pins(row), False)


async def on_col(col):
    return await sw_onoff(col_pins(col), True)


async def off_col(col):
    return await sw_onoff(col_pins(col), False)


async def pinstat(ch=None, frame=True, color=True):
    response = await send_data_once({"cmd": "PINSTAT", "which": "ALL"})
    pins = conv_pinstat(response["pins"])
    print_with_frame(pins, ch, frame, color)
    return pins
