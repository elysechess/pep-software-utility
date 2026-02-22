from PySide6.QtCore import QObject, Signal

class Controller(QObject):
    new_sample = Signal(dict)
    connection_status_update = Signal(bool)

    def __init__(self, usb, logger):
        super().__init__()
        self.usb = usb
        self.logger = logger

        self._connect_signals()


    def _connect_signals(self):
        self.usb.message_received.connect(self._handle_message)
        self.usb.connection_changed.connect(self._update_connection_status)
    
    def _connect_usb(self, port):
        self.usb.connect(port)

    def _handle_message(self, message: str):
        packet = self._parse_packet(message)

        if packet:
            print(packet)

            # need to update graph
            # self.new_sample.emit(packet)
            # self.logger.log(packet)

    def _update_connection_status(self, connected : bool):
        self.connection_status_update.emit(connected)

    # Build this out
    def _parse_packet(self, message : str):
        return message

    def _parse_packet(self, raw):
        # Example:
        # [header][adc1][adc2][crc]

        if len(raw) < 6:
            return None

        adc1 = int.from_bytes(raw[1:3], "little")
        adc2 = int.from_bytes(raw[3:5], "little")

        return {
            "adc1": adc1,
            "adc2": adc2
        }