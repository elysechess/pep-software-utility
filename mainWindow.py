from PySide6.QtWidgets import QMainWindow, QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer
import pyqtgraph as pg
import random
import time

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
        self._start_fake_data()        

    def _load_ui(self):
        file = QFile("ui/utility.ui")
        file.open(QFile.ReadOnly)

        loader = UiLoader()         
        self.ui = loader.load(file, self)

        file.close()

        assert self.ui is not None, "Failed to load UI"
        self.setCentralWidget(self.ui)


    def _setup_plots(self):
        self.plots = []

        for i in range(1, 5):
            plot = getattr(self.ui, f"plot{i}")
            plot.showGrid(x=True, y=True)
            plot.setLabel("left", "Voltage", units="V")
            plot.setLabel("bottom", "Sample")

            curve = plot.plot()
            self.plots.append({"curve": curve, "data": []})

    def _connect_signals(self):
    #     self.ui.sendButton.clicked.connect(self._send_command)
    #     self.ui.terminalInput.returnPressed.connect(self._send_command)
    #     self.ui.startButton.clicked.connect(self._start_recording)
    #     self.ui.stopButton.clicked.connect(self._stop_recording)
        self.ui.terminalLineEdit.returnPressed.connect(self._send_command)
        self.controller.new_sample.connect(self._update_graphs)
        self.controller.status_message.connect(self._show_message)

    def _send_command(self):
        cmd = self.ui.terminalLineEdit.text()
        if not cmd:
            return
        self._update_terminal(cmd)
        self.ui.terminalLineEdit.clear()
        print(cmd)

        # this is where you'd emit to USB worker

    def _update_terminal(self, new_cmd):
        self.ui.termLabel5.setText(self.ui.termLabel4.text())
        self.ui.termLabel4.setText(self.ui.termLabel3.text())
        self.ui.termLabel3.setText(self.ui.termLabel2.text())
        self.ui.termLabel2.setText(self.ui.termLabel1.text())
        self.ui.termLabel1.setText(new_cmd)


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
        for p in self.plots:
            data = p["data"]
            data.append(random.uniform(0, 3.3))
            data[:] = data[-200:]  # keep last 200 points
            p["curve"].setData(data)