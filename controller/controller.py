from PySide6.QtCore import QObject, Signal

class Controller(QObject):
    graph_update = Signal(float, float, float, float)
    dashboard_update = Signal(float, float, float, float, float)
    connection_status_update = Signal(bool)

    def __init__(self, usb, logger):
        super().__init__()
        self.usb = usb
        self.logger = logger

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

    # Build this out
    def _parse_packet(self, message : str):

        # print(message) 
    
        bv, bc, pva, pvb, pvc, pca, pbc, pcc, ts, a_s, temp = map(float, message.split(","))
        mv = (pva * pvb * pvc) / 3 # motor voltage - must calculate
        mc = (pca * pbc * pcc) / 3 # motor current - must calculate

        self.graph_update.emit(ts, a_s, bc, mv)
        self.dashboard_update.emit(bv, bc, mv, mc, temp)
        # self.logger.log(packet)
