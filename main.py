import sys
from PySide6.QtWidgets import QApplication
from mainWindow import MainWindow

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


# current speed + target speed on same graph
# DC bus current (DC power lines to the motors) - input power
# motor voltage
# random

# make command line smaller, only show last sent command OR error message
# add status updates and faults underneath sample rate in aidan pic 



# power 
