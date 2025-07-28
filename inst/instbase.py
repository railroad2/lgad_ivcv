import time
import pyvisa


class InstBase:
    _inst = []
    _delay = 0.005
    _read_termination='\r'
    _verify_msg=''

    def open(self, rname, read_termination=None):
        if read_termination:
            self._read_termination = read_termnation
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(rname, read_termination=read_termination)
        self.verify_inst(self._verify_msg)

    def verify_inst(self, msg):
        if msg not in self.get_idn():
            print ('An incorrect device has been assigned...')
            self._inst = []
            return -1

        return 0

    def close(self):
        self._inst.close()
        return
        
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


