#!/usr/bin/env python3

from typing import Iterable, Optional, Union

try:
    from .gatecomm import GateComm
except ImportError:
    from gatecomm import GateComm

try:
    from .print_utils import print_with_frame
except ImportError:
    from print_utils import print_with_frame


DEFAULT_URI = "ws://localhost:8765"


def conv_pinstat(datain):
    if isinstance(datain, str):
        datain = datain.strip()
        if not datain:
            return []
        return [int(i) for i in datain.split()]

    return [int(i) for i in datain]


def _normalize_channels(ch: Union[str, int, Iterable[Union[str, int]]]):
    if isinstance(ch, (list, tuple, set)):
        return [str(c) for c in ch]
    return [str(ch)]


def sw_onoff(ch, onoff, uri: Optional[str] = None):
    comm = GateComm(uri or DEFAULT_URI)
    try:
        comm.connect()

        channels = _normalize_channels(ch)

        if onoff:
            cmd = "ON " + " ".join(channels)
        else:
            if len(channels) == 1 and channels[0].lower() == "all":
                cmd = "ALLOFF"
            else:
                cmd = "OFF " + " ".join(channels)

        return comm.send_data(cmd)

    finally:
        comm.close()


def sw_on(ch, uri: Optional[str] = None):
    return sw_onoff(ch, True, uri=uri)


def sw_off(ch, uri: Optional[str] = None):
    return sw_onoff(ch, False, uri=uri)


def off_all(uri: Optional[str] = None):
    comm = GateComm(uri or DEFAULT_URI)
    try:
        comm.connect()
        return comm.send_data("ALLOFF")
    finally:
        comm.close()


def pinstat(ch=None, frame=True, color=True, uri: Optional[str] = None):
    comm = GateComm(uri or DEFAULT_URI)
    try:
        comm.connect()
        res = comm.send_data("PINSTAT ALL")
        pins = conv_pinstat(res)

        try:
            print_with_frame(pins, ch, frame, color)
        except TypeError:
            print_with_frame(pins)

        return pins

    finally:
        comm.close()


def ping(uri: Optional[str] = None):
    comm = GateComm(uri or DEFAULT_URI)
    try:
        comm.connect()
        return comm.send_data("PING")
    finally:
        comm.close()


def pcfstat(which="ALL", uri: Optional[str] = None):
    comm = GateComm(uri or DEFAULT_URI)
    try:
        comm.connect()
        return comm.send_data(f"PCFSTAT {which}")
    finally:
        comm.close()