from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from pyqtLE import *
from BMSToolBackend import *
from BMSToolCANWorker import *
from LE import *
import sys
import pyqtgraph as pg
import pyqtgraph.exporters

#baudrates: 125000,       250000,       500000,       1000000
#           125 kBit/sec, 250 kBit/sec, 500 kBit/sec, 1 MBit/sec

currentIndex = 0

fakeCan = {'0xc0': (['00', '00', '00', '00', '01', '00', '00', '00'], 
                    1763154300.3749294), 
            '0xa1': (['26', '01', 'B8', '0B', 'B8', '0B', '18', '02'], 
                    1763154300.375279), 
            '0xa3': (['F3', 'CD', '37', '1F', '10', '00', '00', '00'], 
                    1763154300.3756359), 
            '0xa4': (['00', '00', '00', '00', '00', '01', '00', '00'], 
                    1763154300.375932)
        }

class MainWindow(QWidget):
    # This class' main purpose is to draw the main window and its associated functionality

    comPort = 'COM-1'
    canBaud = 0
    SERIALBAUDRATE = 9600

    baseID = int('B001', 16)
    totalIC = 2 #make this configurable later
    totalCells = 14

    unformattedData = None
    
    def __init__(self):
        # general initilization. Draws what the program looks like before you create or load a file
        
        super().__init__()

        versionNumber = "Beta"

        self.setWindowTitle(f'MR BMS Tool {versionNumber}')

        self.setWindowIcon(QIcon("TempIco.png"))

        self.layout = QGridLayout(self)


        self.candapter = None       # reference to the connected CAN adapter
        self.worker = None


        tabNames = ["Battery Profile",
                    "Diagnostic Trouble Codes",
                    "Live Text Data",
                    "Live Graph/Data Logging",
                    "Live Cell Data",
                    "Live CANBUS Traffic"]

        self.tabSystem = QTabWidget()

        self.tabs = []

        for i in tabNames:
            self.tabs.append(QWidget())

            self.tabSystem.addTab(self.tabs[tabNames.index(i)], i)


        self.tabSystem.tabBarClicked.connect(self.tabIndex)

        '''
        # Left for shame purposes. I spent a month trying to fix the graph only for the problem
        # to be this loop. In an attempt to be efficient I wasted more time. DON'T DO THIS!
        
        for i in self.tabs:
            i.setLayout([self.makeTabZero(), 
                         self.makeTabOne(), 
                         self.makeTabTwo(), 
                         self.makeTabThree(), 
                         self.makeTabFour(), 
                         self.makeTabFive(), 
                         self.makeTabSix()]
                         [self.tabs.index(i)])
        '''


        self.tabs[0].setLayout(self.makeTabZero())
        self.tabs[1].setLayout(self.makeTabOne())
        self.tabs[2].setLayout(self.makeTabTwo())
        self.tabs[3].setLayout(self.makeTabThree())
        self.tabs[4].setLayout(self.makeTabFour())
        self.tabs[5].setLayout(self.makeTabFive())
        #self.tabs[6].setLayout(self.makeTabSix())


        self.layout.addWidget(self.tabSystem)

        self.setLayout(self.layout)


    def closeEvent(self, event):
        self.stopWorker()
        if self.candapter:
            self.candapter.closeCANBus()
        event.accept()


    def updateLiveTextData(self):
        
        if not self.candapter:
            return

        messages = readCANbusToFile(self.candapter,[0x64C,0x6B0,0x6B1,0x6B2])

        if messages:
            for i, msg in enumerate(messages[:min(len(messages), self.dataTable.rowCount())]):
                dataStr = (''.join([f"{b:02X}" for b in msg.data]),msg.arbitration_id)
                
                #print(dataStr[1])

                match dataStr[1]:
                    case 0x64C:
                        #print(dataStr[0])
                        pass

                    case 0x6B0:
                        self.dataTable.setItem(0, 1, QTableWidgetItem( str(int(dataStr[0][8:10], 16) / 2)))
                        
                        self.dataTable.setItem(7, 1, QTableWidgetItem( str(int(dataStr[0][0:2], 16))))
                        
                    case 0x6B1:
                        self.dataTable.setItem(1, 1, QTableWidgetItem( str(int(dataStr[0][2:4], 16))))

                        #self.dataTable.setItem(5, 1, QTableWidgetItem( str(int(dataStr[0][8:10], 16))))

                        #self.dataTable.setItem(6, 1, QTableWidgetItem( str(int(dataStr[0][10:12], 16))))
                        
                    case 0x6B2:
                        self.dataTable.setItem(3, 1, QTableWidgetItem( str(int(dataStr[0][4:6], 16) / 10)))
                        
                        self.dataTable.setItem(4, 1, QTableWidgetItem( str(int(dataStr[0][0:2], 16) / 10)))

                    case _:
                        print(f"How'd we get here?\n{dataStr[1]}")


    def updateTraffic(self):

        global fakeCan
        
    
        if not self.candapter:
            print("setting placeholder data")

            for i in fakeCan.keys():
                
                self.busTraffic.setRowCount(len(fakeCan.keys()))

                self.busTraffic.setItem(list(fakeCan.keys()).index(i), 0, QTableWidgetItem( str(i) ))
                #self.busTraffic.setItem(list(fakeCan.keys()).index(i), 1, QTableWidgetItem( str() ))

                for j in range(8):
                    self.busTraffic.setItem(list(fakeCan.keys()).index(i), j+2, QTableWidgetItem( str(fakeCan[i][0][j]) ))

                self.busTraffic.setItem(list(fakeCan.keys()).index(i), 10, QTableWidgetItem( str() ))
                self.busTraffic.setItem(list(fakeCan.keys()).index(i), 11, QTableWidgetItem( str(fakeCan[i][1]) ))

            self.busTraffic.resizeColumnsToContents()
            self.busTraffic.repaint()

            return


        messages = readCANbusToFile(self.candapter)

        canMessages = {}

        if messages:
            for i, msg in enumerate(messages[:min(len(messages), self.dataTable.rowCount())]):
                dataStr = [hex(msg.arbitration_id), (' '.join([f"{b:02X}" for b in msg.data])).split(), msg.timestamp]

                canMessages[dataStr[0]] = (dataStr[1],dataStr[2])

            for i in canMessages.keys():

                self.busTraffic.setRowCount(len(canMessages.keys()))


                self.busTraffic.setItem(list(canMessages.keys()).index(i), 0, QTableWidgetItem( str(i) ))
                self.busTraffic.setItem(list(canMessages.keys()).index(i), 1, QTableWidgetItem( str() ))



                
                for j in range(8):

                    print(str(canMessages[i][0][j]))

                    self.busTraffic.setItem(list(canMessages.keys()).index(i), j+2, QTableWidgetItem( str(canMessages[i][0][j]) ))
                
                self.busTraffic.setItem(list(canMessages.keys()).index(i), 10, QTableWidgetItem( str() ))
                self.busTraffic.setItem(list(canMessages.keys()).index(i), 11, QTableWidgetItem( str(canMessages[i][1]) ))

        self.busTraffic.repaint()


    def startWorker(self):
        if self.worker and self.worker.isRunning():
            return  # already running
        self.worker = CANWorker(self.candapter)
        self.worker.decodedDataReady.connect(self.onDataReady)
        self.worker.error.connect(lambda e: print(f"[ERROR] {e}"))
        self.worker.start()

    def stopWorker(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.quit()


    def tabIndex(self, index):
        global currentIndex
        currentIndex = index

        if index == 4 and self.candapter:  # only on Live Cell Data tab
            self.startWorker()
        else:
            self.stopWorker()


    def onDataReady(self, ic):
        print(f"onDataReady called, ic length: {len(ic) if ic else None}")
        
        if ic is None:
            print("[WARN] No data received")
            return

        try:
            for row, (ic_dict, cells) in enumerate(ic):
                ic_val = f"{ic_dict['v_segment_V']:.3f}" if ic_dict.get('type') == 'ic_status' else "N/A"
                print(f"Setting row {row}, col 0 to {ic_val}")
                self.cellDataArray[0].setItem(row, 0, QTableWidgetItem(ic_val))

                for col, cell in enumerate(cells, start=1):
                    if cell.get('type') == 'cell':
                        cell_val = f"{cell['voltage_V']:.3f}"
                    else:
                        cell_val = "N/A"
                    print(f"Setting row {row}, col {col} to {cell_val}")
                    self.cellDataArray[0].setItem(row, col, QTableWidgetItem(cell_val))

            print(f"Table rows: {self.cellDataArray[0].rowCount()}, cols: {self.cellDataArray[0].columnCount()}")
            self.cellDataArray[0].viewport().update()
        except (IndexError, TypeError, KeyError) as e:
            print(f"[ERROR] onDataReady failed: {e}")



    def makeGraph(self):
        self.plotGraph = pg.PlotWidget()
        self.plotGraph.showGrid(x=True, y=True)

        # Axis labels (defaults)
        self.plotGraph.setLabel('left', ' ')
        self.plotGraph.setLabel('bottom', ' ')

        # Add legend ONCE
        self.legend = self.plotGraph.addLegend()

        self.plotGraph.setBackground("#292929")

        graphingPen = pg.mkPen(color='#f1b82d', width=2)

        # Create an EMPTY line we will reuse
        self.plotLine = self.plotGraph.plot(
            [],
            [],
            pen=graphingPen,
            #symbol="star",
            #symbolSize=15,
            #symbolBrush="w",
            name="No Data"
        )

        return self.plotGraph

        
    def onAxisSelectionChanged(self):
        yAxis = self.ySelection.currentText()
        xAxis = self.xSelection.currentText()

        print(f"Selected Y: {yAxis}, X: {xAxis}")

        styles = {"color": "white", "font-size": "18px"}

        # Get data for BOTH axes
        xData = self.getXDataForSelection(xAxis)
        yData = self.getYDataForSelection(yAxis)

        # Update axis labels
        self.plotGraph.setLabel('left', yAxis, **styles)
        self.plotGraph.setLabel('bottom', xAxis, **styles)

        # Update plot + legend (Y describes the line)
        self.plotLine.setData(xData, yData, name=yAxis)


    def getXDataForSelection(self, selection):
        returnValues = []
        
        if selection == "Time (min)":
            returnValues = list(range(60))

        # Future examples:
        # elif selection == "Time (sec)":
        #     returnValues = list(range(0, 600, 10))

        return returnValues


    def getYDataForSelection(self, selection):
        returnValues = []
        
        if selection == "Temperature (°C)":
            returnValues = [20 + i * 0.1 for i in range(60)]

        elif selection == "Inverter Temp (°C)":
            returnValues = [30 + i * 0.05 for i in range(60)]

        elif selection == "Pack Voltage (V)":
            returnValues = [350 + i * 0.2 for i in range(60)]

        elif selection == "Pack Amperage (A)":
            returnValues = [10 + i * 0.3 for i in range(60)]

        return returnValues
    
    
    def exportGraphImage(self):
        options = QFileDialog.Options()

        dlg = QMessageBox(self)
        windowTitle = ""
        windowText = ""
        windowIcon = None

        exporter = pg.exporters.ImageExporter(self.plotGraph.plotItem)

        # save to file
        directory = QFileDialog.getSaveFileName(self, "Save File", "", "Image Files (*.png);;All Files (*)", options=options)
        
        if directory[0] != '':
            exporter.export(directory[0])

            windowTitle = "Success!"
            windowText = "The image was exported!"
            windowIcon = QMessageBox.NoIcon

        else:
            windowTitle = "ERROR!"
            windowText = "The image failed failed to export!\nPlease try again."
            windowIcon = QMessageBox.Warning

        
        dlg.setWindowTitle(windowTitle)
        dlg.setText(windowText)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.setIcon(windowIcon)
        dlg.exec()


    def displayErrorCodes(self):
        self.troubleCodeArea.addWidget(QLabel(str(fakeCan)))


    def makeTabZero(self):
        self.tabZeroLayout = QGridLayout()

        self.index = 0

        comSelect = QComboBox()

        refreshButton = PushButtonLE("Refresh")

        comSelect.addItems(verifyCANDAPTERPresent())

        def refreshComPorts():
            comSelect.clear()
            comSelect.addItems(verifyCANDAPTERPresent())

        refreshButton.clicked.connect(refreshComPorts)

        baudSelect = QComboBox()

        baudRates = ["125 kBit/sec", "250 kBit/sec", "500 kBit/sec", "1 MBit/sec"]

        baudSelect.addItems(baudRates)

        items = {
            baudRates[0]: 125_000, 
            baudRates[1]: 250_000, 
            baudRates[2]: 500_000, 
            baudRates[3]: 1_000_000
        }

        connectButton = PushButtonLE("Connect")

        def connectToCAN():
            self.comPort = comSelect.currentText()
            self.canBaud = items.get(baudSelect.currentText())
            self.SERIALBAUDRATE = 9600

            try:
                self.candapter = pyCandapter.pyCandapter(self.comPort, self.SERIALBAUDRATE)
                self.candapter.openCANBus(self.canBaud)
                print("Connected to CAN bus.")
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", str(e))
                self.candapter = None


        connectButton.clicked.connect(connectToCAN)


        self.tabZeroLayout.addWidget(comSelect,0,0)
        self.tabZeroLayout.addWidget(refreshButton,0,1)
        self.tabZeroLayout.addWidget(baudSelect,1,0)

        self.tabZeroLayout.addWidget(connectButton,2,0,1,2)

        return self.tabZeroLayout

    def makeTabOne(self):
        global currentIndex

        self.tabSixLayout = QGridLayout()

        self.index = 1



        self.troubleCodeArea = QVBoxLayout()

        troubleCodeWidget = QWidget()
        troubleCodeWidget.setObjectName("troubleCodeWidget")
        troubleCodeWidget.setLayout(self.troubleCodeArea)


        self.additionalInformationArea = QVBoxLayout()

        additionalInformationWidget = QWidget()
        additionalInformationWidget.setObjectName("additionalInformationWidget")
        additionalInformationWidget.setLayout(self.additionalInformationArea)


        self.activeCellFaultsArea = QVBoxLayout()

        activeCellFaultsWidget = QWidget()
        activeCellFaultsWidget.setObjectName("activeCellFaultsWidget")
        activeCellFaultsWidget.setLayout(self.activeCellFaultsArea)


        self.exportCSV = PushButtonLE("Export Additional Information (CSV)")
        self.clearAllCodes = PushButtonLE("Clear All Codes")

        self.tabSixLayout.addWidget(troubleCodeWidget, 0, 0)
        self.tabSixLayout.addWidget(QLabel("==>"), 0, 1)
        self.tabSixLayout.addWidget(additionalInformationWidget, 0, 2)
        self.tabSixLayout.addWidget(activeCellFaultsWidget, 0, 3)

        self.tabSixLayout.addWidget(QLabel("Code Symbol Legend:"), 1, 0)
        self.tabSixLayout.addWidget(QLabel("(H) = Historical (Past Occurrence)\n(S) = Stored\n(A) = Active\n(F) = Freeze Frame Data Available"), 2, 0)

        self.tabSixLayout.addWidget(self.exportCSV, 1, 2)
        self.tabSixLayout.addWidget(self.clearAllCodes, 4, 0, 1, 4)


        button = PushButtonLE(text='Refresh')
        button.clicked.connect(self.displayErrorCodes)

        self.tabSixLayout.addWidget(button)

        return self.tabSixLayout

    def makeTabTwo(self):
        global currentIndex

        self.tabTwoLayout = QGridLayout()

        self.index = 2

        parameterUnit = [
                        ("Pack State of Charge (SOC)","%"),            # 0x6B0 Byte4
                        ("Pack Discharge Current Limit (DCL)","A"),    # 0x6B1 Byte0 
                        ("Pack Charge Current Limit (CCL)","A"),       # 
                        ("Lowest Cell Voltage","V"),                   # 0x6B2 Byte2
                        ("Highest Cell Voltage","V"),                  # 0x6B2 Byte0
                        ("Highest Battery Temp","C"),                  # 0x6B1 Byte4
                        ("Lowest Battery Temp","C"),                   # 0x6B1 Byte5
                        ("Pack Amperage (Current)","A"),               # 0x6B0 Byte0
                        ("Average Pack Amperage","A"),                 # 
                        ("Pack Voltage","V"),                          # 
                        ("Power Supply (lower than actual)","V"),      # 
                        ("Always-On Power Status",""),                 # 
                        ("Is-Ready Power Status",""),                  # 
                        ("Is-Charging Power Status",""),               # 
                        ("Charge-Enabled Output Active",""),           # 
                        ("Discharge-Enabled Output Active",""),        # 
                        ("Errors Present",""),                         # 
                        ("Is Pack Balancing",""),                      # 
                        ("Time Since Power-On","Sec"),                 # 0x64C
                        ("Time Since Faults Cleared","Min")            # 
                        ]

        self.dataTable = QTableWidget()

        self.dataTable.setColumnCount(3)

        self.dataTable.setRowCount(20)

        self.dataTable.setHorizontalHeaderLabels(["Parameter","Value","Unit"])

        self.dataTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.dataTable.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        for i, (name, unit) in enumerate(parameterUnit):
            itemName = QTableWidgetItem(name)
            itemUnit = QTableWidgetItem(unit)
            self.dataTable.setItem(i, 0, itemName)
            self.dataTable.setItem(i, 2, itemUnit)

        self.dataTable.resizeColumnsToContents()

        self.tabTwoLayout.addWidget(self.dataTable,1,0)

        return self.tabTwoLayout

    def makeTabThree(self):
        self.tabThreeLayout = QGridLayout()
        self.index = 3

        self.ySelection = QComboBox()
        self.ySelection.addItems([
            "Temperature (°C)",
            "Inverter Temp (°C)",
            "Pack Voltage (V)",
            "Pack Amperage (A)"
        ])

        self.xSelection = QComboBox()
        self.xSelection.addItems(["Time (min)"])

        # IMPORTANT: connect selection change
        self.ySelection.currentTextChanged.connect(self.onAxisSelectionChanged)
        self.xSelection.currentTextChanged.connect(self.onAxisSelectionChanged)


        exportButton = PushButtonLE("Export")
        exportButton.clicked.connect(self.exportGraphImage)
        self.tabThreeLayout.addWidget(exportButton, 4, 1)


        # Create graph ONCE
        self.tabThreeLayout.addWidget(self.makeGraph(), 0, 1, 1, 2)

        self.tabThreeLayout.addWidget(QLabel("Y-Axis: "), 2, 1)
        self.tabThreeLayout.addWidget(self.ySelection, 3, 1)

        self.tabThreeLayout.addWidget(QLabel("X-Axis: "), 2, 2)
        self.tabThreeLayout.addWidget(self.xSelection, 3, 2)

        return self.tabThreeLayout

    def makeTabFour(self):
        global currentIndex

        self.tabFourLayout = QGridLayout()

        self.index = 4

        grouping = GroupBoxLE("Live Cell Data")

        groupingLayout = QGridLayout()

        resistanceHigh = QLabel(f"Highest Resistance: {None}")
        resistanceLow = QLabel(f"Lowest Resistance: {None}")
        resistanceAvg = QLabel(f"Avg Cell Resistance: {None}")
        resistanceDelta = QLabel(f"Delta Cell Resistance: {None}")
        groupingLayout.addWidget(resistanceHigh, 0, 0)
        groupingLayout.addWidget(resistanceLow, 1, 0)
        groupingLayout.addWidget(resistanceAvg, 2, 0)
        groupingLayout.addWidget(resistanceDelta, 3, 0)

        voltageHigh = QLabel(f"Highest Cell Volt: {None}")
        voltageLow = QLabel(f"Lowest Cell Volt: {None}")
        voltageAvg = QLabel(f"Avg Cell Volt: {None}")
        voltageDelta = QLabel(f"Delta Cell Volt: {None}")
        groupingLayout.addWidget(voltageHigh, 0, 1)
        groupingLayout.addWidget(voltageLow, 1, 1)
        groupingLayout.addWidget(voltageAvg, 2, 1)
        groupingLayout.addWidget(voltageDelta, 3, 1)

        packSOC = QLabel(f"Pack SOC: {None}")
        packCurrent = QLabel(f"Pack Current: {None}")
        packVoltage = QLabel(f"Pack Voltage: {None}")
        currentLimits = QLabel(f"Current Limits: {None}")
        groupingLayout.addWidget(packSOC, 0, 2)
        groupingLayout.addWidget(packCurrent, 1, 2)
        groupingLayout.addWidget(packVoltage, 2, 2)
        groupingLayout.addWidget(currentLimits, 3, 2)

        liveCellRadio = QRadioButton("Live Cell Voltages")
        openCellRadio = QRadioButton("Open Cell Voltages")
        
        self.typeOfDataGroup = QButtonGroup()

        self.typeOfDataGroup.addButton(liveCellRadio)
        self.typeOfDataGroup.addButton(openCellRadio)

        groupingLayout.addWidget(liveCellRadio, 0, 3)
        groupingLayout.addWidget(openCellRadio, 1, 3)

        liveCellRadio.setChecked(True)


        grouping.setLayout(groupingLayout)



        self.cellDataArray = [ QTableWidget() for i in range(0, 5) ]

        for i in range(len(self.cellDataArray)):

            self.cellDataArray[i].setColumnCount(15)
            self.cellDataArray[i].setRowCount(2)

            self.cellDataArray[i].setHorizontalHeaderLabels(
                ["Segment Voltage" if i == 0 else f"Cell {i}" for i in range(0, 15)]
            )

            #self.cellDataArray.setVerticalHeader()

            self.cellDataArray[i].setEditTriggers(QAbstractItemView.NoEditTriggers)






        self.tabFourLayout.addWidget(grouping, 0, 0, 1, 3)

        for i in range(len(self.cellDataArray)):

            self.tabFourLayout.addWidget(self.cellDataArray[i], i + 1, 0, 1, 3)

        exportLiveCellValues = PushButtonLE(text='Export Live Cell Values (CSV)')
        #exportLiveCellValues.clicked.connect()

        recordData = PushButtonLE(text='Record Data')
        recordData.setIcon(recordData.style().standardIcon(QStyle.SP_MediaPlay))
        #exportLiveCellValues.clicked.connect()

        stopDataRecording = PushButtonLE(text='Stop Recording')
        stopDataRecording.setIcon(stopDataRecording.style().standardIcon(QStyle.SP_MediaStop))
        #exportLiveCellValues.clicked.connect()

        self.tabFourLayout.addWidget(exportLiveCellValues,6,0)
        self.tabFourLayout.addWidget(recordData,6,1)
        self.tabFourLayout.addWidget(stopDataRecording,6,2)

        return self.tabFourLayout

    def makeTabFive(self):
        global currentIndex

        def testingDic():
            global fakeCan

            fakeCan["0xa5"] = (['88', '00', '00', '00', '00', '01', '00', '00'], 
                    1763154300.375932)
            
            fakeCan["0xc0"][0][0] = '88'


        self.tabFiveLayout = QGridLayout()

        self.index = 5

        self.busTraffic = QTableWidget()

        self.busTraffic.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        self.busTraffic.setColumnCount(12)
        self.busTraffic.setRowCount(1)

        self.busTraffic.setHorizontalHeaderLabels(
            [
                "ID",
                "Length",
                "Byte0",
                "Byte1",
                "Byte2",
                "Byte3",
                "Byte4",
                "Byte5",
                "Byte6",
                "Byte7",
                "Count",
                "Timestamp"
            ]
        )

        self.busTraffic.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.tabFiveLayout.addWidget(self.busTraffic,1,0)

        button = PushButtonLE(text='Refresh')
        button.clicked.connect(self.updateTraffic)

        button2 = PushButtonLE(text='Change Placeholders')
        button2.clicked.connect(lambda: testingDic())

        self.tabFiveLayout.addWidget(button)

        self.tabFiveLayout.addWidget(button2)

        return self.tabFiveLayout
    
    '''
    def makeTabSix(self):
        global currentIndex

        self.tabSixLayout = QGridLayout()

        self.index = 6

        return self.tabSixLayout
    '''


    def loadFileButton(self, textBox, fileTypeIndex):
        # loads the file and ensures the data is somewhat valid
        print(textBox)

        options = QFileDialog.Options()

        msg = QMessageBox()

        fileTypes = ["Comma Separated Values (*.csv);;All Files (*)","MP4 (*.mp4);;All Files (*)"]

        directory = QFileDialog.getOpenFileName(self, "Open File", "", fileTypes[fileTypeIndex], options=options)

        if directory[0] != '':
      
            try:
                msg.setText("Successfully loaded file!")
                msg.setWindowTitle("Success")
                msg.exec()

                textBox.setPlainText(directory[0])

            except:
                msg.setText("Could not load Json file.")
                msg.setWindowTitle("Error")
                msg.exec()


if __name__ == "__main__":
    # Executes the app and configures a few small settings

    app = QApplication(sys.argv)

    app.setStyle('Fusion')

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print('running in a PyInstaller bundle')
        stylesheet = loadFile(sys._MEIPASS + "/styles.qss")
    else:
        print('running in a normal Python process')
        stylesheet = loadFile("dev/styles.qss")

    app.setStyleSheet(stylesheet)
    
    window = MainWindow()
    
    window.show()

    sys.exit(app.exec())