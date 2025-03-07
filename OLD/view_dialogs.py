from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QTextEdit, QPushButton, QDialogButtonBox, QFileDialog,
                            QFormLayout, QGroupBox, QComboBox, QSpinBox, QCheckBox, QMainWindow, QWidget)
from PyQt5.QtCore import Qt
from typing import Dict, Optional, Tuple
from view_classes import ImageGridView

class SampleInfoDialog(QDialog):
    """Dialog to collect sample information from the user"""
    
    def __init__(self, parent=None, folder_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Sample Information")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Form layout for input fields
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Sample ID (pre-filled with folder name)
        self.sample_id_edit = QLineEdit()
        if folder_name:
            # Try to extract prefix from folder name (e.g., SEM1-123)
            import re
            folder_match = re.search(r'(SEM\d+-\d+)', folder_name)
            if folder_match:
                prefix = folder_match.group(1)
                self.sample_id_edit.setText(prefix)
            else:
                self.sample_id_edit.setText(folder_name)
        form_layout.addRow("Sample ID:", self.sample_id_edit)
        
        # Preparation method
        self.prep_method_edit = QLineEdit()
        form_layout.addRow("Preparation method:", self.prep_method_edit)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(100)
        form_layout.addRow("Notes:", self.notes_edit)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_sample_info(self) -> Dict[str, str]:
        """Get the sample information entered by the user"""
        return {
            "sample_id": self.sample_id_edit.text(),
            "preparation_method": self.prep_method_edit.text(),
            "notes": self.notes_edit.toPlainText()
        }


class ExportDialog(QDialog):
    """Dialog for configuring image export options"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Options")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Image format selection
        format_group = QGroupBox("Image Format")
        format_layout = QVBoxLayout(format_group)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "TIFF"])
        format_layout.addWidget(self.format_combo)
        
        layout.addWidget(format_group)
        
        # Image size options
        size_group = QGroupBox("Image Size")
        size_layout = QFormLayout(size_group)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(500, 10000)
        self.width_spin.setValue(2000)
        self.width_spin.setSingleStep(100)
        size_layout.addRow("Width (px):", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(500, 10000)
        self.height_spin.setValue(2000)
        self.height_spin.setSingleStep(100)
        size_layout.addRow("Height (px):", self.height_spin)
        
        self.maintain_aspect_check = QCheckBox("Maintain aspect ratio")
        self.maintain_aspect_check.setChecked(True)
        size_layout.addRow("", self.maintain_aspect_check)
        
        layout.addWidget(size_group)
        
        # Add DPI setting
        dpi_group = QGroupBox("Resolution")
        dpi_layout = QFormLayout(dpi_group)
        
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        dpi_layout.addRow("DPI:", self.dpi_spin)
        
        layout.addWidget(dpi_group)
        
        # File selection
        file_group = QGroupBox("Output File")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        file_layout.addWidget(self.file_path_edit)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_button)
        
        layout.addWidget(file_group)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def browse_file(self) -> None:
        """Open file browser to select output file"""
        file_format = self.format_combo.currentText().lower()
        file_filter = f"{file_format.upper()} Files (*.{file_format})"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Export As", "", file_filter)
        
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def get_export_options(self) -> Dict:
        """Get the export options entered by the user"""
        return {
            "format": self.format_combo.currentText().lower(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "maintain_aspect": self.maintain_aspect_check.isChecked(),
            "dpi": self.dpi_spin.value(),
            "file_path": self.file_path_edit.text()
        }


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScaleGrid - SEM Image Analysis")
        self.resize(1200, 800)
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Add toolbar-like controls at the top
        self.toolbar_layout = QHBoxLayout()
        self.main_layout.addLayout(self.toolbar_layout)
        
        # Add folder selection
        self.folder_button = QPushButton("Open Folder...")
        self.toolbar_layout.addWidget(self.folder_button)
        
        self.folder_path_label = QLabel("No folder selected")
        self.toolbar_layout.addWidget(self.folder_path_label)
        
        self.toolbar_layout.addStretch()
        
        # Add sample info button
        self.sample_info_button = QPushButton("Sample Info")
        self.toolbar_layout.addWidget(self.sample_info_button)
        
        # Add the image grid view
        self.image_grid = ImageGridView()
        self.main_layout.addWidget(self.image_grid)
        
        # Connect export button from image grid
        self.image_grid.export_button.clicked.connect(self.on_export_clicked)
    
    def on_export_clicked(self) -> None:
        """Handle export button click - to be connected to controller"""
        pass
    
    def update_folder_path(self, path: str) -> None:
        """Update the displayed folder path"""
        self.folder_path_label.setText(path if path else "No folder selected")
    
    def show_message(self, title: str, message: str) -> None:
        """Show a message box to the user"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, title, message)
    
    def show_error(self, title: str, message: str) -> None:
        """Show an error message to the user"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, title, message)
