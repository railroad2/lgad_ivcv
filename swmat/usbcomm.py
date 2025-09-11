import serial

class USBComm:
    def __init__(self, port=None):
        self.port = port
        self.ser = None

        self.ser_list = []

    def connect(self, port=None):
        if port is None:
            port = self.port

        try:
            self.ser = serial.Serial(port=port, baudrate=115200, timeout=1)
        except serial.serialutil.SerialException:
            print(port, " is not connected.")

    def is_connected(self):
        return self.ser is not None

    def send_data(self, data):
        self.ser.write(f"{data}\r\n".encode())
        mes = self.ser.read_until().strip()
        return mes.decode()

    def send_data_once(self, data):
        if self.is_connected():
            raise Exception("The port is already connected.")

        with serial.Serial(port=self.port, baudrate=115200, timeout=1) as ser:
            wer.write(f"{data}\r\n".encode())
            mes = self.ser.read_until().strip()
            return mes.decode()

