"""
Real-time plotting widget using pyqtgraph.
"""
from collections import deque
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Slot, Signal
import pyqtgraph as pg

class PlotWidget(QWidget):
    channels_detected = Signal(int)

    def __init__(self, parent=None, window_size=100):
        super().__init__(parent)
        self.num_lines = 0  # Will be determined dynamically
        self.window_size = window_size

        # Setup pyqtgraph plot
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.getPlotItem().enableAutoRange(axis='y')
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time (samples)')

        # Initialize empty lists for lines and data
        self.lines = []
        self.data = []
        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 'w']

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def _initialize_plot_lines(self, num_channels):
        """Dynamically create plot lines and data deques."""
        self.num_lines = num_channels
        self.lines = []
        self.data = []
        self.plot_widget.clear()

        for i in range(self.num_lines):
            pen = pg.mkPen(color=self.colors[i % len(self.colors)])
            line = self.plot_widget.plot([], [], pen=pen)
            self.lines.append(line)
            self.data.append(deque(maxlen=self.window_size))
        self.channels_detected.emit(self.num_lines)

    @Slot(list) # Changed to accept a list of strings
    def update_data(self, data_list):
        """Parse comma-separated strings from a list and update plot."""
        for data_string in data_list:
            try:
                values = [float(v) for v in data_string.split(',')]

                if self.num_lines == 0: # First data packet, determine number of channels
                    self._initialize_plot_lines(len(values))

                if len(values) != self.num_lines:
                    print(f"Warning: Received {len(values)} values, expected {self.num_lines}. Data ignored.")
                    continue # Skip to next data string in the list

                for i in range(self.num_lines):
                    self.data[i].append(values[i])

                # Update plot only once per batch for efficiency
                for i in range(self.num_lines):
                    self.lines[i].setData(range(len(self.data[i])), list(self.data[i]))

            except (ValueError, IndexError) as e:
                print(f"Plot Error: Could not parse data '{data_string}'. Error: {e}")

    @Slot(int)
    def set_window_size(self, size):
        """Update the maxlen of the data deques."""
        if size > 0:
            self.window_size = size
            for i in range(self.num_lines):
                # Create a new deque with the new size and preserve existing data
                new_deque = deque(self.data[i], maxlen=self.window_size)
                self.data[i] = new_deque
