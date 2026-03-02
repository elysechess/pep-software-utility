import sys
from PySide6.QtWidgets import QApplication
from mainWindow import MainWindow
from controller.controller import Controller
from usb.usb import USBBackend

def main():
    app = QApplication(sys.argv)

    usb = USBBackend()
    controller = Controller(usb)


    win = MainWindow(controller)
    win.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()