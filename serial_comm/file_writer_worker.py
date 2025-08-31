from PySide6.QtCore import QObject, Signal, Slot, QThread
import os # Import os module for file existence check

class FileWriterWorker(QObject):
    finished = Signal(bool, str) # Signal to report success/failure and message
    all_data_written = Signal() # New signal to indicate all data has been written and file is closed
    _file = None # Internal file handle
    _stop_pending = False # Flag to indicate stop has been requested

    @Slot(str, int)
    def start_recording(self, file_name, start_message_count):
        print(f"[FileWriterWorker] Attempting to start recording to: {file_name}")
        try:
            # Open in append mode, create if not exists
            self.file_name = file_name
            self._file = open(file_name, 'a')
            self.start_message_count = start_message_count
            self._stop_pending = False # Reset stop pending flag
            # If file is new, write header
            if not os.path.exists(file_name) or os.path.getsize(file_name) == 0:
                print(f"[FileWriterWorker] File {file_name} is new/empty. Header will be written on first data.")
                # Header will be written by append_data when first data arrives
                pass
            self.finished.emit(True, f"Recording started to {file_name}")
            print(f"[FileWriterWorker] Recording started successfully.")
        except Exception as e:
            print(f"[FileWriterWorker] Error starting recording: {e}")
            self.finished.emit(False, f"Error starting recording: {e}")

    @Slot(list)
    def append_data(self, data_lines):
        print(f"[FileWriterWorker] Received {len(data_lines)} data lines to append.")
        if not self._file:
            print("[FileWriterWorker] Error: _file is None. Recording not started or already stopped.")
            self.finished.emit(False, "Error: Recording not started.")
            return

        try:
            if self._file.tell() == 0 and data_lines: # Check if file is empty and data exists
                # Infer number of channels from the first data line
                num_channels = len(data_lines[0].split(','))
                header = ",".join([f"channel{i+1}" for i in range(num_channels)])
                self._file.write(header + '\n')
                print(f"[FileWriterWorker] Wrote header: {header}")
            for line in data_lines:
                self._file.write(line + '\n')
            self._file.flush() # Ensure data is written to disk
            print(f"[FileWriterWorker] Appended {len(data_lines)} lines and flushed.")

            if self._stop_pending and not data_lines: # If stop was requested and no more data is coming
                self.finalize_stop() # Close the file now

        except Exception as e:
            print(f"[FileWriterWorker] Error appending data: {e}")
            self.finished.emit(False, f"Error appending data: {e}")

    @Slot(int)
    def stop_recording(self, end_message_count):
        print(f"[FileWriterWorker] Stop recording requested. Setting _stop_pending flag.")
        self._stop_pending = True
        self.end_message_count = end_message_count # Store for finalize_stop
        # Do NOT close file here. It will be closed in finalize_stop after all data is written.

    @Slot()
    def finalize_stop(self):
        print(f"[FileWriterWorker] Attempting to stop recording. Expected end count: {self.end_message_count}")
        if self._file:
            try:
                self._file.close()
                print(f"[FileWriterWorker] File closed: {self.file_name}")
                self._file = None
                self._stop_pending = False

                # Verify message count
                # This part needs to be re-evaluated. The current implementation relies on
                # reading the file back, which is inefficient and prone to issues if the file
                # is very large or if the data format changes. A better approach would be to
                # track the number of messages written directly within the worker.
                # For now, we'll keep the basic check but acknowledge its limitations.
                try:
                    with open(self.file_name, 'r') as f:
                        lines = f.readlines()
                        # Subtract 1 for the header line if it exists
                        actual_lines_written = len(lines) - 1 if len(lines) > 0 and lines[0].startswith('channel') else len(lines)

                    expected_lines = self.end_message_count - self.start_message_count
                    if actual_lines_written != expected_lines:
                        print(f"[FileWriterWorker] WARNING: {expected_lines - actual_lines_written} messages lost! (Expected: {expected_lines}, Actual: {actual_lines_written})")
                        self.finished.emit(False, f"Recording stopped with data loss. Expected: {expected_lines}, Actual: {actual_lines_written}")
                    else:
                        self.finished.emit(True, f"Recording stopped. {actual_lines_written} lines written.")
                except Exception as e:
                    print(f"[FileWriterWorker] Error verifying file content: {e}")
                    self.finished.emit(False, f"Recording stopped, but verification failed: {e}")

                self.all_data_written.emit() # Emit signal after file is fully processed

            except Exception as e:
                print(f"[FileWriterWorker] Error closing file: {e}")
                self.finished.emit(False, f"Error closing file: {e}")
        else:
            print("[FileWriterWorker] No file to close.")
            self.finished.emit(False, "Recording stopped, but no file was open.")

    @Slot()
    def finalize_recording(self):
        self.finalize_stop()

