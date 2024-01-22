import time
import pyvisa

class GPIBBase(): 
    _inst = []
    _delay = 0.005

    def open(self, rname):
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(rname)

    def get_idn(self):
        return self._inst.query("*IDN?")

    def reset(self):
        self._inst.write("*RST")

    def query(self, line):
        return self._inst.query(line)

    def read(self):
        return self._inst.query(":READ?") 

    def write(self, line):
        self._inst.write(line)
        return

    def sleep(self):
        time.sleep(self._delay)

    def delay(self):
        self.sleep()

    def set_delay(self, delay):
        self._delay = delay

    def measure(self):
        self.sleep()
        val = read()
        val1 = self.parse(val)

        return val1

    def parse(self, val):
        tmp = val.strip()
        tmp = tmp.split(',') 
        val1 = []

        for v in val:
            try:
                val1.append(float(v))
            except ValueError:
                val1.append(float(v[:-1])) 

        return val1


