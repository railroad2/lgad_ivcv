import numpy as np
import usbcomm 
import wscomm

class SWmat():
    comm = None

    def __init__(self, src): 
        self.comm = None

        if "ttyACM" in src:
            self.comm = usbcomm.USBComm(src)
        elif "ws://" in src:
            self.comm = wscomm.WSComm(src)
        else:
            raise Exception(f"Invalid source {src}")

    def pinstat_all(self):
        pinstat = self.comm.send_data('PINSTAT ALL')
        pinstat = np.array([int(i) for i in pinstat.split()]).reshape(16,16)

        return pinstat

    def on(self, row, col):
        nch = row*16 + col
        recv = self.comm.send_data(f"ON {nch}")
        print (recv)

    def off(self, row, col):
        nch = row*16 + col
        recv = self.comm.send_data(f"OFF {nch}")
        print (recv)

    def off_all(self):
        stat = self.pinstat_all()
        for i in range(16):
            for j in range(16):
                if stat[i][j] == 1:
                    off(i, j)

