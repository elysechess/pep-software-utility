import csv

class CSVLogger:
    def __init__(self):
        self.file = open("beans.csv", "w", newline="")
        self.writer = csv.DictWriter(self.file, fieldnames=["adc1", "adc2"])
        self.writer.writeheader()

    def log(self, data):
        self.writer.writerow(data)

    def close(self):
        self.file.close()