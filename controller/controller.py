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
        self.idx = 0
        self.motor_voltage_vals = np.zeros(5000)
        self.motor_current_vals = np.zeros(5000)
        self.bus_current_vals = np.zeros(5000)

        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self._process_packets)
        self.processing_timer.start(50) # Process USB buffer every 10 ms

        self.curr_log_file = None
        self.logging_data_fields = {}
        self.latest_data = {}
        self.log_buffer = []

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
        
        # Create CSV file
        self.curr_log_file = open("log.csv", "w", newline="")
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
        self.logging_data_fields = fields

    def _end_logging(self):
        self.curr_log_file.close()

    def _emit_ui_update(self):
        if not self.latest_data:
            return

        motor_voltage = np.sqrt(3) * np.sqrt(np.mean(self.motor_voltage_vals**2) - np.mean(self.motor_voltage_vals)**2)
        motor_current = np.sqrt(np.mean(self.motor_current_vals**2))
        avg_bus_current = np.mean(self.bus_current_vals)

        self.graph_update.emit(
            self.target_speed,
            self.latest_data["speed_rpm"],
            avg_bus_current,
            motor_voltage
        )

        self.dashboard_update.emit(
            self.latest_data["bus_voltage"],
            avg_bus_current,
            motor_voltage,
            motor_current,
            self.latest_data["temperature_c"]
        )

    def _flush_log_buffer(self):
        if len(self.log_buffer) >= 500:  # ~100 ms of data
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

            # print(parsed)

        except struct.error as e:
            print("Parse error:", e)
            return None
        
        self.latest_data = parsed # For logging
        if self.logging_data_fields:
            row = []
            for field, enabled in self.logging_data_fields.items():
                if enabled:
                    if field == "Phase Voltages":
                        row += [parsed["p1_voltage"], parsed["p2_voltage"], parsed["p3_voltage"]]
                    elif field == "Phase Currents":
                        row += [parsed["p1_current"], parsed["p2_current"], parsed["p3_current"]]
                    else:
                        row.append(parsed[field])
            self.log_buffer.append(row)

        self.idx = (self.idx + 1) % 5000
        self.motor_voltage_vals[self.idx] = parsed["p1_voltage"]
        self.motor_current_vals[self.idx] = parsed["p1_current"]
        self.bus_current_vals[self.idx] = parsed["bus_current"]