from PySide6.QtCore import QThread, Signal
from BMSToolBackend import *

class CANWorker(QThread):
    formattedDataReady = Signal(object)  # emits ic data when done
    decodedDataReady = Signal(object)
    error = Signal(str)

    def __init__(self, candapter, msgLen=29):
        super().__init__()
        self.candapter = candapter
        self.msgLen = msgLen

    def run(self):
        while not self.isInterruptionRequested():
            #print("Worker loop iteration")  # add this
            try:
                ic = formatCANMessage(self.candapter, self.msgLen)
                decodedIC = decode_formatted_data(ic)
                self.formattedDataReady.emit(ic)
                self.decodedDataReady.emit(decodedIC)
            except Exception as e:
                self.error.emit(str(e))
            self.msleep(100)