import serial


class USBComm:
    def __init__(self, port):
        self.port = port
        self.ser = None
        self._connect(self.port)

        self.ser_list = []

    def _connect(self, port):
        try:
            self.ser = serial.Serial(port=port, baudrate=115200, timeout=1)
        except serial.serialutil.SerialException:
            print(port, " is not connected")

    def is_connected(self):
        if self.ser is not None:
            return True
        else:
            return False

    def send_data(self, data):
        self.ser.write(f"{data}\r".encode())
        mes = self.ser.read_until().strip()
        return mes.decode()

