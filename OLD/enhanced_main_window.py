from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QWidget)
from PyQt5.QtCore import Qt

from enhanced_image_grid import EnhancedImageGridView

class EnhancedMainWindow(QMainWindow):
    """Main application window with enhanced image grid"""
    
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
        
        # Add the enhanced image grid view
        self.image_grid = EnhancedImageGridView()
        self.main_layout.addWidget(self.image_grid)
    
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
