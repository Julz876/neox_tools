import sys
import os
import traceback
import argparse
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton, QLabel, QVBoxLayout, QWidget, QStatusBar, QListWidget, QListWidgetItem, QHBoxLayout, QCheckBox, QTextEdit, QTreeView, QFileSystemModel, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
from viewer import ViewerWidget
from util import mesh_from_path
from converter import saveobj, savegltf, parse_mesh
from onmyoji_converter import _parse_mesh 
from extractorNEW import unpack

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("Unhandled exception", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

class ConsoleOutputHandler(QObject):
    text_output = pyqtSignal(str)

    def write(self, text):
        if text.strip():  # Prevent empty lines from being printed
            self.text_output.emit(text)
            sys.__stdout__.write(text)  # Also write to the standard output for VSCode

    def flush(self):
        sys.__stdout__.flush()  # Ensure that the output is flushed immediately

def redirect_output(console_handler):
    sys.stdout = console_handler
    sys.stderr = console_handler

class ProcessingThread(QThread):
    finished = pyqtSignal()
    status_updated = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            # Redirect stdout to emit signals
            old_stdout = sys.stdout
            sys.stdout = self
            try:
                self.func(*self.args, **self.kwargs)
            finally:
                sys.stdout = old_stdout
        except Exception as e:
            traceback.print_exc()
        finally:
            self.finished.emit()

    def write(self, text):
        self.status_updated.emit(text)

    def flush(self):
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('NPK/EXPK Extractor and Mesh Viewer')
        self.setGeometry(100, 100, 1200, 800)

        # Initialize GUI components
        self.initUI()

        # Initialize the console output handler
        self.console_handler = ConsoleOutputHandler()
        self.console_handler.text_output.connect(self.append_console_output)
        redirect_output(self.console_handler)

        # Keep track of the threads to avoid them being garbage collected
        self.threads = []

    def initUI(self):
        # Central widget and main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Splitter for dividing folder tree, file list, and viewer
        splitter = QSplitter(Qt.Horizontal)

        # Folder tree view with filtering for compatible files
        self.folder_tree = QTreeView()
        self.folder_model = QFileSystemModel()
        self.folder_model.setRootPath('')
        self.folder_model.setNameFilters(self.get_supported_extensions())
        self.folder_model.setNameFilterDisables(False)
        self.folder_tree.setModel(self.folder_model)
        self.folder_tree.setRootIndex(self.folder_model.index(''))
        self.folder_tree.clicked.connect(self.on_tree_view_clicked)

        splitter.addWidget(self.folder_tree)

        # List widget to display compatible files
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemSelectionChanged.connect(self.on_file_selected)

        splitter.addWidget(self.file_list_widget)

        # Viewer for .mesh files
        self.viewer = ViewerWidget()

        splitter.addWidget(self.viewer)

        splitter.setSizes([250, 250, 700])

        main_layout.addWidget(splitter)

        # Console output area with adjusted height
        self.console_output = QTextEdit(self)
        self.console_output.setReadOnly(True)
        self.console_output.setFixedHeight(150)
        main_layout.addWidget(self.console_output)

        # Buttons and checkbox
        button_layout = QHBoxLayout()

        self.load_button = QPushButton('Load Folder', self)
        self.load_button.clicked.connect(self.load_folder)
        button_layout.addWidget(self.load_button)

        self.save_obj_button = QPushButton('Save OBJ', self)
        self.save_obj_button.clicked.connect(lambda: self.save_mesh('obj'))
        button_layout.addWidget(self.save_obj_button)

        self.save_gltf_button = QPushButton('Save GLTF', self)
        self.save_gltf_button.clicked.connect(lambda: self.save_mesh('gltf'))
        button_layout.addWidget(self.save_gltf_button)

        self.unpack_button = QPushButton('Unpack', self)
        self.unpack_button.clicked.connect(self.start_unpack)
        button_layout.addWidget(self.unpack_button)

        self.batch_obj_button = QPushButton('Batch OBJ', self)
        self.batch_obj_button.clicked.connect(lambda: self.batch_save_mesh('obj'))
        button_layout.addWidget(self.batch_obj_button)

        self.batch_gltf_button = QPushButton('Batch GLTF', self)
        self.batch_gltf_button.clicked.connect(lambda: self.batch_save_mesh('gltf'))
        button_layout.addWidget(self.batch_gltf_button)

        # Checkbox for flipping UVs
        self.flip_uv_checkbox = QCheckBox('Flip UVs on Y axis', self)
        button_layout.addWidget(self.flip_uv_checkbox)  # Ensure checkbox is added to the layout

        # Checkbox for unpacking the entire folder
        self.unpack_entire_folder_checkbox = QCheckBox('Unpack Entire Folder', self)
        button_layout.addWidget(self.unpack_entire_folder_checkbox)

        main_layout.addLayout(button_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def get_supported_extensions(self):
        # Define the supported file formats
        extensions = ['*.mesh', '*.npk']  # Include .npk for unpacking
        return extensions

    def on_tree_view_clicked(self, index):
        path = self.folder_model.filePath(index)
        if os.path.isdir(path):
            self.list_files_in_folder(path)

    def list_files_in_folder(self, folder_path):
        self.file_list_widget.clear()
        valid_extensions = tuple(ext.replace('*', '') for ext in self.get_supported_extensions())
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(valid_extensions):
                item = QListWidgetItem(file_name)
                item.setData(Qt.UserRole, os.path.join(folder_path, file_name))
                self.file_list_widget.addItem(item)

    def load_folder(self):
        options = QFileDialog.Options()
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", options=options)
        if folder_path:
            self.folder_tree.setRootIndex(self.folder_model.index(folder_path))
            self.list_files_in_folder(folder_path)
            self.folder_path = folder_path
            self.status_bar.showMessage(f'Selected Folder: {os.path.basename(folder_path)}')

    def on_file_selected(self):
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            return
        selected_item = selected_items[0]
        file_path = selected_item.data(Qt.UserRole)
        if file_path.endswith('.mesh'):
            # Try parsing with the primary converter first
            mesh = mesh_from_path(file_path)
            
            if not mesh:
                # If mesh_from_path fails, try the secondary converter
                print(f"Primary parsing failed. Trying secondary parser for {file_path}")
                mesh = _parse_mesh(file_path)
            
            if mesh:
                self.viewer.load_mesh(mesh)
                self.current_mesh = mesh
                self.current_file_path = file_path

                # Display the number of faces and bones
                face_count = len(mesh['face'])
                bone_count = len(mesh['bone_name']) if 'bone_name' in mesh else 0
                self.status_bar.showMessage(f"Loaded {os.path.basename(file_path)}: {face_count} faces, {bone_count} bones.")
            else:
                print(f"Failed to load mesh from {file_path} with both parsers.")
                self.status_bar.showMessage(f"Failed to load mesh from {os.path.basename(file_path)}.")

    def save_mesh(self, mode):
        if hasattr(self, 'current_mesh') and hasattr(self, 'current_file_path'):
            save_path, _ = QFileDialog.getSaveFileName(self, f"Save as {mode.upper()}", self.current_file_path.replace('.mesh', f'.{mode}'), f"{mode.upper()} Files (*.{mode})")
            if not save_path:  # Check if the save_path is valid
                self.status_bar.showMessage('Save operation canceled.')
                return  # Exit the function if the path is not valid

            print(f"Saving {mode.upper()} to: {save_path}")  # Debug statement to print the file path

            flip_uv = self.flip_uv_checkbox.isChecked()  # Get the checkbox state
            try:
                if mode == 'obj':
                    saveobj(self.current_mesh, save_path, flip_uv=flip_uv)  # Pass flip_uv to saveobj
                elif mode == 'gltf':
                    savegltf(self.current_mesh, save_path, flip_uv=flip_uv)  # Pass flip_uv to savegltf
                
                self.status_bar.showMessage(f'{mode.upper()} saved successfully!')
                QMessageBox.information(self, f'Save as {mode.upper()}', f'The mesh has been successfully saved as a {mode.upper()} file.')
            except Exception as e:
                self.status_bar.showMessage(f'Failed to save {mode.upper()}: {str(e)}')
                print(f"Failed to save {mode.upper()}: {e}")
        else:
            self.status_bar.showMessage('No mesh loaded to save.')
            QMessageBox.warning(self, f'Save as {mode.upper()}', 'Please load a mesh file first.')

    def batch_save_mesh(self, mode):
        if hasattr(self, 'folder_path'):
            folder = QFileDialog.getExistingDirectory(self, f"Select Folder to Save {mode.upper()}s")
            if folder:
                for i in range(self.file_list_widget.count()):
                    item = self.file_list_widget.item(i)
                    file_path = item.data(Qt.UserRole)
                    if file_path.endswith('.mesh'):
                        try:
                            print(f"Processing file: {file_path}")
                            
                            # Attempt to parse with parse_mesh first
                            mesh = parse_mesh(file_path)
                            
                            if not mesh:  # If parse_mesh fails, try _parse_mesh
                                print(f"parse_mesh failed for {file_path}. Attempting to use _parse_mesh.")
                                mesh = _parse_mesh(file_path)
                            
                            if not mesh:  # Skip if both parsers fail
                                print(f"Failed to parse {file_path} with both parsers. Skipping.")
                                continue
                            
                            # Determine the save path and save the mesh
                            save_path = os.path.join(folder, os.path.basename(file_path).replace('.mesh', f'.{mode}'))
                            
                            if mode == 'obj':
                                saveobj(mesh, save_path, flip_uv=self.flip_uv_checkbox.isChecked())
                            elif mode == 'gltf':
                                savegltf(mesh, save_path, flip_uv=self.flip_uv_checkbox.isChecked())
                            
                            print(f"Successfully saved: {save_path}")
                            self.status_bar.showMessage(f'Successfully saved: {os.path.basename(file_path)}')
                        
                        except Exception as e:
                            print(f"Error processing {file_path}: {e}")
                            self.status_bar.showMessage(f'Failed to save {os.path.basename(file_path)}: {str(e)}')
                
                QMessageBox.information(self, f'Batch Save as {mode.upper()}', f'Batch save process completed.')
            else:
                self.status_bar.showMessage('No folder selected for batch saving.')
        else:
            self.status_bar.showMessage('No folder loaded for batch saving.')
            QMessageBox.warning(self, f'Batch Save as {mode.upper()}', 'Please load a folder first.')

    def save_mesh_obj(self, file_path, save_path):
        mesh_data = parse_mesh(file_path)
        saveobj(mesh_data, save_path, flip_uv=self.flip_uv_checkbox.isChecked())

    def save_mesh_gltf(self, file_path, save_path):
        mesh_data = parse_mesh(file_path)
        savegltf(mesh_data, save_path, flip_uv=self.flip_uv_checkbox.isChecked())

    def start_unpack(self):
        if hasattr(self, 'folder_path') and self.folder_path:
            if self.unpack_entire_folder_checkbox.isChecked():
                # Unpack the entire folder
                args = argparse.Namespace(path=self.folder_path, info=1, nxfn_file=False, no_nxfn=False, do_one=False, nxs3=False, force=False, delete_compressed=False)
                thread = ProcessingThread(unpack, args)
                thread.status_updated.connect(self.append_console_output)
                thread.finished.connect(lambda: self.on_thread_finished(thread))
                thread.start()
                self.threads.append(thread)
            else:
                # Unpack selected files
                selected_items = self.file_list_widget.selectedItems()
                if not selected_items:
                    self.status_bar.showMessage('Error: No file selected')
                    return

                for item in selected_items:
                    file_path = item.data(Qt.UserRole)
                    args = argparse.Namespace(path=file_path, info=1, nxfn_file=False, no_nxfn=False, do_one=False, nxs3=False, force=False, delete_compressed=False)
                    thread = ProcessingThread(unpack, args)
                    thread.status_updated.connect(self.append_console_output)
                    thread.finished.connect(lambda: self.on_thread_finished(thread))
                    thread.start()
                    self.threads.append(thread)

    def on_thread_finished(self, thread):
        self.threads.remove(thread)
        self.status_bar.showMessage('Unpacking completed')

    def append_console_output(self, text):
        # Append the text to the console output widget
        self.console_output.append(text)
        # Scroll to the bottom to see the latest output
        self.console_output.ensureCursorVisible()

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
