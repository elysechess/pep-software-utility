from PySide6.QtCore import QObject, Signal, QTimer
import serial
import time


class USBBackend(QObject):
    message_received = Signal(str)
    connection_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.ser = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._read_serial)

    def connect(self, port: str, baudrate: int = 115200):
        try:
            print(port)
            self.ser = serial.Serial(port, baudrate, timeout=0)

            if not self.ser.is_open:
                raise serial.SerialException("Port failed to open")

            time.sleep(2)
            self.timer.start(10)
            self.connection_changed.emit(True)

        except serial.SerialException:
            self.ser = None
            self.connection_changed.emit(False)

    def disconnect(self):
        if self.ser:
            self.timer.stop()
            self.ser.close()
            self.ser = None
        self.connection_changed.emit(False)

    def send(self, message: str):
        if self.ser:
            self.ser.write((message + "\n").encode())

    def _read_serial(self):
        if self.ser and self.ser.in_waiting:
            try:
                line = self.ser.readline().decode().strip()
                if line:
                    print(line)
                    self.message_received.emit(line)
            except UnicodeDecodeError:
                pass