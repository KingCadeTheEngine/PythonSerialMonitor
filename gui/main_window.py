"""
Main application window.

- Sets up the UI layout.
- Creates and manages the serial worker thread.
- Connects GUI signals to worker slots and vice-versa.
"""
import serial.tools.list_ports
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QComboBox, QPushButton, QLineEdit, QSpinBox, QFileDialog
)
from PySide6.QtCore import QThread, Slot
from datetime import datetime

from serial_comm.worker import SerialWorker
from gui.widgets.plot_widget import PlotWidget
from gui.widgets.logger_widget import LoggerWidget
from serial_comm.file_writer_worker import FileWriterWorker

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Python Serial GUI")
        self.resize(1200, 800)

        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Create Widgets ---
        # Pass initial window size to plot widget
        self.plot_widget = PlotWidget(window_size=100)
        self.logger_widget = LoggerWidget()

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

        # --- Setup Serial Worker and Thread ---
        self._setup_serial_worker()

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

        # Initialize recording state
        self.is_recording = False
        self.recorded_data = []

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
        self.worker.data_received.connect(self._handle_incoming_data)

        # Connect UI signals
        self.connect_button.clicked.connect(self.connect_serial)
        self.disconnect_button.clicked.connect(self.worker.disconnect_port)
        self.refresh_ports_button.clicked.connect(self._populate_ports)
        self.send_button.clicked.connect(self.send_command)
        self.window_size_spinbox.valueChanged.connect(self.plot_widget.set_window_size)
        self.start_record_button.clicked.connect(self.start_recording)
        self.stop_record_button.clicked.connect(self.stop_recording)

        self.thread.start()

    @Slot()
    def connect_serial(self):
        port = self.port_combo.currentText()
        baud = self.baud_combo.currentText()
        if not port:
            self.statusBar().showMessage("Error: No port selected.", 3000)
            return
        self.worker.connect_port(port, int(baud))

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
        super().closeEvent(event)

    @Slot()
    def start_recording(self):
        self.is_recording = True
        self.recorded_data = []
        self.record_status_label.setText("Recording: ON")
        self.start_record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)
        self.statusBar().showMessage("Recording started.", 3000)

    @Slot()
    def stop_recording(self):
        self.is_recording = False
        self.record_status_label.setText("Recording: OFF")
        self.start_record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)
        self.statusBar().showMessage("Recording stopped.", 3000)
        self._save_recorded_data()

    @Slot(list)
    def _handle_incoming_data(self, data_list):
        # Pass data to logger and plotter
        self.logger_widget.log_data(data_list)
        self.plot_widget.update_data(data_list)

        # If recording, append data
        if self.is_recording:
            for data_item in data_list:
                self.recorded_data.append(data_item)

    def _save_recorded_data(self):
        if not self.recorded_data:
            self.statusBar().showMessage("No data recorded to save.", 3000)
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Recording",
            f"serial_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_name:
            # Create a QThread and worker for file writing
            self.file_write_thread = QThread()
            self.file_writer_worker = FileWriterWorker()
            self.file_writer_worker.moveToThread(self.file_write_thread)

            # Connect signals
            self.file_write_thread.started.connect(
                lambda: self.file_writer_worker.write_data(file_name, self.recorded_data)
            )
            self.file_writer_worker.finished.connect(self.on_file_write_finished)
            self.file_writer_worker.finished.connect(self.file_write_thread.quit)
            self.file_write_thread.finished.connect(self.file_write_thread.deleteLater)
            self.file_writer_worker.finished.connect(self.file_writer_worker.deleteLater)

            # Start the thread
            self.file_write_thread.start()
        else:
            self.statusBar().showMessage("Save operation cancelled.", 3000)

    @Slot(bool, str)
    def on_file_write_finished(self, success, message):
        self.statusBar().showMessage(message, 5000)
