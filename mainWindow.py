from PySide6.QtWidgets import QMainWindow, QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer
import pyqtgraph as pg
import random
import time
import serial.tools.list_ports

class UiLoader(QUiLoader):
    def createWidget(self, className, parent=None, name=""):
        if className == "PlotWidget":
            widget = pg.PlotWidget(parent)
            widget.setObjectName(name)
            return widget
        return super().createWidget(className, parent, name)
    
class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self._load_ui()
        self._setup_plots()
        self._connect_signals()
        self._refresh_ports()
        # self._start_fake_data()        

    def _load_ui(self):
        file = QFile("ui/utility.ui")
        file.open(QFile.ReadOnly)

        loader = UiLoader()         
        self.ui = loader.load(file, self)

        file.close()

        assert self.ui is not None, "Failed to load UI"
        self.setCentralWidget(self.ui)


    def _setup_plots(self):
        self.plots = {}

        # ----- Plot 1 (two curves) -----
        plot1 = self.ui.plot1
        plot1.showGrid(x=True, y=True)
        plot1.setLabel("left", "Current + Target Speed", units="rpm")
        plot1.setLabel("bottom", "Sample")

        curve1_a = plot1.plot(pen="r")   # red
        curve1_b = plot1.plot(pen="b")   # blue

        self.plots["plot1"] = {
            "curves": [curve1_a, curve1_b],
            "data": [[], []]
        }

        # ----- Plot 2 (one curve) -----
        plot2 = self.ui.plot2
        plot2.showGrid(x=True, y=True)
        plot2.setLabel("left", "DC Bus Current", units="A")
        plot2.setLabel("bottom", "Sample")

        curve2 = plot2.plot(pen="g")   # green

        self.plots["plot2"] = {
            "curves": [curve2],
            "data": [[]]
        }

        # ----- Plot 3 (one curve) -----
        plot3 = self.ui.plot3
        plot3.showGrid(x=True, y=True)
        plot3.setLabel("left", "Motor Voltage", units="V")
        plot3.setLabel("bottom", "Sample")

        curve3 = plot3.plot(pen="y")   # yellow

        self.plots["plot3"] = {
            "curves": [curve3],
            "data": [[]]
        }

    def _connect_signals(self):
        # self.ui.recordButton.clicked.connect(self._record_session)
        self.ui.terminalLineEdit.returnPressed.connect(self._send_command)
        self.ui.connectButton.clicked.connect(self._connect_to_board)
        self.controller.graph_update.connect(self._update_graphs)
        self.controller.dashboard_update.connect(self._update_dashboard)
        self.controller.connection_status_update.connect(self._log_connection_status)

    def _log_connection_status(self, connected : bool):
        if connected:
            self._update_terminal("Connection established")
        else:
            self._update_terminal("No connection established")

    def _refresh_ports(self):

        self.ui.COMselect.clear()

        ports = serial.tools.list_ports.comports()

        if not ports:
            self.ui.COMselect.addItem("No ports found")
            self.ui.COMselect.setEnabled(False)
            return

        self.ui.COMselect.setEnabled(True)

        for port in ports:
            display_text = f"{port.device} - {port.description}"
            self.ui.COMselect.addItem(display_text, port.device)

    def _send_command(self):
        cmd = self.ui.terminalLineEdit.text()
        if not cmd:
            return
        self._update_terminal(cmd)
        self.ui.terminalLineEdit.clear()
        # print(cmd)

        # this is where you'd emit to USB worker
        self.controller.send_message(cmd)

    def _connect_to_board(self):
        if self.ui.connectButton.text() == "CONNECT TO BOARD":
            port = self.ui.COMselect.currentData()
            self.controller._connect_usb(port)
            self.ui.connectButton.setText("DISCONNECT FROM BOARD")
        else:
            self.controller._disconnect_usb()
            self.ui.connectButton.setText("CONNECT TO BOARD")

    def _update_terminal(self, new_cmd):
        self.ui.termLabel5.setText(self.ui.termLabel4.text())
        self.ui.termLabel4.setText(self.ui.termLabel3.text())
        self.ui.termLabel3.setText(self.ui.termLabel2.text())
        self.ui.termLabel2.setText(self.ui.termLabel1.text())
        self.ui.termLabel1.setText(new_cmd)

    def _update_graphs(self, p1, p2, p3, p4):


        # ----- Plot 1 (two curves) -----
        plot1 = self.plots["plot1"]
        plot1["data"][0].append(p1)
        plot1["data"][1].append(p2)

        plot1["data"][0] = plot1["data"][0][-200:]
        plot1["data"][1] = plot1["data"][1][-200:]

        plot1["curves"][0].setData(plot1["data"][0])
        plot1["curves"][1].setData(plot1["data"][1])

        # ----- Plot 2 -----
        plot2 = self.plots["plot2"]
        plot2["data"][0].append(p3)
        plot2["data"][0] = plot2["data"][0][-200:]
        plot2["curves"][0].setData(plot2["data"][0])

        # ----- Plot 3 -----
        plot3 = self.plots["plot3"]
        plot3["data"][0].append(p4)
        plot3["data"][0] = plot3["data"][0][-200:]
        plot3["curves"][0].setData(plot3["data"][0])

    def _update_dashboard(self, bv, bc, mv, mc, temp):
        self.ui.busVoltage.setText(f"{bv:.2f}")
        self.ui.busCurrent.setText(f"{bc:.2f}")

        bp = bv * bc
        self.ui.busPower.setText(f"{bp:.2f}")

        self.ui.motorVoltage.setText(f"{mv:.2f}")
        self.ui.motorCurrent.setText(f"{mc:.2f}")

        mp = mv * mc
        self.ui.motorPower.setText(f"{mp:.2f}")

        efficiency = bp / mp if mp != 0 else 0
        self.ui.efficiency.setText(f"{efficiency:.2f}")

        self.ui.temperature.setText(f"{temp:.2f}")


    # def _start_recording(self):
    #     self.ui.terminalOutput.appendPlainText("Recording started")

    # def _stop_recording(self):
    #     self.ui.terminalOutput.appendPlainText("Recording stopped")


    # REMOVE once USB data input works
    def _start_fake_data(self):
        self.start_time = time.time()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_fake_data)
        self.timer.start(50)  # 20 Hz

    # REMOVE once USB data input works
    def _update_fake_data(self):

        # ----- Plot 1 (two curves) -----
        plot1 = self.plots["plot1"]
        plot1["data"][0].append(random.uniform(0, 3.3))
        plot1["data"][1].append(random.uniform(0, 3.3))

        plot1["data"][0] = plot1["data"][0][-200:]
        plot1["data"][1] = plot1["data"][1][-200:]

        plot1["curves"][0].setData(plot1["data"][0])
        plot1["curves"][1].setData(plot1["data"][1])

        # ----- Plot 2 -----
        plot2 = self.plots["plot2"]
        plot2["data"][0].append(random.uniform(0, 3.3))
        plot2["data"][0] = plot2["data"][0][-200:]
        plot2["curves"][0].setData(plot2["data"][0])

        # ----- Plot 3 -----
        plot3 = self.plots["plot3"]
        plot3["data"][0].append(random.uniform(0, 3.3))
        plot3["data"][0] = plot3["data"][0][-200:]
        plot3["curves"][0].setData(plot3["data"][0])