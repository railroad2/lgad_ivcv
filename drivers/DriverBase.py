import pyvisa

class GPIBBase(): 
    _inst = []

    def open(self, rname):
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(rname)

    def getIDN(self):
        return self._inst.query("*IDN?")

    def reset(self):
        self.inst.write("*RST")

