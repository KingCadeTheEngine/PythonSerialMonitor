"""
Main application window.

- Sets up the UI layout.
- Creates and manages the serial worker thread.
- Connects GUI signals to worker slots and vice-versa.
"""
import serial.tools.list_ports
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QComboBox, QPushButton, QLineEdit, QSpinBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import QThread, Slot, QTimer, Qt
from PySide6.QtGui import QTextCursor
from datetime import datetime

from serial_comm.worker import SerialWorker
from gui.widgets.plot_widget import PlotWidget
from gui.widgets.logger_widget import LoggerWidget
from serial_comm.file_writer_worker import FileWriterWorker
from serial_comm.plot_data_processor import PlotDataProcessor
from serial_comm.data_bufferer import DataBufferer # Import the new data bufferer

from PySide6.QtCore import QThread, Slot, QTimer, Qt, Signal # Import Signal
class MainWindow(QMainWindow):
    finalize_file_writing = Signal() # New signal for finalizing file writing
    request_connect_port = Signal(str, int) # Signal to request serial port connection
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Python Serial GUI")
        self.resize(1200, 800)

        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Setup Plot Data Processor and Thread ---
        self.plot_data_processor_thread = QThread()
        self.plot_data_processor = PlotDataProcessor(window_size=100) # Initial window size
        self.plot_data_processor.moveToThread(self.plot_data_processor_thread)
        self.plot_data_processor_thread.start()

        # --- Setup Data Bufferer and Thread ---
        self.data_bufferer_thread = QThread()
        self.data_bufferer = DataBufferer()
        self.data_bufferer.moveToThread(self.data_bufferer_thread)
        self.data_bufferer_thread.start()

        # --- Create Widgets ---
        # Plot widget now receives data from the processor
        self.plot_widget = PlotWidget(window_size=100)
        self.logger_widget = LoggerWidget(max_lines=100)

        # Timer for updating logger display
        self.logger_display_timer = QTimer(self)
        self.logger_display_timer.setInterval(150) # Update logger display every 150 ms
        self.logger_display_timer.timeout.connect(self.logger_widget.update_display)
        self.logger_display_timer.start()

        # --- Create Control Panel ---
        self._create_control_panel()
        self._populate_ports()

        # Arrange plot and logger side-by-side
        plot_logger_layout = QHBoxLayout()
        plot_logger_layout.addWidget(self.plot_widget, 7) # 70% width
        plot_logger_layout.addWidget(self.logger_widget, 3) # 30% width

        # Add widgets to main layout
        main_layout.addWidget(self.control_panel)
        main_layout.addLayout(plot_logger_layout)

        # --- Setup File Writer Worker and Thread ---
        self.file_write_thread = QThread()
        self.file_writer_worker = FileWriterWorker()
        self.file_writer_worker.moveToThread(self.file_write_thread)
        self.file_writer_worker.finished.connect(self.on_file_write_finished)
        self.file_write_thread.start() # Start the thread once
        self.file_write_thread.started.connect(self._connect_file_writer_signals)

        # --- Setup Serial Worker and Thread ---
        self._setup_serial_worker()

        # Initialize recording state
        self.is_recording = False
        self.current_message_count = 0 # Initialize message count

    def _create_control_panel(self):
        self.control_panel = QGroupBox("Control Panel")
        layout = QHBoxLayout()

        # Connection Group
        connection_group = QGroupBox("Connection")
        conn_layout = QGridLayout()
        self.port_combo = QComboBox()
        self.baud_combo = QComboBox()
        baud_rates = ['9600', '19200', '38400', '57600', '115200', '2000000']
        self.baud_combo.addItems(baud_rates)
        self.baud_combo.setCurrentText('2000000')
        self.refresh_ports_button = QPushButton("Refresh")
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        conn_layout.addWidget(QLabel("Port:"), 0, 0)
        conn_layout.addWidget(self.port_combo, 0, 1)
        conn_layout.addWidget(self.refresh_ports_button, 0, 2)
        conn_layout.addWidget(QLabel("Baud Rate:"), 1, 0)
        conn_layout.addWidget(self.baud_combo, 1, 1)
        conn_layout.addWidget(self.connect_button, 2, 0, 1, 3)
        conn_layout.addWidget(self.disconnect_button, 3, 0, 1, 3)
        connection_group.setLayout(conn_layout)

        # Plotting Group
        plot_group = QGroupBox("Plotting")
        plot_layout = QGridLayout()
        self.window_size_spinbox = QSpinBox()
        self.window_size_spinbox.setRange(10, 10000)
        self.window_size_spinbox.setValue(100)
        self.window_size_spinbox.setSuffix(" samples")
        plot_layout.addWidget(QLabel("Window Size:"), 0, 0)
        plot_layout.addWidget(self.window_size_spinbox, 0, 1)
        plot_group.setLayout(plot_layout)

        # Send Command Group
        send_group = QGroupBox("Send Command")
        send_layout = QVBoxLayout()
        self.command_input = QLineEdit()
        self.send_button = QPushButton("Send")
        send_layout.addWidget(self.command_input)
        send_layout.addWidget(self.send_button)
        send_group.setLayout(send_layout)

        layout.addWidget(connection_group)
        layout.addWidget(plot_group)
        layout.addWidget(send_group)

        # Recording Group
        record_group = QGroupBox("Recording")
        record_layout = QVBoxLayout()
        
        # File path selection
        file_path_layout = QHBoxLayout()
        self.record_file_path_input = QLineEdit()
        self.record_file_path_input.setPlaceholderText("Enter recording file path or browse...")
        self.record_file_path_input.setText(f"serial_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv") # Default filename
        self.browse_record_file_button = QPushButton("Browse...")
        file_path_layout.addWidget(self.record_file_path_input)
        file_path_layout.addWidget(self.browse_record_file_button)
        record_layout.addLayout(file_path_layout)

        self.start_record_button = QPushButton("Start Recording")
        self.stop_record_button = QPushButton("Stop Recording")
        self.stop_record_button.setEnabled(False) # Disabled until recording starts
        self.record_status_label = QLabel("Recording: OFF")
        record_layout.addWidget(self.start_record_button)
        record_layout.addWidget(self.stop_record_button)
        record_layout.addWidget(self.record_status_label)
        record_group.setLayout(record_layout)
        layout.addWidget(record_group)

        layout.addStretch()
        self.control_panel.setLayout(layout)

    def _populate_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)

    def _setup_serial_worker(self):
        self.thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.worker.port_status.connect(self.on_port_status_changed)
        self.worker.data_received.connect(self._handle_incoming_data) # Raw data to main window
        self.worker.message_count_updated.connect(self._update_message_count) # Connect new signal

        # Connect raw data to plot data processor
        self.worker.data_received.connect(self.plot_data_processor.process_incoming_data)
        # Connect processed data from processor to plot widget
        self.plot_data_processor.processed_plot_data_ready.connect(self.plot_widget.update_plot_data)

        # Connect raw data to data bufferer
        self.worker.data_received.connect(self.data_bufferer.process_raw_data)
        # Connect buffered logger data to logger widget
        self.data_bufferer.logger_data_ready.connect(self.logger_widget.log_data)
        # Connection for recording data moved to _connect_file_writer_signals to ensure thread readiness.

        # Connect UI signals
        self.connect_button.clicked.connect(self.connect_serial)
        self.request_connect_port.connect(self.worker.connect_port) # Connect new signal to worker's slot
        self.disconnect_button.clicked.connect(self.worker.disconnect_port)
        self.refresh_ports_button.clicked.connect(self._populate_ports)
        self.send_button.clicked.connect(self.send_command)
        self.window_size_spinbox.valueChanged.connect(self.plot_data_processor.set_window_size) # Connect to processor
        self.window_size_spinbox.valueChanged.connect(self.logger_widget.set_max_lines)
        self.start_record_button.clicked.connect(self.start_recording)
        self.stop_record_button.clicked.connect(self.stop_recording)
        self.browse_record_file_button.clicked.connect(self._browse_record_file)

        self.thread.start()

    @Slot()
    def connect_serial(self):
        port = self.port_combo.currentText()
        baud = self.baud_combo.currentText()
        if not port:
            self.statusBar().showMessage("Error: No port selected.", 3000)
            return
        # Call connect_port as a queued slot on the worker object
        self.request_connect_port.emit(port, int(baud))

    @Slot()
    def send_command(self):
        command = self.command_input.text()
        if self.disconnect_button.isEnabled() and command:
            self.worker.send(command + '\n') # Log sent command
            self.logger_widget.log_data(f">> {command}") # Log sent command
            self.command_input.clear()

    @Slot(bool, str)
    def on_port_status_changed(self, is_open, message):
        self.statusBar().showMessage(message, 3000)
        self.connect_button.setEnabled(not is_open)
        self.disconnect_button.setEnabled(is_open)
        self.port_combo.setEnabled(not is_open)
        self.baud_combo.setEnabled(not is_open)
        self.refresh_ports_button.setEnabled(not is_open)

    def closeEvent(self, event):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait(5000) # Wait up to 5s for thread to finish

        self.file_write_thread.quit()
        self.file_write_thread.wait(5000) # Wait up to 5s for file write thread to finish

        self.plot_data_processor_thread.quit()
        self.plot_data_processor_thread.wait(5000) # Wait up to 5s for plot data processor thread to finish

        self.data_bufferer_thread.quit()
        self.data_bufferer_thread.wait(5000) # Wait up to 5s for data bufferer thread to finish

        super().closeEvent(event)

    @Slot()
    def _browse_record_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Recording As",
            self.record_file_path_input.text(), # Use current text as default
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            self.record_file_path_input.setText(file_name)

    @Slot()
    def start_recording(self):
        file_name = self.record_file_path_input.text()
        if not file_name:
            self.statusBar().showMessage("Error: Please specify a recording file path.", 3000)
            return

        self.is_recording = True
        self.data_bufferer.clear_recording_buffer() # Clear buffer for new recording
        start_message_count = self.current_message_count # Get count at start
        self.file_writer_worker.start_recording(file_name, start_message_count)
        self.data_bufferer.set_recording_status(True) # Start flushing timer in DataBufferer
        self.record_status_label.setText("Recording: ON")
        self.start_record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)
        self.statusBar().showMessage("Recording started.", 3000)

    @Slot()
    def stop_recording(self):
        self.is_recording = False
        self.data_bufferer.set_recording_status(False) # Stop flushing timer in DataBufferer
        end_message_count = self.current_message_count # Get count at end
        self.file_writer_worker.stop_recording(end_message_count)
        self.finalize_file_writing.emit() # Emit signal to finalize file writing
        self.record_status_label.setText("Recording: OFF")
        self.start_record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)
        self.statusBar().showMessage("Recording stopped.", 3000)

    @Slot(list)
    def _handle_incoming_data(self, data_list):
        # This method now only serves as a pass-through for raw data
        # to other workers. Buffering is handled by DataBufferer.
        pass # Data is now directly connected to plot_data_processor and data_bufferer

    

    @Slot(bool, str)
    def on_file_write_finished(self, success, message):
        self.statusBar().showMessage(message, 5000)
        if not success:
            QMessageBox.warning(self, "Recording Error", message)

    @Slot(int)
    def _update_message_count(self, count):
        self.current_message_count = count

    @Slot()
    def _connect_file_writer_signals(self):
        # Connect buffered recording data to file writer worker
        self.data_bufferer.recording_data_ready.connect(self.file_writer_worker.append_data)
        self.finalize_file_writing.connect(self.file_writer_worker.finalize_recording) # Connect finalize signal
        
