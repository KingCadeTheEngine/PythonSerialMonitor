"""
Serial Communication Worker.

Runs in a separate thread and handles all serial port communication.
Emits signals with received data and receives signals to send data.
"""
import time
import serial
from PySide6.QtCore import QObject, Signal, Slot, QTimer

class SerialWorker(QObject):
    data_received = Signal(list) # Changed to emit a list of strings
    port_status = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port = None
        self._port = None
        self._baudrate = None
        self._is_running = False
        self._is_active = True

        # _data_buffer and _emit_timer will be initialized in run() to ensure thread affinity
        self._data_buffer = []
        self._emit_timer = None
        self._line_buffer = "" # Buffer for incomplete lines

    @Slot(str, int)
    def connect_port(self, port, baudrate):

        self._port = port
        self._baudrate = baudrate
        self._is_running = True

    @Slot()
    def disconnect_port(self):
        
        self._is_running = False

    @Slot()
    def run(self):
        """This method is called when the QThread starts.
        It does not contain a blocking loop, allowing the event loop to run.
        """
        # This method is intentionally left empty or for initial setup that doesn't block.
        # The actual serial reading and emitting is driven by QTimers and slots.
        pass

    @Slot(str, int)
    def connect_port(self, port, baudrate):

        if self._is_running: # Already connected
            return

        self._port = port
        self._baudrate = baudrate
        self._is_running = True

        try:
            self.serial_port = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=0 # Non-blocking read
            )
            self.port_status.emit(True, f"Connected to {self._port} at {self._baudrate} bps.")
            

            # Start the timer for reading serial data
            self._read_timer = QTimer(self)
            self._read_timer.setInterval(1) # Read as fast as possible
            self._read_timer.timeout.connect(self._read_serial_data)
            self._read_timer.start()

            # Start the timer for emitting buffered data
            self._emit_timer = QTimer(self)
            self._emit_timer.setInterval(33) # ~30 FPS update rate
            self._emit_timer.timeout.connect(self._emit_buffered_data)
            self._emit_timer.start()

        except serial.SerialException as e:
            self.port_status.emit(False, f"Error: {e}")
            self._is_running = False
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

    @Slot()
    def disconnect_port(self):
        
        self._is_running = False
        if self._read_timer and self._read_timer.isActive():
            self._read_timer.stop()
        if self._emit_timer and self._emit_timer.isActive():
            self._emit_timer.stop()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.port_status.emit(False, "Disconnected.")

    @Slot()
    def _read_serial_data(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                bytes_to_read = self.serial_port.in_waiting
                if bytes_to_read > 0:
                    data = self.serial_port.read(min(bytes_to_read, 4096)).decode('utf-8', errors='ignore')
                    self._line_buffer += data
                    
                    # Process complete lines
                    lines = self._line_buffer.split('\n')
                    self._line_buffer = lines.pop() # The last element might be an incomplete line

                    for line in lines:
                        line = line.strip()
                        if line:
                            self._data_buffer.append(line)
                            # print(f"Worker: Read line: '{line}'") # Keep for debugging if needed
            except serial.SerialException as e:
                self.port_status.emit(False, f"Serial Read Error: {e}")
                self.disconnect_port() # Disconnect on read error

    @Slot()
    def _emit_buffered_data(self):
        if self._data_buffer:
            
            self.data_received.emit(self._data_buffer) # Emit the whole buffer
            self._data_buffer = [] # Clear the buffer

    @Slot(str)
    def send(self, data):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(data.encode('utf-8'))
                
            except serial.SerialException as e:
                self.port_status.emit(False, f"Send Error: {e}")

    def stop(self):
        """Stop the worker thread gracefully."""
        self._is_active = False
        if self._emit_timer and self._emit_timer.isActive():
            self._emit_timer.stop()
