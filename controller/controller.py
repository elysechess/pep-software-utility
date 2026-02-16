from PySide6.QtCore import QObject, Signal

class Controller(QObject):
    new_sample = Signal(dict)
    status_message = Signal(str)

    def __init__(self, usb, logger):
        super().__init__()
        self.usb = usb
        self.logger = logger

        self.usb.raw_packet_received.connect(self._handle_raw_packet)

    def _handle_raw_packet(self, raw: bytes):
        packet = self._parse_packet(raw)

        if packet:
            self.new_sample.emit(packet)
            self.logger.log(packet)

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