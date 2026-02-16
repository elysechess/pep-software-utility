from PySide6.QtCore import QObject, Signal
import serial

class USBBackend(QObject):
    raw_packet_received = Signal(bytes)
    connection_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.ser = None

    def connect(self, port):
        self.ser = serial.Serial(port, 115200)
        self.connection_changed.emit(True)

    def disconnect(self):
        if self.ser:
            self.ser.close()
        self.connection_changed.emit(False)

    def poll(self):
        if self.ser and self.ser.in_waiting:
            data = self.ser.read(self.ser.in_waiting)
            self.raw_packet_received.emit(data)

    def send(self, data: bytes):
        if self.ser:
            self.ser.write(data)