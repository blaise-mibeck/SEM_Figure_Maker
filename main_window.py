from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QWidget, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt

from image_grid import ImageGridView

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
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Initialize menu bar
        self.setup_menu_bar()
        
        # Connect export button from image grid
        self.image_grid.export_button.clicked.connect(self.on_export_clicked)
    
    def setup_menu_bar(self):
        """Set up the main menu bar"""
        # Create File menu
        file_menu = self.menuBar().addMenu("File")
        
        # Open folder action
        open_folder_action = file_menu.addAction("Open Folder...")
        # Will connect this in the controller
        
        # Export action
        export_action = file_menu.addAction("Export Grid...")
        # Will connect this in the controller
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Create Collections menu placeholder - will be populated by controller
        self.collections_menu = self.menuBar().addMenu("Collections")
        
        # Create View menu
        view_menu = self.menuBar().addMenu("View")
        
        # View grid size submenu
        grid_size_menu = view_menu.addMenu("Grid Size")
        
        # Populate grid size options
        grid_sizes = ["1x1", "2x2", "3x3", "4x4"]
        for size in grid_sizes:
            action = grid_size_menu.addAction(size)
            # Will connect these in the controller
    
    def on_export_clicked(self) -> None:
        """Handle export button click - to be connected to controller"""
        pass
    
    def update_folder_path(self, path: str) -> None:
        """Update the displayed folder path"""
        self.folder_path_label.setText(path if path else "No folder selected")
    
    def show_message(self, title: str, message: str) -> None:
        """Show a message box to the user"""
        QMessageBox.information(self, title, message)
    
    def show_error(self, title: str, message: str) -> None:
        """Show an error message to the user"""
        QMessageBox.critical(self, title, message)
        
    def show_question(self, title: str, message: str) -> bool:
        """Show a yes/no question dialog to the user
        
        Returns:
            True if user clicked Yes, False otherwise
        """
        response = QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        return response == QMessageBox.Yes
    
    def set_status(self, message: str) -> None:
        """Set the status bar message"""
        self.status_bar.showMessage(message)
    
    def clear_status(self) -> None:
        """Clear the status bar message"""
        self.status_bar.clearMessage()