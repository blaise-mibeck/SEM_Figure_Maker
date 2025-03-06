import os
import sys
from typing import Dict, List, Optional, Tuple, Callable
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, 
                            QFileDialog, QDialog, QGridLayout, QScrollArea, 
                            QComboBox, QCheckBox, QGroupBox, QSpinBox, QMessageBox,
                            QSizePolicy, QFrame)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QFont
from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal, QRectF, QPoint

from PIL import Image, ImageQt


class ImageWidget(QWidget):
    """Widget to display a single image with metadata and optional bounding box"""
    
    boxDrawn = pyqtSignal(QRectF)  # Signal emitted when user draws a box
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.scaled_pixmap = None
        self.metadata_text = ""
        self.show_metadata = True
        self.bounding_boxes = []  # List of (x1,y1,x2,y2) normalized coordinates
        self.box_colors = []      # List of QColor objects for each box
        
        # For drawing mode
        self.drawing = False
        self.draw_start_pos = None
        self.current_rect = None
        self.drawing_enabled = False
        
        # Set up widget properties
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def set_image(self, image_path: str) -> None:
        """Set the image to display"""
        if os.path.exists(image_path):
            self.pixmap = QPixmap(image_path)
            self.update()
        else:
            print(f"Warning: Image not found at {image_path}")
    
    def set_metadata_text(self, text: str) -> None:
        """Set metadata text to display with the image"""
        self.metadata_text = text
        self.update()
    
    def toggle_metadata(self, show: bool) -> None:
        """Toggle metadata display"""
        self.show_metadata = show
        self.update()
    
    def add_bounding_box(self, rect: Tuple[float, float, float, float], color: QColor = Qt.red) -> None:
        """Add a bounding box to display on the image
        rect is (x1, y1, x2, y2) in normalized coordinates (0-1)
        """
        self.bounding_boxes.append(rect)
        self.box_colors.append(color)
        self.update()
    
    def clear_bounding_boxes(self) -> None:
        """Clear all bounding boxes"""
        self.bounding_boxes = []
        self.box_colors = []
        self.update()
    
    def enable_drawing(self, enabled: bool) -> None:
        """Enable or disable box drawing mode"""
        self.drawing_enabled = enabled
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)
        if not enabled:
            self.drawing = False
            self.current_rect = None
            self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse press for drawing boxes"""
        if self.drawing_enabled and event.button() == Qt.LeftButton:
            self.drawing = True
            self.draw_start_pos = event.pos()
            self.current_rect = QRect(self.draw_start_pos, self.draw_start_pos)
            self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for drawing boxes"""
        if self.drawing:
            self.current_rect = QRect(self.draw_start_pos, event.pos()).normalized()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release for drawing boxes"""
        if self.drawing and event.button() == Qt.LeftButton:
            self.drawing = False
            
            # Convert to normalized coordinates
            if self.pixmap and not self.pixmap.isNull():
                x1 = self.draw_start_pos.x() / self.width()
                y1 = self.draw_start_pos.y() / self.height()
                x2 = event.pos().x() / self.width()
                y2 = event.pos().y() / self.height()
                
                rect = QRectF(x1, y1, x2-x1, y2-y1).normalized()
                self.boxDrawn.emit(rect)
            
            self.current_rect = None
            self.update()
    
    def paintEvent(self, event):
        """Paint the widget including image, metadata, and bounding boxes"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Draw background
        painter.fillRect(self.rect(), Qt.white)
        
        # Draw image if available
        if self.pixmap and not self.pixmap.isNull():
            # Scale pixmap to fit widget while maintaining aspect ratio
            self.scaled_pixmap = self.pixmap.scaled(
                self.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            # Center the pixmap in the widget
            x = (self.width() - self.scaled_pixmap.width()) / 2
            y = (self.height() - self.scaled_pixmap.height()) / 2
            
            painter.drawPixmap(int(x), int(y), self.scaled_pixmap)
            
            # Draw bounding boxes
            if self.scaled_pixmap.width() > 0 and self.scaled_pixmap.height() > 0:
                for rect, color in zip(self.bounding_boxes, self.box_colors):
                    x1, y1, x2, y2 = rect
                    
                    # Convert normalized coordinates to widget coordinates
                    box_x = int(x + x1 * self.scaled_pixmap.width())
                    box_y = int(y + y1 * self.scaled_pixmap.height())
                    box_w = int((x2 - x1) * self.scaled_pixmap.width())
                    box_h = int((y2 - y1) * self.scaled_pixmap.height())
                    
                    pen = QPen(color, 2)
                    painter.setPen(pen)
                    painter.drawRect(box_x, box_y, box_w, box_h)
            
            # Draw current rectangle if in drawing mode
            if self.current_rect:
                painter.setPen(QPen(Qt.blue, 2, Qt.DashLine))
                painter.drawRect(self.current_rect)
        
        # Draw metadata if enabled
        if self.show_metadata and self.metadata_text:
            painter.setPen(Qt.black)
            painter.setFont(QFont("Arial", 9))
            painter.drawText(10, self.height() - 10, self.metadata_text)


class ImageGridView(QWidget):
    """Widget to display a grid of images with different magnifications"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        
        # Controls layout
        self.controls_layout = QHBoxLayout()
        self.layout.addLayout(self.controls_layout)
        
        # Add grid size control
        self.grid_size_label = QLabel("Grid size:")
        self.controls_layout.addWidget(self.grid_size_label)
        
        self.grid_size_combo = QComboBox()
        self.grid_size_combo.addItems(["1x1", "2x2", "3x3", "4x4"])
        self.grid_size_combo.setCurrentIndex(1)  # Default to 2x2
        self.grid_size_combo.currentIndexChanged.connect(self.on_grid_size_changed)
        self.controls_layout.addWidget(self.grid_size_combo)
        
        # Add metadata toggle
        self.show_metadata_check = QCheckBox("Show metadata")
        self.show_metadata_check.setChecked(True)
        self.show_metadata_check.stateChanged.connect(self.toggle_metadata)
        self.controls_layout.addWidget(self.show_metadata_check)
        
        # Add draw box toggle
        self.draw_box_check = QCheckBox("Draw magnification boxes")
        self.draw_box_check.setChecked(False)
        self.draw_box_check.stateChanged.connect(self.toggle_drawing_mode)
        self.controls_layout.addWidget(self.draw_box_check)
        
        self.controls_layout.addStretch()
        
        # Add export button
        self.export_button = QPushButton("Export Grid")
        self.controls_layout.addWidget(self.export_button)
        
        # Create scroll area for the grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.scroll_area)
        
        # Create grid container widget
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.scroll_area.setWidget(self.grid_container)
        
        # Initialize with default 2x2 grid
        self.rows = 2
        self.cols = 2
        self.image_widgets = []
        self.setup_grid()
    
    def setup_grid(self) -> None:
        """Set up the grid layout with image widgets"""
        # Clear existing grid
        for widget in self.image_widgets:
            widget.setParent(None)
        
        # Clear layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.image_widgets = []
        
        # Create new grid of ImageWidget instances
        for row in range(self.rows):
            for col in range(self.cols):
                image_widget = ImageWidget()
                self.grid_layout.addWidget(image_widget, row, col)
                self.image_widgets.append(image_widget)
                
                # Connect box drawing signal
                image_widget.boxDrawn.connect(lambda rect, r=row, c=col: self.on_box_drawn(rect, r, c))
    
    def on_grid_size_changed(self, index: int) -> None:
        """Handle grid size change"""
        size_text = self.grid_size_combo.currentText()
        self.rows, self.cols = map(int, size_text.split('x'))
        self.setup_grid()
    
    def set_images(self, image_paths: List[str], metadata_texts: List[str]) -> None:
        """Set images and metadata in the grid"""
        for i, (widget, path) in enumerate(zip(self.image_widgets, image_paths)):
            if i < len(image_paths):
                widget.set_image(path)
                if i < len(metadata_texts):
                    widget.set_metadata_text(metadata_texts[i])
    
    def add_bounding_box(self, widget_index: int, rect: Tuple[float, float, float, float], 
                         color: QColor = Qt.red) -> None:
        """Add a bounding box to a specific image widget"""
        if 0 <= widget_index < len(self.image_widgets):
            self.image_widgets[widget_index].add_bounding_box(rect, color)
    
    def clear_all_bounding_boxes(self) -> None:
        """Clear all bounding boxes from all widgets"""
        for widget in self.image_widgets:
            widget.clear_bounding_boxes()
    
    def toggle_metadata(self, state: int) -> None:
        """Toggle metadata display for all widgets"""
        show = state == Qt.Checked
        for widget in self.image_widgets:
            widget.toggle_metadata(show)
    
    def toggle_drawing_mode(self, state: int) -> None:
        """Toggle box drawing mode for all widgets"""
        enabled = state == Qt.Checked
        for widget in self.image_widgets:
            widget.enable_drawing(enabled)
    
    def on_box_drawn(self, rect: QRectF, row: int, col: int) -> None:
        """Handle box drawn signal from an image widget"""
        # This will be connected to the controller
        pass
    
    def export_grid(self, file_path: str) -> bool:
        """Export the current grid as a PNG image"""
        try:
            # Create a pixmap to render the entire grid
            pixmap = QPixmap(self.grid_container.size())
            pixmap.fill(Qt.white)
            
            # Render the grid container to the pixmap
            self.grid_container.render(pixmap)
            
            # Save the pixmap as PNG
            pixmap.save(file_path, "PNG")
            return True
        except Exception as e:
            print(f"Error exporting grid: {e}")
            return False