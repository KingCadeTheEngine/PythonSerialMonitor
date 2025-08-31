from collections import deque
from PySide6.QtCore import QObject, Signal, Slot, QTimer
import numpy as np

class PlotDataProcessor(QObject):
    processed_plot_data_ready = Signal(list, list) # Emits (x_data, list_of_y_data_arrays)

    def __init__(self, parent=None, window_size=100):
        super().__init__(parent)
        self.window_size = window_size
        self.num_channels = 0
        self.data_buffers = [] # List of deques, one for each channel
        self.x_data = deque(maxlen=self.window_size) # For x-axis (sample index)
        self.current_sample_index = 0

        self._process_timer = QTimer(self)
        self._process_timer.setInterval(50) # Process and emit data at ~20 FPS
        self._process_timer.timeout.connect(self._emit_processed_data)
        self._process_timer.start()

        self._incoming_data_buffer = deque(maxlen=4000) # Buffer for raw incoming string data, with maxlen

    @Slot(list)
    def process_incoming_data(self, data_list):
        # This slot is called from the GUI thread, so we just append to a thread-safe buffer
        # The actual processing will happen in the worker thread's timer slot
        self._incoming_data_buffer.extend(data_list)

    def _initialize_buffers(self, num_channels):
        self.num_channels = num_channels
        self.data_buffers = [deque(maxlen=self.window_size) for _ in range(self.num_channels)]
        self.x_data = deque(maxlen=self.window_size) # Reset x_data as well

    @Slot()
    def _emit_processed_data(self):
        # Process all data currently in the incoming buffer
        data_to_process = list(self._incoming_data_buffer)
        self._incoming_data_buffer.clear()

        if not data_to_process:
            return

        for data_string in data_to_process:
            try:
                values = np.fromstring(data_string, sep=',')

                if self.num_channels == 0: # First data packet, determine number of channels
                    self._initialize_buffers(len(values))

                if len(values) != self.num_channels:
                    print(f"PlotDataProcessor Warning: Received {len(values)} values, expected {self.num_channels}. Data ignored.")
                    continue

                for i in range(self.num_channels):
                    self.data_buffers[i].append(values[i])
                
                self.x_data.append(self.current_sample_index)
                self.current_sample_index += 1

            except (ValueError, IndexError) as e:
                print(f"PlotDataProcessor Error: Could not parse data '{data_string}'. Error: {e}")
        
        if self.num_channels > 0:
            # Prepare data for emission
            y_data_arrays = [np.array(list(buf)) for buf in self.data_buffers]
            x_data_array = np.array(list(self.x_data))
            self.processed_plot_data_ready.emit(list(x_data_array), y_data_arrays)

    @Slot(int)
    def set_window_size(self, size):
        if size > 0 and size != self.window_size:
            self.window_size = size
            # Re-initialize deques with new size, preserving existing data
            for i in range(self.num_channels):
                new_deque = deque(self.data_buffers[i], maxlen=self.window_size)
                self.data_buffers[i] = new_deque
            
            # Re-initialize x_data deque with new size
            new_x_deque = deque(self.x_data, maxlen=self.window_size)
            self.x_data = new_x_deque
            # Re-emit data to update plot with new window size
            self._emit_processed_data()
