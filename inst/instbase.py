import time
import pyvisa

class InstError(Exception):
    pass

class InstBase:
    _inst = []
    _delay = 0.005
    _read_termination='\r'
    _write_termination='\r'
    _verify_msg=''

    def open(self, rname, read_termination=None, write_termination=None):
        if rname is None:
            raise Exception('An incorrect device has been assigned...')

        if read_termination:
            self._read_termination = read_termination
        if write_termination:
            self._write_termination = write_termination
        
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(rname, 
                                      read_termination=self._read_termination)
        self.verify_inst(self._verify_msg)

    def verify_inst(self, msg):
        if msg not in self.get_idn():
            print ('An incorrect device has been assigned...')
            self._inst = []
            return -1
            #raise Exception('An incorrect device has been assigned...')

        return 0

    def find_inst(self, read_termination=None, msg=None):
        if read_termination is None:
            read_termination = self._read_termination
        
        if msg is None:
            msg = self._verify_msg

        rm = pyvisa.ResourceManager()
        rlist = rm.list_resources()

        for rname in rlist:
            if 'ttyUSB' not in rname:
                continue

            tmp = rm.open_resource(rname, read_termination=read_termination)
            try:
                idn = tmp.query("*idn?")
                tmp.close()
            except pyvisa.VisaIOError as e:
                if e.error_code == pyvisa.constants.VI_ERROR_TMO:
                    print (f"Operation timed out for {rname}")

                tmp.close()
                continue

            if msg not in idn:
                print (idn)
                tmp.close()
                continue 
            else:
                tmp.close()
                print (f"{msg} is found in {idn} from {rname}.")
                del rm
                del tmp
                #self._inst = tmp
                return rname

        return
        

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

    def sleep(self, delay=None):
        if delay:
            time.sleep(delay)
        else:
            time.sleep(self._delay)

    def delay(self):
        self.sleep()

    def set_delay(self, delay):
        self._delay = delay

    def measure(self):
        self.sleep()
        val = self.read()
        val1 = self.parse(val)

        return val1

    def parse(self, val):
        tmp = val.strip()
        tmp = tmp.split(',') 
        val1 = []

        for v in tmp:
            try:
                val1.append(float(v))
            except ValueError:
                val1.append(float(v[:-1])) 

        return val1


