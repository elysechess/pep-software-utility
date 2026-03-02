from PySide6.QtCore import QObject, Signal, QTimer
import time

class Controller(QObject):
    graph_update = Signal(float, float, float, float)
    dashboard_update = Signal(float, float, float, float, float)
    connection_status_update = Signal(bool)

    def __init__(self, usb):
        super().__init__()
        self.usb = usb

        self.latest_data = {}
        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self._log)

        self._connect_signals()

    def _connect_signals(self):
        self.usb.message_received.connect(self._parse_packet)
        self.usb.connection_changed.connect(self._update_connection_status)
    
    def _connect_usb(self, port):
        self.usb.connect(port)     

    def _disconnect_usb(self):
        self.usb.disconnect()

    def _update_connection_status(self, connected : bool):
        self.connection_status_update.emit(connected)

    def send_message(self, cmd):
        self.usb.send(cmd)

    def _start_logging(self, fields, sample_rate):
        
        # Create CSV file

        # Start logging timer
        interval_ms = int(1000 / sample_rate)
        self.logging_timer.start(interval_ms)

    def _log(self):

        # log self.latest_data
        print("logignf")

    def _end_logging(self):

        # Stop logging timer
        self.logging_timer.stop()

    # Build this out
    def _parse_packet(self, message : str):

        # print(message) 
    
        bv, bc, pva, pvb, pvc, pca, pcb, pcc, ts, a_s, temp = map(float, message.split(","))
        mv = (pva * pvb * pvc) / 3 # motor voltage - must calculate
        mc = (pca * pcb * pcc) / 3 # motor current - must calculate

        self.latest_data = {
            "Bus Voltage": bv,
            "Bus Current": bc,
            "Phase Voltages": [pva, pvb, pvc],
            "Phase Currents": [pca, pcb, pcc],
            "Target Speed": ts,
            "Actual Speed": a_s,
            "Board Temperature": temp,
            "Fault Mask": None,
            "Warning Mask": None
        }

        self.graph_update.emit(ts, a_s, bc, mv)
        self.dashboard_update.emit(bv, bc, mv, mc, temp)
