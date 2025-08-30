# Gemini Project Context: Python Serial GUI

This document provides context for the "PythonSerial" project for other Gemini agents.

## 1. Project Overview

The project is a cross-platform graphical user interface (GUI) application built in Python to communicate with a microcontroller or other serial device. It provides real-time data visualization, logging, and two-way communication.

The application is designed to be run on both Windows and Linux (specifically Raspbian for Raspberry Pi).

## 2. Core Features

- **Serial Port Management:** Auto-detects available serial ports and allows the user to select a port and baud rate to connect.
- **Non-Blocking UI:** The GUI remains responsive at all times, even while actively listening for serial data.
- **Real-Time Plotting:** Incoming numerical data is plotted on a real-time chart.
  - The Y-axis auto-scales to fit the data.
  - The X-axis shows a configurable-length scrolling window of recent data points.
- **Data Logging & Export:** Raw incoming serial data and user-sent commands are displayed in a logger panel. Users can also record incoming data to CSV files, which include a header row with channel names (e.g., "channel1,channel2,...") for easier post-processing.
- **Command Sending:** Users can send string commands to the connected serial device.

## 3. Architecture and Design

The application follows a multi-threaded architecture to ensure a non-blocking user experience.

- **GUI Framework:** **PySide6**
- **Plotting Library:** **pyqtgraph** (chosen over Matplotlib for its superior performance in real-time Qt applications).
- **Serial Communication:** **pyserial**

### Threading Model

- **Main/GUI Thread:** Runs the PySide6 application event loop. Handles all UI rendering and user interaction.
- **Worker Thread (`QThread`):** A single background thread is dedicated to handling all blocking serial I/O.
  - The `serial_comm.worker.SerialWorker` class (a `QObject`) is moved to this thread.
  - The `SerialWorker` contains the `pyserial` logic to open, read from, and write to the serial port.
  - This design prevents the GUI from freezing while waiting for serial data.

### Communication Protocol (Software)

- **Signal/Slot Mechanism:** Communication between the worker thread and the main GUI thread is handled exclusively and safely through Qt's signal and slot mechanism.
  - The `SerialWorker` emits signals like `data_received(str)` or `port_status(bool, str)`.
  - The GUI components (e.g., `MainWindow`, `PlotWidget`) have slots that connect to these signals to update the UI.

### Data Protocol (Hardware)

- The application expects incoming data from the microcontroller to be formatted as a **comma-separated string of numbers**, terminated by a **newline character (`
`)**.
- **Example:** "1.23,4.56,7.89\n"

## 4. Project Structure

```
PythonSerial/
├── main.py                 # Application entry point
├── requirements.txt        # Project dependencies (pyserial, PySide6, pyqtgraph)
├── GEMINI.md               # This file
│
├── gui/
│   ├── main_window.py      # The main QMainWindow, UI layout, and signal connections
│   └── widgets/
│       ├── plot_widget.py  # The pyqtgraph plotting widget
│       └── logger_widget.py # The QTextEdit logging widget
│
└── serial_comm/
    ├── worker.py           # The QObject worker for all serial communication
    └── file_writer_worker.py # QObject worker for writing recorded data to files (e.g., CSV)
```

## 5. Data Export Format

When recording data to a file, the application generates a CSV (Comma Separated Values) file.

-   **Header Row:** The first row of the CSV file contains channel names, automatically generated based on the number of data points received in the first line of data (e.g., "channel1,channel2,channel3").
-   **Data Rows:** Subsequent rows contain the raw, comma-separated numerical data received from the serial device. Each line of data from the serial device corresponds to one row in the CSV.
