#############################################################################
#Integration system of step motor, dro, and user interface
#2024 Fall
#############################################################################

#Library -----------------------------------------------------------------------
import serial
import matplotlib.pyplot as plt
import pyqtgraph as pg
from random import randint
import numpy as np
import pandas as pd
import time
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import qdarktheme
try:
    import Queue
except:
    import queue as Queue
import sys, time, serial
import json

import PyQt6.QtCore as QtCore
from PyQt6.QtCore import QDateTime, Qt, QTimer
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget, QPlainTextEdit, QTableWidgetItem, QScrollArea,
        QFormLayout, QHeaderView)
from PyQt6 import QtGui
from animated_toggle import AnimatedToggle

#Global variable ---------------------------------------------------------------------
SER_TIMEOUT = 0.1  # Timeout for serial Rx
MAIN_UI = None
PULSE_DRO = [] #Record the coordinates from router by time
PLOT_TIME_FRAME = 200
PLOT_UPDATE_INTERVAL = 0.01
RECORD_INDEX = 0
START_TIME = 0
RECORD_TIME = {} #Define a dictionary to record the time enabling hall sensor
PLOT_UPDATE_BOOL = False
TEXT_UPDATE_BOOL = False
#-------------------------------------------------------------------------------------

#Thread for updating plot and text displayed on main UI within a defined period
class PlotUpdateWorker(QtCore.QRunnable):

    def __init__(self): # Initialise with serial port details
        QtCore.QThread.__init__(self)
        self.running = True
        self.text_update_bool = False
        self.plot_update_bool = False
        self.pulse_lower = -90
        self.pulse_upper = 90
        self.dro_lower = -0.04
        self.dro_upper = 0.04
        self.latest_message = ""
        
        global MAIN_UI

    @QtCore.pyqtSlot()
    def run(self):                          # Run serial reader thread

        while self.running:                
            
            time.sleep(PLOT_UPDATE_INTERVAL)
            
            if len(PULSE_DRO)!=0:

                if PULSE_DRO[-1][1] == "Moving":
                    self.text_update_bool = True
                    self.plot_update_bool = True

                elif PULSE_DRO[-1][1] == "Finish":
                    self.text_update_bool = False
                    self.plot_update_bool = False
                #print(message[-1])
                pulse_display = PULSE_DRO[-1][2]
                dro_display = PULSE_DRO[-1][3]/100

                self.pulse_lower = min(self.pulse_lower, pulse_display)
                self.pulse_upper = max(self.pulse_upper, pulse_display)

                self.dro_lower = min(self.dro_lower, dro_display)
                self.dro_upper = max(self.dro_upper, dro_display)
                
                if self.text_update_bool:
                    MAIN_UI.update_text(round(pulse_display,2), round(dro_display,2))
                if self.plot_update_bool:
                    MAIN_UI.update_plot(pulse_display, dro_display, self.pulse_lower, self.pulse_upper, self.dro_lower, self.dro_upper)
          

#Thread for monitoring data in and out from Arduino
class SerialWorker(QtCore.QRunnable): 

    def __init__(self, portname, baudrate): # Initialise with serial port details
        QtCore.QThread.__init__(self)
        self.portname, self.baudrate = portname, baudrate
        self.txq = Queue.Queue()
        self.running = True
        self.latest_message = ""
        self.ser = None
        global MAIN_UI
 
    def ser_out(self, s):                   # Write outgoing data to serial port if open
        self.txq.put(s)                     # ..using a queue to sync with reader thread
         
    def ser_in(self, s):                    # Write incoming serial data to screen
        global RECORD_INDEX, PULSE_DRO
        for ss in s:
            if ss == '!':

                if self.latest_message[0] == 'R':

                    if self.latest_message[1] == 'R':
                        msg = self.latest_message.replace("RR","")
                        msg_array = msg.split(";")
                        pulse_return = float(msg_array[0])
                        dro_return = float(msg_array[1])
                        PULSE_DRO.append([RECORD_INDEX, "Moving", pulse_return, dro_return, int(time.time()*1000) - START_TIME])
                        self.latest_message = ""

                    elif self.latest_message[1] == 'F':
                        msg = self.latest_message.replace("RF","")
                        msg_array = msg.split(";")
                        pulse_return = float(msg_array[0])
                        dro_return = float(msg_array[1])
                        PULSE_DRO = PULSE_DRO[:-1] #If last coordinates match RR, replace that with RM
                        PULSE_DRO.append([RECORD_INDEX, "Finish", pulse_return, dro_return, int(time.time()*1000) - START_TIME])
                        MAIN_UI.update_text(pulse_return, dro_return)
                        self.latest_message = "" 
            else:
                self.latest_message += ss

    @QtCore.pyqtSlot()
    def run(self):                          # Run serial reader thread
        try:
            self.ser = serial.Serial(self.portname, self.baudrate, timeout=SER_TIMEOUT)
            
            time.sleep(SER_TIMEOUT*1.2)
            self.ser.flushInput()
        except:
            self.ser = None
        if not self.ser:
            MAIN_UI.write("Can't open port")
            self.running = False
        while self.running:
            s = self.ser.read(self.ser.in_waiting or 1)
            if s:                                       # Get data from serial port
                self.ser_in(to_string(s))               # ..and convert to string
            if not self.txq.empty():
                txd = str(self.txq.get())               # If Tx data in queue, write to serial port
                self.ser.write(txd.encode())
        if self.ser:                                    # Close serial port when thread finished
            self.ser.close()
            self.ser = None

#Thread for the main user interface
class WidgetGallery(QDialog):

    text_update = QtCore.pyqtSignal(str)
    
    def __init__(self, parent=None):
        
        super(WidgetGallery, self).__init__(parent)
        global MAIN_UI, START_TIME, PULSE_DRO

        # Define START_TIME, used as ID for each measurement
        START_TIME = int(time.time() * 1000)
        self.record_time = {} #define a dictionary, unordered_map, to record the time enabling hall sensor

        self.threadpool = QtCore.QThreadPool()
        self.plot_updater = PlotUpdateWorker()
        self.threadpool.start(self.plot_updater)
        self.plot_updater.running = True

        self.ser_router = None
        
        MAIN_UI = self
        self.connect_router = 0 # 0 disconnect, 1 connect

        self.setGeometry(30, 30, 300, 500)

        self.text_update.connect(self.append_text)      # Connect text update to handler
        
        self.createTopGroupBox()
        self.createCenterLeftTabWidget()
        self.createCenterRightTabWidget()
        self.createBottomTabWidget()

        self.tab3MiddleGroupBox.setDisabled(1)

        with open("./config/config.json", "r") as json_file:
            self.config = json.load(json_file)

        title = self.config["description"]["title"]
        doc = self.config["description"]["content"]
        
        sim_title = QLabel(title)
        sim_doc = QLabel(doc)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(sim_title)
        mainLayout.addWidget(sim_doc)
        mainLayout.addWidget(self.TopTabWidget)
        mainLayout.setStretchFactor(self.TopTabWidget, 2)
        mainLayout.addWidget(self.CenterLeftTabWidget)
        mainLayout.setStretchFactor(self.CenterLeftTabWidget, 3)
        mainLayout.addWidget(self.CenterRightTabWidget)
        mainLayout.setStretchFactor(self.CenterRightTabWidget, 6)
        mainLayout.addWidget(self.bottom_textEdit)
        mainLayout.setStretchFactor(self.bottom_textEdit, 2)

        self.setLayout(mainLayout)

        self.setWindowTitle("DRO & Motor Data Collecting Software")

    def createTopGroupBox(self):

        self.TopTabWidget = QTabWidget()
        self.TopTabWidget.setTabPosition(QTabWidget.TabPosition.West)

        self.TopLeftGroupBox = QGroupBox("Basic Information and I/O")
        self.TopLeftGroupBox.setChecked(True)

        #1st line button
        self.top_line1_styleLabel = QLabel("Control Module:")
        self.top_line1_lineEdit1 = QLineEdit("COM9")
        self.top_line1_toggle1 = AnimatedToggle()
        self.top_line1_toggle1.stateChanged.connect(lambda: self.button_clicked_main("connect_router"))

        #top layout line2
        layout = QHBoxLayout()
        layout.addWidget(self.top_line1_styleLabel)
        layout.setStretchFactor(self.top_line1_styleLabel, 5)
        layout.addWidget(self.top_line1_lineEdit1)
        layout.setStretchFactor(self.top_line1_lineEdit1, 5)
        layout.addWidget(self.top_line1_toggle1)
        layout.setStretchFactor(self.top_line1_toggle1, 1)
        layout.addStretch(10)
  
        #layout.setRowStretch(5, 1)
        self.TopLeftGroupBox.setLayout(layout)

        self.TopRightGroupBox = QGroupBox("Info")
        self.TopRightGroupBox.setChecked(True)

        self.top_line2_Label1 = QLabel("Manual")
        self.top_line2_Button1 = QPushButton(icon=QtGui.QIcon("./icon/Manual.svg"))
        self.top_line2_Button1.setIconSize(QtCore.QSize(50, 50))
        self.top_line2_Button1.clicked.connect(lambda: self.button_clicked_main("show_manual"))
        self.top_line2_Label2 = QLabel("Spec")
        self.top_line2_Button2 = QPushButton(icon=QtGui.QIcon("./icon/Equipment.svg"))
        self.top_line2_Button2.setIconSize(QtCore.QSize(50, 50))
        self.top_line2_Button2.clicked.connect(lambda: self.button_clicked_main("show_equipment"))
        self.top_line2_Label3 = QLabel("Document")
        self.top_line2_Button3 = QPushButton(icon=QtGui.QIcon("./icon/Doc.svg"))
        self.top_line2_Button3.setIconSize(QtCore.QSize(50, 50))
        self.top_line2_Button3.clicked.connect(lambda: self.button_clicked_main("show_document"))
        self.top_line2_Label4 = QLabel("Contact")
        self.top_line2_Button4 = QPushButton(icon=QtGui.QIcon("./icon/Contact.svg"))
        self.top_line2_Button4.setIconSize(QtCore.QSize(50, 50))
        self.top_line2_Button4.clicked.connect(lambda: self.button_clicked_main("show_contact"))

        layout2 = QGridLayout()
        layout2.addWidget(self.top_line2_Label1, 0, 0, 1, 1)
        layout2.addWidget(self.top_line2_Label2, 0, 1, 1, 1)
        layout2.addWidget(self.top_line2_Label3, 0, 2, 1, 1)
        layout2.addWidget(self.top_line2_Label4, 0, 3, 1, 1)

        layout2.addWidget(self.top_line2_Button1, 1, 0, 1, 1)
        layout2.addWidget(self.top_line2_Button2, 1, 1, 1, 1)
        layout2.addWidget(self.top_line2_Button3, 1, 2, 1, 1)
        layout2.addWidget(self.top_line2_Button4, 1, 3, 1, 1)
        #layout2.addStretch(10)

        self.TopRightGroupBox.setLayout(layout2)

        tab2 = QWidget()
        tableWidget = QTableWidget(10, 10)

        tab2hbox = QHBoxLayout()
        tab2hbox.setContentsMargins(1, 1, 1, 1)
        tab2hbox.addWidget(self.TopLeftGroupBox)
        tab2hbox.setStretchFactor(self.TopLeftGroupBox, 6)
        tab2hbox.addWidget(self.TopRightGroupBox)
        tab2hbox.setStretchFactor(self.TopRightGroupBox, 4)
        
        tab2.setLayout(tab2hbox)

        self.TopTabWidget.addTab(tab2, "&Basic")

    def createCenterLeftTabWidget(self):

        self.new_messages = []
        
        self.CenterLeftTabWidget = QTabWidget()
        self.CenterLeftTabWidget.setTabPosition(QTabWidget.TabPosition.West)

        tab1 = QWidget()

        self.CoordinateGroupBox = QGroupBox("Coordinate")

        self.tab1_Line1Label1 = QLabel("DRO: ")
        self.tab1_Line1Label2 = QLabel("0")
        self.tab1_Line1Label3 = QLabel(" mm")
        self.tab1_Line2Label1 = QLabel("Motor: ")
        self.tab1_Line2Label2 = QLabel("0")
        self.tab1_Line2Label3 = QLabel(" pulse")

        coordinate_box = QGridLayout()
        coordinate_box.addWidget(self.tab1_Line1Label1, 0, 0, 1, 1)
        coordinate_box.addWidget(self.tab1_Line1Label2, 0, 1, 1, 1)
        coordinate_box.addWidget(self.tab1_Line1Label3, 0, 2, 1, 1)
        coordinate_box.addWidget(self.tab1_Line2Label1, 1, 0, 1, 1)
        coordinate_box.addWidget(self.tab1_Line2Label2, 1, 1, 1, 1)
        coordinate_box.addWidget(self.tab1_Line2Label3, 1, 2, 1, 1)

        self.CoordinateGroupBox.setLayout(coordinate_box)

        self.tab3MiddleGroupBox = QGroupBox("Parameters")

        self.tab3_line4Label1 = QLabel("Speed: ")
        self.tab3_line4ComboBox1 = QComboBox()
        self.tab3_line4ComboBox1.addItems(['High', 'Middle', 'Low'])
        self.tab3_line5Label1 = QLabel("Distance: ")
        self.tab3_line5Edit1 = QLineEdit('0.5')

        self.tab3_Button8 = QPushButton("X+")                             
        self.tab3_Button9 = QPushButton("Home")
        self.tab3_Button10 = QPushButton("X-")

        self.tab3_Button8.clicked.connect(lambda: self.button_clicked_main("X+move"))
        self.tab3_Button9.clicked.connect(lambda: self.button_clicked_main("Homing"))
        self.tab3_Button10.clicked.connect(lambda: self.button_clicked_main("X-move"))

        tab3_middle_box = QGridLayout()
        tab3_middle_box.addWidget(self.tab3_line4Label1, 0, 0, 1, 1)
        tab3_middle_box.addWidget(self.tab3_line4ComboBox1, 0, 1, 1, 1)
        tab3_middle_box.addWidget(self.tab3_line5Label1, 0, 2, 1, 1)
        tab3_middle_box.addWidget(self.tab3_line5Edit1, 0, 3, 1, 1)
        tab3_middle_box.addWidget(self.tab3_Button8, 1, 0, 1, 1)
        tab3_middle_box.addWidget(self.tab3_Button9, 1, 1, 1, 1)
        tab3_middle_box.addWidget(self.tab3_Button10, 1, 2, 1, 1)
        tab3_middle_box.setColumnStretch(tab3_middle_box.columnCount(), 1)


        self.tab3MiddleGroupBox.setLayout(tab3_middle_box)

        tab3 = QWidget()
        tableWidget = QTableWidget(10, 10)

        tab3hbox = QHBoxLayout()
        tab3hbox.setContentsMargins(1, 1, 1, 1)
        tab3hbox.addWidget(self.CoordinateGroupBox)
        tab3hbox.setStretchFactor(self.CoordinateGroupBox, 3)
        tab3hbox.addWidget(self.tab3MiddleGroupBox)
        tab3hbox.setStretchFactor(self.tab3MiddleGroupBox, 7)
        
        tab3.setLayout(tab3hbox)

        self.CenterLeftTabWidget.addTab(tab3, "&Move")

    def createCenterRightTabWidget(self):

        self.new_messages = []
        
        self.CenterRightTabWidget = QTabWidget()

        self.CenterRightTabWidget.setTabPosition(QTabWidget.TabPosition.West)
        #self.CenterRightTabWidget.setTabShape(QTabWidget.TabShape.Triangular)

        self.tab10MiddleGroupBox = QGroupBox("Real-time Magnetic Field")

        self.tab10_line4Edit1 = QLabel("Distance: ")
        self.tab10_line4Edit2 = QLabel("0")
        self.tab10_line4Edit3 = QLabel(" mm")

        #self.plot_thread1 = PlotThread(tab11)

        self.time = np.array(range(PLOT_TIME_FRAME))
        self.plot_dro = np.zeros(PLOT_TIME_FRAME, dtype = float)
        self.plot_pulse = np.zeros(PLOT_TIME_FRAME, dtype = float)

        pg.mkQApp()

        pw = pg.PlotWidget()
        pw.setBackground("w")
        pw.show()
        self.p1 = pw.plotItem
        self.p1.setLabels(left='DRO')

        ## create a new ViewBox, link the right axis to its coordinate system
        self.p2 = pg.ViewBox()
        self.p1.showAxis('right')
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis('right').linkToView(self.p2)
        self.p2.setXLink(self.p1)
        self.p1.getAxis('right').setLabel('Pulse', color='black')

        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())

        self.updateViews()
        self.p1.vb.sigResized.connect(self.updateViews)

        pen = pg.mkPen(color=(51, 82, 255), width=2, cosmetic=True)

        self.p1.plot(self.plot_dro)
        self.p2.addItem(pg.PlotCurveItem(self.plot_pulse, pen=pen))

        tab10_middle_box = QGridLayout()
        tab10_middle_box.addWidget(pw, 0, 0, 1, 1)

        self.tab10MiddleGroupBox.setLayout(tab10_middle_box)
        
        tab10 = QWidget()

        tab10hbox = QGridLayout()
        tab10hbox.addWidget(self.tab10MiddleGroupBox, 1, 0, 1, 1)
        tab10hbox.setContentsMargins(1, 1, 1, 1)
        tab10.setLayout(tab10hbox)

        self.CenterRightTabWidget.addTab(tab10, "&Chart") 

    #Message box 
    def createBottomTabWidget(self):
        self.bottomTabWidget = QTabWidget()
        self.bottom_textEdit = QTextEdit()
        self.bottom_textEdit.setPlainText("message start\n")

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.bottom_textEdit)
        self.bottomTabWidget.setLayout(bottom_layout)

    def append_text(self, text):                # Text display update handler
        cur = self.bottom_textEdit.textCursor()
        cur.movePosition(cur.MoveOperation.End) # Move cursor to end of text
        s = str(text)

        cur.insertText(s+'\n')
        self.bottom_textEdit.setTextCursor(cur)  
        
    def closeEvent(self, event):                # Window closing

        if self.ser_router:
            self.ser_router.running = False              # Wait until serial thread terminates
            self.ser_router.wait()
            
    def write(self, text):                      # Handle sys.stdout.write: update display
        self.text_update.emit(text)             # Send signal to synchronise call with main thread

    def update_plot(self, pulse, dro, pulse_lower, pulse_upper, dro_lower, dro_upper):
        
        self.time = np.append(self.time[1:], self.time[-1] + 1)
        self.plot_dro = np.append(self.plot_dro[1:], dro)
        self.plot_pulse = np.append(self.plot_pulse[1:], pulse)

        self.p1.clear()
        self.p2.clear()
        self.p1.plot(self.plot_dro)
        self.p2.addItem(pg.PlotCurveItem(self.plot_pulse, pen='b'))

    def update_text(self, pulse, dro):
        
        self.tab1_Line1Label2.setText(str(dro/100))
        self.tab1_Line2Label2.setText(str(pulse))

    def button_clicked_main(self, action):
        global RECORD_INDEX, RECORD_TIME
        match action:               
                
            case "connect_router":
                if self.connect_router == 0:
                    self.ser_router = SerialWorker(self.top_line1_lineEdit1.text(), 9600)
                    self.threadpool.start(self.ser_router)
                    if self.ser_router.ser:
                        MAIN_UI.write("connect router")
                        self.connect_router = 1
                        self.tab3MiddleGroupBox.setDisabled(0)

                    else:
                        p = QtGui.QPainter(self)
                        p.setBrush(self._bar_brush)
                        p.drawRoundedRect(barRect, rounding, rounding)
                        p.setPen(self._light_grey_pen)
                        p.setBrush(self._handle_brush)
                        p.end()
                        self.top_line1_toggle1.animations_group.stop()
                        self.top_line1_toggle1.animation.setEndValue(0)
                        self.top_line1_toggle1.animations_group.start()

                elif self.connect_router == 1:
                    self.ser_router.running = False
                    MAIN_UI.write("disconnect router")
                    self.connect_router = 0
                    self.tab3MiddleGroupBox.setDisabled(1)
                
            case "X+move":
                RECORD_INDEX += 1
                self.record_time[RECORD_INDEX] = datetime.now().strftime("%d%m%Y_%H%M%S")
                command = "L+" + self.move_command_generator() + "#"
                self.ser_router.ser_out(command)
                self.plot_updater.text_update_bool = True
                self.plot_updater.plot_update_bool = True
                
            case "X-move":
                RECORD_INDEX += 1
                self.record_time[RECORD_INDEX] = datetime.now().strftime("%d%m%Y_%H%M%S")
                command = "L-" + self.move_command_generator() + "#"
                self.ser_router.ser_out(command)
                self.plot_updater.text_update_bool = True
                self.plot_updater.plot_update_bool = True

            case "Homing":
                #To Do: Need a touch limit sensor
                pass

            case "show_manual":
                dialog = QDialog()
                lay = QVBoxLayout(dialog)      
                title = QLabel(self.config["manual"]["title"])
                content = QLabel(self.config["manual"]["content"])
                lay.addWidget(title)
                lay.addWidget(content)
                dialog.exec()

            case "show_equipment":
                dialog = QDialog()
                lay = QVBoxLayout(dialog)      
                title = QLabel(self.config["equipment"]["title"])
                content = QLabel(self.config["equipment"]["content"])
                lay.addWidget(title)
                lay.addWidget(content)
                dialog.exec()

            case "show_document":
                dialog = QDialog()
                lay = QVBoxLayout(dialog)      
                title = QLabel(self.config["document"]["title"])
                content = QLabel(self.config["document"]["content"])
                lay.addWidget(title)
                lay.addWidget(content)
                dialog.exec()

            case "show_contact":
                dialog = QDialog()
                lay = QVBoxLayout(dialog)      
                title = QLabel(self.config["contact"]["title"])
                content = QLabel(self.config["contact"]["content"])
                lay.addWidget(title)
                lay.addWidget(content)
                dialog.exec()

    def move_command_generator(self):
        
        match str(self.tab3_line4ComboBox1.currentText()):
            case 'High':
                speed = "00"
            case 'Middle':
                speed = "50"
            case 'Low':
                speed = "90"

        distance = float(self.tab3_line5Edit1.text())
        if distance<0 or distance>99:
            print("invalid stroke: out of range")
            return "invalid"
        distance = str(int(distance*100)) #Unit of DRO is 0.01 mm, while unit of use input is 1 mm
        match len(distance):
            case 1:
                distance = "000" + distance
            case 2:
                distance = "00" + distance
            case 3:
                distance = "0" + distance
            case 4:
                distance = distance

        return speed + distance

    def update_data(self):

        self.df = pd.DataFrame(columns = ['DRO','Pulse','Time','No'])
        time_series, dro_series, pulse_series, no_series = [], [], [], []

        for data in PULSE_DRO:

            no_series.append(data[0])
            pulse_series.append(data[2])
            dro_series.append(data[3]/100)
            time_series.append(data[4])

        self.df['No'] = no_series
        self.df['Pulse'] = pulse_series
        self.df['DRO'] = dro_series
        self.df['Time'] = time_series

    ## Handle view resizing for plotting DRO and Pulse in the same plot
    def updateViews(self):
        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)
     
# Convert bytes to string
def to_string(d):
    return d if type(d) is str else "".join([chr(b) for b in d])

if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    gallery = WidgetGallery()
    gallery.show()
    sys.exit(app.exec())