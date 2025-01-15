import time
import PyQt6.QtCore as QtCore
import serial

import queue as Queue

#Thread for updating plot and text displayed on main UI within a defined period
class PlotUpdater(QtCore.QRunnable):

    def __init__(self, UI): # Initialise with serial port details
        QtCore.QThread.__init__(self)
        self.running = True
        self.text_update_bool = False
        self.plot_update_bool = False
        self.pulse_lower = -90
        self.pulse_upper = 90
        self.dro_lower = -0.04
        self.dro_upper = 0.04
        self.latest_message = ""
        self.interface = UI
        

    @QtCore.pyqtSlot()
    def run(self):                          # Run serial reader thread

        while self.running:                
            
            time.sleep(self.interface.plot_update_interval)
            
            if len(self.interface.dro_pulse_record)!=0:

                if self.interface.dro_pulse_record[-1][1] == "Moving":
                    self.text_update_bool = True
                    self.plot_update_bool = True

                elif self.interface.dro_pulse_record[-1][1] == "Finish":
                    self.text_update_bool = False
                    self.plot_update_bool = False

                pulse_display = self.interface.dro_pulse_record[-1][2]
                dro_display = self.interface.dro_pulse_record[-1][3]/100

                self.pulse_lower = min(self.pulse_lower, pulse_display)
                self.pulse_upper = max(self.pulse_upper, pulse_display)

                self.dro_lower = min(self.dro_lower, dro_display)
                self.dro_upper = max(self.dro_upper, dro_display)
                
                if self.text_update_bool:
                    self.interface.update_text(round(pulse_display,2), round(dro_display,2))
                if self.plot_update_bool:
                    self.interface.update_plot(pulse_display, dro_display)
  

#Thread for monitoring data in and out from Arduino
class ComPortConnector(QtCore.QRunnable): 

    def __init__(self, portname, baudrate, UI): # Initialise with serial port details
        QtCore.QThread.__init__(self)
        self.portname, self.baudrate = portname, baudrate
        self.txq = Queue.Queue()
        self.running = True
        self.latest_message = ""
        self.ser = None
        self.interface = UI
 
    def ser_out(self, s):                   # Write outgoing data to serial port if open
        self.txq.put(s)                     # ..using a queue to sync with reader thread
         
    def ser_in(self, s):                    # Write incoming serial data to screen

        for ss in s:
            if ss == '!':

                if self.latest_message[0] == 'R':

                    if self.latest_message[1] == 'R':
                        msg = self.latest_message.replace("RR","")
                        msg_array = msg.split(";")
                        pulse_return = float(msg_array[0])
                        dro_return = float(msg_array[1])
                        self.interface.dro_pulse_record.append([self.interface.record_index[0], "Moving", pulse_return, dro_return, int(time.time()*1000) - self.interface.start_time])
                        self.latest_message = ""

                    elif self.latest_message[1] == 'F':
                        msg = self.latest_message.replace("RF","")
                        msg_array = msg.split(";")
                        pulse_return = float(msg_array[0])
                        dro_return = float(msg_array[1])
                        self.interface.dro_pulse_record = self.interface.dro_pulse_record[:-1] #If last coordinates match RR, replace that with RM
                        self.interface.dro_pulse_record.append([self.interface.record_idx, "Finish", pulse_return, dro_return, int(time.time()*1000) - self.interface.start_time])
                        self.interface.update_text(pulse_return, dro_return)
                        self.latest_message = "" 
            else:
                self.latest_message += ss

    # Convert bytes to string
    def to_string(self, d):
        return d if type(d) is str else "".join([chr(b) for b in d])

    @QtCore.pyqtSlot()
    def run(self):                          # Run serial reader thread
        try:
            self.ser = serial.Serial(self.portname, self.baudrate, timeout=self.interface.timeout)
            
            time.sleep(self.interface.timeout*1.2)
            self.ser.flushInput()
        except:
            self.ser = None
            self.interface.write("Can't open port")

        if not self.ser:
            self.running = False
        while self.running:
            s = self.ser.read(self.ser.in_waiting or 1)
            if s:                                       # Get data from serial port
                self.ser_in(self.to_string(s))               # ..and convert to string
            if not self.txq.empty():
                txd = str(self.txq.get())               # If Tx data in queue, write to serial port
                self.ser.write(txd.encode())
        if self.ser:                                    # Close serial port when thread finished
            self.ser.close()
            self.ser = None