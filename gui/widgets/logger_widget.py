"""
Widget for logging raw serial data.
"""
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Slot
from PySide6.QtGui import QTextCursor
from collections import deque # Import deque

class LoggerWidget(QPlainTextEdit):
    def __init__(self, parent=None, max_lines=100):
        super().__init__(parent)
        self.setReadOnly(True)
        self.log_buffer = deque(maxlen=max_lines) # Use deque for efficient line management
        self.max_lines = max_lines

    @Slot(list)
    def log_data(self, data_list):
        # Append new data to the deque
        for data_string in data_list:
            self.log_buffer.append(data_string)
        
        # The actual display update will be triggered by a timer in MainWindow
        # This method just buffers the data.

    @Slot()
    def update_display(self):
        # Clear the QPlainTextEdit and set its content from the deque
        self.clear()
        self.setPlainText("\n".join(self.log_buffer))
        # Scroll to the bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    @Slot(int)
    def set_max_lines(self, max_lines):
        if max_lines > 0 and max_lines != self.max_lines:
            self.max_lines = max_lines
            # Create a new deque with the new size and preserve existing data
            new_buffer = deque(self.log_buffer, maxlen=self.max_lines)
            self.log_buffer = new_buffer
            self.update_display() # Update display after changing max_lines
