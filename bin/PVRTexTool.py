import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton,
    QLabel, QLineEdit, QVBoxLayout, QWidget, QMessageBox, QProgressBar
)
import subprocess

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('PVRTexToolCLI GUI')
        self.setGeometry(100, 100, 300, 300)

        layout = QVBoxLayout()

        # Input file selection
        self.input_label = QLabel('Select Input File:', self)
        layout.addWidget(self.input_label)
        
        self.input_file = QLineEdit(self)
        layout.addWidget(self.input_file)
        
        self.input_button = QPushButton('Browse', self)
        self.input_button.clicked.connect(self.browse_input_file)
        layout.addWidget(self.input_button)

        # Execute button for single file
        self.single_execute_button = QPushButton('Convert to DDS', self)
        self.single_execute_button.clicked.connect(self.convert_single_file)
        layout.addWidget(self.single_execute_button)

        # PVR folder selection
        self.folder_label = QLabel('Select PVR Folder for Batch Conversion:', self)
        layout.addWidget(self.folder_label)
        
        self.folder_path = QLineEdit(self)
        layout.addWidget(self.folder_path)
        
        self.folder_button = QPushButton('Browse Folder', self)
        self.folder_button.clicked.connect(self.browse_folder)
        layout.addWidget(self.folder_button)

        # Execute button for batch conversion
        self.batch_execute_button = QPushButton('Batch Convert to DDS', self)
        self.batch_execute_button.clicked.connect(self.batch_convert)
        layout.addWidget(self.batch_execute_button)

        # Progress bar for batch processing
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def browse_input_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'PVR Files (*.pvr);;All Files (*)')
        if file_name:
            self.input_file.setText(file_name)

    def browse_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folder_name:
            self.folder_path.setText(folder_name)

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def convert_single_file(self):
        try:
            input_file = self.input_file.text()

            if not input_file:
                self.show_error_message("No input file selected.")
                return

            # Construct the output file name by replacing the .pvr extension with .dds
            output_file = os.path.splitext(input_file)[0] + ".dds"

            # Get the path of the executable
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PVRTexToolCLI.exe")

            # Command to run the PVRTexToolCLI with the .dds extension
            command = f'"{exe_path}" -i "{input_file}" -o "{output_file}"'
            print(f"Running Command: {command}")

            # Run the command
            result = subprocess.run(command, shell=True, check=True)

            # Show success message
            QMessageBox.information(self, "Success", f"Successfully converted {input_file} to DDS.")

        except subprocess.CalledProcessError as e:
            self.show_error_message(f"Failed to convert {input_file}. Error: {str(e)}")
        except Exception as e:
            self.show_error_message(f"An unexpected error occurred: {str(e)}")

    def batch_convert(self):
        try:
            folder_path = self.folder_path.text()

            if not folder_path:
                self.show_error_message("No folder selected.")
                return

            # Get the path of the executable
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PVRTexToolCLI.exe")

            # Recursively search for .pvr files and count them
            total_files = sum([len(files) for r, d, files in os.walk(folder_path) if any(f.endswith('.pvr') for f in files)])
            if total_files == 0:
                self.show_error_message("No .pvr files found in the selected folder.")
                return

            converted_files = 0

            # Initialize the progress bar
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(total_files)

            # Recursively search for .pvr files and convert them
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith('.pvr'):
                        input_file = os.path.join(root, file)
                        output_file = os.path.splitext(input_file)[0] + ".dds"

                        try:
                            # Command to run the PVRTexToolCLI with the .dds extension
                            command = f'"{exe_path}" -i "{input_file}" -o "{output_file}"'
                            print(f"Running Command: {command}")

                            # Run the command
                            subprocess.run(command, shell=True, check=True)
                            converted_files += 1

                        except subprocess.CalledProcessError as e:
                            # Log or print the error and continue with the next file
                            print(f"Failed to convert {input_file}. Error: {str(e)}")
                        except Exception as e:
                            print(f"An unexpected error occurred with {input_file}: {str(e)}")

                        # Update the progress bar
                        self.progress_bar.setValue(converted_files)

            if converted_files > 0:
                QMessageBox.information(self, "Success", "Batch conversion completed successfully.")
            else:
                QMessageBox.information(self, "No Files Converted", "No .pvr files were successfully converted.")

            # Reset progress bar
            self.progress_bar.setValue(0)

        except Exception as e:
            self.show_error_message(f"An unexpected error occurred during batch conversion: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
