"""
Widget for logging raw serial data.
"""
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Slot

class LoggerWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    @Slot(list) # Changed to accept a list of strings
    def log_data(self, data_list):
        for data_string in data_list:
            self.appendPlainText(data_string)
