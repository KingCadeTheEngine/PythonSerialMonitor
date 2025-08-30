from PySide6.QtCore import QObject, Signal, Slot, QThread

class FileWriterWorker(QObject):
    finished = Signal(bool, str) # Signal to report success/failure and message

    @Slot(str, list)
    def write_data(self, file_name, data):
        try:
            with open(file_name, 'w') as f:
                if data:
                    # Infer number of channels from the first data line
                    num_channels = len(data[0].split(','))
                    header = ",".join([f"channel{i+1}" for i in range(num_channels)])
                    f.write(header + '\n')
                for line in data:
                    f.write(line + '\n')
            self.finished.emit(True, f"Recording saved to {file_name}")
        except Exception as e:
            self.finished.emit(False, f"Error saving recording: {e}")
