from PySide6.QtCore import QObject, Signal, QTimer
import datetime
import csv

class Controller(QObject):
    graph_update = Signal(float, float, float, float)
    dashboard_update = Signal(float, float, float, float, float)
    connection_status_update = Signal(bool)
    send_command_status = Signal(bool)

    def __init__(self, usb):
        super().__init__()
        self.usb = usb

        self.curr_log_file = None
        self.logging_data_fields = {}
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
        
        # Parse entered command
        parsed_cmd = ""
        comm = cmd.split(",")
        if comm[0].upper() == "ESTOP":
            parsed_cmd = "00003000" # xxx 00 000 00000 00000 11000 000000000 --> xxx0 0000 0000 0000 0011 0000 0000 0000
        elif comm[0].upper() == "SETSPEED":
            if len(comm) < 2:
                self.send_command_status.emit(False)
                return
            parsed_cmd = "08183000" # xxx 01 000 00011 00000 11000 000000000 --> xxx0 1000 0001 1000 0011 0000 0000 0000
        elif comm[0].upper() == "RELEASE":
            parsed_cmd = "00003001" # xxx 00 000 00000 00000 11000 000000001 --> xxx0 0000 0000 0000 0011 0000 0000 0001
        else:
            self.send_command_status.emit(False)
            return

        # Send over USB
        self.usb.send(cmd)
        self.send_command_status.emit(True)

    def _start_logging(self, fields, sample_rate):
        
        # Create CSV file
        self.curr_log_file = open("log.csv", "w", newline="")
        self.csv_writer = csv.writer(self.curr_log_file)

        # Write header
        header = ["Timestamp"]
        for field, enabled in fields.items():
            if enabled:
                header.append(field)
        self.csv_writer.writerow(header)

        # Start logging timer
        self.logging_data_fields = fields
        interval_ms = int(1000 / sample_rate)
        self.logging_timer.start(interval_ms)

    def _log(self):
        if not self.latest_data:
            return

        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")
        line = [timestamp]
        for field, enabled in self.logging_data_fields.items():
            if enabled:
                line.append(self.latest_data[field])
        self.csv_writer.writerow(line)

    def _end_logging(self):

        self.curr_log_file.close()
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
