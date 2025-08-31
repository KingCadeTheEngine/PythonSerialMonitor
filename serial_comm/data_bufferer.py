from collections import deque
from PySide6.QtCore import QObject, Signal, Slot, QTimer

class DataBufferer(QObject):
    logger_data_ready = Signal(list)
    recording_data_ready = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger_buffer = []
        self._recording_buffer = []
        self._is_recording = False

        # Timers for flushing buffers
        self._logger_timer = QTimer(self)
        self._logger_timer.setInterval(100) # Flush logger every 100 ms (10 FPS)
        self._logger_timer.timeout.connect(self._flush_logger_buffer)
        self._logger_timer.start()

        self._recording_timer = QTimer(self)
        self._recording_timer.setInterval(1000) # Flush recording every 1000 ms (1 FPS)
        self._recording_timer.timeout.connect(self._flush_recording_buffer)
        # This timer will be started/stopped by start_recording/stop_recording

    @Slot(list)
    def process_raw_data(self, data_list):
        self._logger_buffer.extend(data_list)
        if self._is_recording:
            self._recording_buffer.extend(data_list)

    @Slot()
    def _flush_logger_buffer(self):
        if self._logger_buffer:
            data_to_log = list(self._logger_buffer)
            self._logger_buffer.clear()
            self.logger_data_ready.emit(data_to_log)

    @Slot()
    def _flush_recording_buffer(self):
        if self._recording_buffer:
            data_to_record = list(self._recording_buffer)
            self._recording_buffer.clear()
            self.recording_data_ready.emit(data_to_record)

    @Slot(bool)
    def set_recording_status(self, status):
        self._is_recording = status
        if status:
            self._recording_timer.start()
        else:
            self._recording_timer.stop()
            self._flush_recording_buffer() # Flush any remaining data on stop

    @Slot()
    def clear_recording_buffer(self):
        self._recording_buffer.clear()
