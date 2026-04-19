from PySide6.QtCore import QObject, Signal
import serial
import time
import queue
import threading


class USBBackend(QObject):
    connection_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.ser = None
        self.packet_queue = queue.Queue(maxsize = 10000)
        self.buffer = bytearray()
        self.running = False
        self.PACKET_SIZE = 64

    def connect(self, port: str, baudrate: int = 115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0)
            if not self.ser.is_open:
                raise serial.SerialException("Port failed to open")
            time.sleep(0.1)
            self.running = True
            threading.Thread(target = self._read_loop, daemon = True).start()
            self.connection_changed.emit(True)

        except serial.SerialException:
            self.ser = None
            self.connection_changed.emit(False)

    def disconnect(self):
        self.running = False
        if self.ser:
            self.ser.close()
            self.ser = None
        self.connection_changed.emit(False)

    def send(self, message: str):
        if self.ser:
            self.ser.write(message)

    def _read_loop(self):
        while self.running:
            try:
                if self.ser.in_waiting:
                    chunk = self.ser.read(self.ser.in_waiting)
                    self.buffer.extend(chunk)
                    while len(self.buffer) >= self.PACKET_SIZE:
                        packet = self.buffer[:self.PACKET_SIZE]
                        del self.buffer[:self.PACKET_SIZE]

                        try:
                            self.packet_queue.put_nowait(packet)
                        except queue.Full:
                            try:
                                self.packet_queue.get_nowait()
                                self.packet_queue.put_nowait(packet) # Drop oldest
                                print("Queue full, dropping oldest packet")
                            except:
                                print("Unknown error")
                            
            except:
                self.connection_changed.emit(False)