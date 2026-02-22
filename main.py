import sys
from PySide6.QtWidgets import QApplication
from mainWindow import MainWindow
from controller.controller import Controller
from usb.usb import USBBackend
from data.csv import CSVLogger

def main():
    app = QApplication(sys.argv)

    usb = USBBackend()
    logger = CSVLogger()
    controller = Controller(usb, logger)


    win = MainWindow(controller)
    win.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


# current speed + target speed on same graph
# DC bus current (DC power lines to the motors) - input power
# motor voltage
# random

# add status updates and faults underneath sample rate in aidan pic 

# change start recording button to stop recording after its clicked

# power 
