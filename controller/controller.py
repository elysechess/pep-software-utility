from PySide6.QtCore import QObject, Signal, QTimer
import datetime
import csv
import numpy as np
import struct

class Controller(QObject):
    graph_update = Signal(float, float, float, float)
    dashboard_update = Signal(float, float, float, float, float)
    connection_status_update = Signal(bool)
    send_command_status = Signal(bool)

    def __init__(self, usb):
        super().__init__()
        self.usb = usb

        self.FORMAT = "<I10f2I"   # little-endian
        self.PACKET_SIZE = struct.calcsize(self.FORMAT)
        self.target_speed = 0
        self.motor_voltage_vals = np.zeros(5000)
        self.motor_current_vals = np.zeros(5000)

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
        
        # Parse entered command (all commands should be 6 bytes)
        parsed_cmd = None
        speed = 0
        comm = cmd.split(",")
        if comm[0].upper() == "ESTOP":
            parsed_cmd = 0x00003000 # xxx 00 000 00000 00000 11000 000000000 --> xxx0 0000 0000 0000 0011 0000 0000 0000 + no extra data
        elif comm[0].upper() == "SETSPEED":
            if len(comm) < 2:
                self.send_command_status.emit(False)
                return
            parsed_cmd = 0x08183000 # xxx 01 000 00011 00000 11000 000000000 --> xxx0 1000 0001 1000 0011 0000 0000 0000 + 2 bytes extra data
            speed = int(comm[1])
            target_speed = int(comm[1])
        elif comm[0].upper() == "RELEASE":
            parsed_cmd = 0x00003001 # xxx 00 000 00000 00000 11000 000000001 --> xxx0 0000 0000 0000 0011 0000 0000 0001 + no extra data
        else:
            self.send_command_status.emit(False)
            return

        # Send over USB
        message = struct.pack(">I", parsed_cmd) + struct.pack(">h", speed)
        self.usb.send(message)
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

    # All data is 32 bit floating point
    # Timestamp: 32 bit unsigned int
    # Order: timestamp, bus voltage (V), bus current (A), P1 voltage, P1 current, P2 voltage, P2 current, P3 voltage, P3 current, speed (rpm), temperature (degrees Celsius), fault mask, warning mask  
    # SET UP QUEUE - PERIODIC UPDATE
    def _parse_packet(self, message):

        print(message) 

        # if len(message) < PACKET_SIZE:
        #     print("Incomplete packet")
        #     return None

        try:

            # Unpack hex message
            unpacked = struct.unpack(self.FORMAT, message[:self.PACKET_SIZE])
            parsed = {
                "timestamp": unpacked[0],
                "bus_voltage": unpacked[1],
                "bus_current": unpacked[2],
                "p1_voltage": unpacked[3],
                "p1_current": unpacked[4],
                "p2_voltage": unpacked[5],
                "p2_current": unpacked[6],
                "p3_voltage": unpacked[7],
                "p3_current": unpacked[8],
                "speed_rpm": unpacked[9],
                "temperature_c": unpacked[10],
                "fault_mask": unpacked[11],
                "warning_mask": unpacked[12],
            }

            print(parsed)

        except struct.error as e:
            print("Parse error:", e)
            return None

        # Calculate motor voltage
        self.motor_voltage_vals = parsed["p1_voltage"] + self.motor_voltage_vals[1:] 
        motor_voltage = np.sqrt(np.mean(self.motor_voltage_vals**2) - np.mean(self.motor_voltage_vals)**2)

        # Calculate motor current
        self.motor_current_vals = parsed["p1_current"] + self.motor_current_vals[1:] 
        motor_current = np.sqrt(np.mean(self.motor_current_vals**2))

        self.latest_data = parsed # For logging
        self.graph_update.emit(self.target_speed, parsed["speed_rpm"], parsed["bus_current"], motor_voltage)
        self.dashboard_update.emit(parsed["bus_voltage"], parsed["bus_current"], motor_voltage, motor_current, parsed["temperature_c"])