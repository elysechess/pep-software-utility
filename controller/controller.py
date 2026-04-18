from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QFileDialog
import datetime
import csv
import numpy as np
import struct

class Controller(QObject):
    graph_update = Signal(float, float, float, float)
    dashboard_update = Signal(float, float, float, float, float)
    fw_update = Signal(int, int)
    connection_status_update = Signal(bool)
    send_command_status = Signal(bool)

    def __init__(self, usb):
        super().__init__()
        self.usb = usb

        self.FORMAT = "<I10f2I"   # little-endian
        self.PACKET_SIZE = struct.calcsize(self.FORMAT)
        self.target_speed = 0
        self.idx = 0
        self.motor_voltage_pA_vals = np.zeros(5000)
        self.motor_voltage_pB_vals = np.zeros(5000)
        self.motor_current_vals = np.zeros(5000)
        self.bus_current_vals = np.zeros(5000)

        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self._process_packets)
        self.processing_timer.start(50) # Process USB buffer every 10 ms

        self.curr_log_file = None
        self.logging_data_fields = []
        self.latest_data = {}
        self.log_buffer = []
        self.logging = False

        self._connect_signals()

    def _connect_signals(self):
        self.usb.connection_changed.connect(self._update_connection_status)
    
    def _connect_usb(self, port):
        self.usb.connect(port)     

    def _disconnect_usb(self):
        self.usb.disconnect()

    def _update_connection_status(self, connected : bool):
        self.connection_status_update.emit(connected)

    def send_message(self, cmd):
        
        # Parse entered command (all commands should be 6 bytes)
        parsed_cmd = None
        speed = 0
        comm = cmd.split(",")
        if comm[0].upper() == "ESTOP":
            parsed_cmd = 0x00003000 # xxx 00 000 00000 00000 11000 000000000 --> xxx0 0000 0000 0000 0011 0000 0000 0000 
        elif comm[0].upper() == "SETSPEED":
            if len(comm) < 2:
                self.send_command_status.emit(False)
                return
            parsed_cmd = 0x08183000 # xxx 01 000 00011 00000 11000 000000000 --> xxx0 1000 0001 1000 0011 0000 0000 0000 
            speed = int(comm[1])
            self.target_speed = int(comm[1])
        elif comm[0].upper() == "RELEASE":
            parsed_cmd = 0x00003001 # xxx 00 000 00000 00000 11000 000000001 --> xxx0 0000 0000 0000 0011 0000 0000 0001 
        else:
            self.send_command_status.emit(False)
            return

        # Send over USB
        message = struct.pack(">I", parsed_cmd) + struct.pack(">h", speed) # 2 bytes speed data - used for SETSPEED
        self.usb.send(message)
        self.send_command_status.emit(True)

    def _process_packets(self):
        packets = []
        while not self.usb.packet_queue.empty():
            packets.append(self.usb.packet_queue.get()) # Drain queue
        if packets:
            # print(packets)
            pass

        if not packets:
            return
    
        for packet in packets:
            self._parse_packet(packet)
        self._flush_log_buffer()
        self._emit_ui_update()

    def _start_logging(self, fields):
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Log File",
            datetime.datetime.now().strftime("log_%Y%m%d_%H%M%S.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )

        # If user cancels, do nothing
        if not file_path:
            return

        # Create CSV file
        self.curr_log_file = open(file_path, "w", newline="")
        self.csv_writer = csv.writer(self.curr_log_file)

        # Write header
        header = ["Timestamp"]
        for field, enabled in fields.items():
            if enabled:
                if field == "Phase Voltages":
                    header += ["Phase Voltage A", "Phase Voltage B", "Phase Voltage C"]
                elif field == "Phase Currents":
                    header += ["Phase Current A", "Phase Current B", "Phase Current C"]
                else:
                    header.append(field)
        self.csv_writer.writerow(header)
        self.logging_data_fields = header
        self.logging = True

    def _end_logging(self):
        self.logging = False
        self.curr_log_file.close()

    def _emit_ui_update(self):
        if not self.latest_data:
            return

        motor_voltage = np.sqrt(np.mean((self.motor_voltage_pA_vals - self.motor_voltage_pB_vals)**2)) 
        motor_current = np.sqrt(np.mean(self.motor_current_vals**2))
        avg_bus_current = np.mean(self.bus_current_vals)

        self.graph_update.emit(
            self.target_speed,
            self.latest_data["Actual Speed"],
            avg_bus_current,
            motor_voltage
        )

        self.dashboard_update.emit(
            self.latest_data["Bus Voltage"],
            avg_bus_current,
            motor_voltage,
            motor_current,
            self.latest_data["Board Temperature"]
        )

        self.fw_update.emit(
            self.latest_data["Warning Mask"], 
            self.latest_data["Fault Mask"]
        )

    def _flush_log_buffer(self):
        if self.logging and len(self.log_buffer) >= 500:  # ~100 ms of data
            self.csv_writer.writerows(self.log_buffer)
            self.log_buffer.clear()

    # All data is 32 bit floating point
    # Timestamp: 32 bit unsigned int
    # Order: timestamp, bus voltage (V), bus current (A), P1 voltage, P1 current, P2 voltage, P2 current, P3 voltage, P3 current, speed (rpm), temperature (degrees Celsius), fault mask, warning mask  
    def _parse_packet(self, message):

        # print(message) 
        if len(message) != 64:
            return

        # if len(message) < PACKET_SIZE:
        #     print("Incomplete packet")
        #     return None

        try:

            # Unpack hex message
            unpacked = struct.unpack(self.FORMAT, message[:self.PACKET_SIZE])
            parsed = {
                "Timestamp": unpacked[0],
                "Bus Voltage": unpacked[1],
                "Bus Current": unpacked[2],
                "Phase Voltage A": unpacked[3],
                "Phase Current A": unpacked[4],
                "Phase Voltage B": unpacked[5],
                "Phase Current B": unpacked[6],
                "Phase Voltage C": unpacked[7],
                "Phase Current C": unpacked[8],
                "Actual Speed": unpacked[9],
                "Board Temperature": unpacked[10],
                "Fault Mask": unpacked[11],
                "Warning Mask": unpacked[12],
            }

            # print(parsed)

        except struct.error as e:
            print("Parse error:", e)
            return None
        
        self.latest_data = parsed # For logging
        if self.logging_data_fields:
            row = []
            for field in self.logging_data_fields:
                row.append(parsed[field])
            self.log_buffer.append(row)

        self.idx = (self.idx + 1) % 5000
        self.motor_voltage_pA_vals[self.idx] = parsed["Phase Voltage A"]
        self.motor_voltage_pB_vals[self.idx] = parsed["Phase Voltage B"]
        self.motor_current_vals[self.idx] = parsed["Phase Current A"]
        self.bus_current_vals[self.idx] = parsed["Bus Current"]