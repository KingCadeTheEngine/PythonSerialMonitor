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

    @Slot(list, list)
    def update_plot_data(self, x_data, y_data_arrays):
        """Update plot with pre-processed numerical data."""
        if not y_data_arrays:
            return

        num_channels = len(y_data_arrays)
        if self.num_lines == 0 or self.num_lines != num_channels:
            self._initialize_plot_lines(num_channels)

        for i in range(self.num_lines):
            self.lines[i].setData(x_data, y_data_arrays[i])

    @Slot(int)
    def set_window_size(self, size):
        """This slot is now handled by PlotDataProcessor."""
        # The PlotDataProcessor will handle updating its internal deques
        # and re-emitting data with the new window size.
        pass
