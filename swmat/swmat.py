import sys
import time
import numpy as np
from urllib.parse import urlparse

from . import wscomm
from . import usbcomm
from . import gatecomm


class SWmat():
    comm = None
    port = None
    delay = 0.5

    def __init__(self, port=None):
        self.comm = None

        if port is not None:
            self.port = port
            self.open(port)

    def open(self, port=None):
        if port is None:
            raise ValueError("port is None")

        if "ttyACM" in port:
            self.comm = usbcomm.USBComm(port)

        elif port.startswith("ws://") or port.startswith("wss://"):
            parsed = urlparse(port)
            ws_port = parsed.port

            if ws_port == 8765:
                self.comm = gatecomm.GateComm(port)
                self.comm.connect()
            else:
                self.comm = wscomm.WSComm(port)

        else:
            raise Exception(f"Invalid port: {port}")

    def close(self):
        if self.comm is not None and hasattr(self.comm, "close"):
            self.comm.close()

    def pinstat_all(self):
        pinstat = self.comm.send_data('PINSTAT ALL')
        pinstat = np.array([int(i) for i in pinstat.split()]).reshape(16,16)
        return pinstat

    def on(self, row, col):
        nch = row*16 + col
        recv = self.comm.send_data(f"ON {nch}")
        if recv is not None:
            print(recv)
        time.sleep(self.delay)

    def off(self, row, col):
        nch = row*16 + col
        recv = self.comm.send_data(f"OFF {nch}")
        if recv is not None:
            print(recv)
        time.sleep(self.delay)

    def off_all(self):
        stat = self.pinstat_all()
        for i in range(16):
            for j in range(16):
                if stat[i][j]:
                    self.off(i, j)