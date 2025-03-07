from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
                           QPushButton, QScrollArea, QComboBox, QCheckBox, QSizePolicy,
                           QFrame, QGroupBox, QRadioButton)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QImage
from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal, QRectF, QPoint
from PIL import Image, ImageQt
import os

class ImageWidget(QWidget):
    """Widget to display a single image with metadata, bounding boxes, and borders"""
    
    boxDrawn = pyqtSignal(QRectF)  # Signal emitted when user draws a box
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.scaled_pixmap = None
        self.metadata_text = ""
        self.show_metadata = True
        self.bounding_boxes = []  # List of (x1,y1,x2,y2) normalized coordinates
        self.box_colors = []      # List of QColor objects for each box
        self.box_tooltips = []    # List of (rect, tooltip_text) pairs
        self.border_color = None  # Border color for this image
        self.show_boxes = True    # Whether to show bounding boxes
        self.line_style = Qt.SolidLine  # Line style for bounding boxes
        
        # For drawing mode
        self.drawing = False
        self.draw_start_pos = None
        self.current_rect = None
        self.drawing_enabled = False
        
        # For tooltips
        self.tooltip_rect = None
        self.tooltip_text = None
        
        # Set up widget properties
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Enable mouse tracking for tooltips
        self.setMouseTracking(True)
        
    def set_image(self, image_path: str) -> None:
        """Set the image to display"""
        if os.path.exists(image_path):
            self.pixmap = QPixmap(image_path)
            self.image_path = image_path  # Store the path for reference
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
    
    def add_bounding_box(self, rect: tuple, color: QColor = Qt.red, tooltip: str = None) -> None:
        """Add a bounding box to display on the image
        rect is (x1, y1, x2, y2) in normalized coordinates (0-1)
        """
        self.bounding_boxes.append(rect)
        self.box_colors.append(color)
        if tooltip:
            self.box_tooltips.append((rect, tooltip))
        self.update()
    
    def clear_bounding_boxes(self) -> None:
        """Clear all bounding boxes"""
        self.bounding_boxes = []
        self.box_colors = []
        self.box_tooltips = []
        self.update()
    
    def set_border_color(self, color: QColor) -> None:
        """Set the border color for this image"""
        self.border_color = color
        self.update()
    
    def toggle_boxes(self, show: bool) -> None:
        """Toggle visibility of bounding boxes"""
        self.show_boxes = show
        self.update()
    
    def set_line_style(self, style: int) -> None:
        """Set line style for bounding boxes (Qt.SolidLine, Qt.DashLine, etc.)"""
        self.line_style = style
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
        """Handle mouse move for drawing boxes and tooltips"""
        if self.drawing:
            self.current_rect = QRect(self.draw_start_pos, event.pos()).normalized()
            self.update()
        else:
            # Check if mouse is over a bounding box for tooltip
            if self.pixmap and not self.pixmap.isNull() and self.scaled_pixmap:
                # Get image position
                x = (self.width() - self.scaled_pixmap.width()) / 2
                y = (self.height() - self.scaled_pixmap.height()) / 2
                
                # Convert mouse position to normalized coordinates
                norm_x = (event.x() - x) / self.scaled_pixmap.width()
                norm_y = (event.y() - y) / self.scaled_pixmap.height()
                
                # Check if mouse is over any bounding box
                for i, (rect, tooltip) in enumerate(self.box_tooltips):
                    x1, y1, x2, y2 = rect
                    if x1 <= norm_x <= x2 and y1 <= norm_y <= y2:
                        self.tooltip_rect = rect
                        self.tooltip_text = tooltip
                        self.update()
                        return
                
                # Mouse not over any box
                if self.tooltip_text:
                    self.tooltip_text = None
                    self.tooltip_rect = None
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
        """Paint the widget including image, metadata, bounding boxes, and border"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Draw background
        painter.fillRect(self.rect(), Qt.lightGray)  # Light gray background instead of white
        
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
            
            # Draw border if specified
            if self.border_color:
                border_rect = QRect(
                    int(x) - 3, 
                    int(y) - 3,
                    self.scaled_pixmap.width() + 6,
                    self.scaled_pixmap.height() + 6
                )
                pen = QPen(self.border_color, 3)
                painter.setPen(pen)
                painter.drawRect(border_rect)
            
            # Draw the image
            painter.drawPixmap(int(x), int(y), self.scaled_pixmap)
            
            # Draw bounding boxes if enabled
            if self.show_boxes and self.scaled_pixmap.width() > 0 and self.scaled_pixmap.height() > 0:
                for rect, color in zip(self.bounding_boxes, self.box_colors):
                    x1, y1, x2, y2 = rect
                    
                    # Convert normalized coordinates to widget coordinates
                    box_x = int(x + x1 * self.scaled_pixmap.width())
                    box_y = int(y + y1 * self.scaled_pixmap.height())
                    box_w = int((x2 - x1) * self.scaled_pixmap.width())
                    box_h = int((y2 - y1) * self.scaled_pixmap.height())
                    
                    pen = QPen(color, 2, self.line_style)
                    painter.setPen(pen)
                    painter.drawRect(box_x, box_y, box_w, box_h)
            
            # Draw current rectangle if in drawing mode
            if self.current_rect:
                painter.setPen(QPen(Qt.blue, 2, Qt.DashLine))
                painter.drawRect(self.current_rect)
                
            # Draw tooltip if needed
            if self.tooltip_text and self.tooltip_rect:
                x1, y1, x2, y2 = self.tooltip_rect
                
                # Convert normalized coordinates to widget coordinates
                box_x = int(x + x1 * self.scaled_pixmap.width())
                box_y = int(y + y1 * self.scaled_pixmap.height())
                
                # Draw tooltip background
                tooltip_rect = QRect(box_x, box_y - 30, 200, 30)
                painter.fillRect(tooltip_rect, QColor(255, 255, 220, 230))  # Light yellow background
                painter.setPen(QPen(Qt.black))
                painter.drawRect(tooltip_rect)
                
                # Draw tooltip text
                painter.drawText(tooltip_rect, Qt.AlignCenter, self.tooltip_text)
        else:
            # Draw placeholder text if no image
            painter.setPen(Qt.darkGray)
            painter.setFont(self.font())
            painter.drawText(self.rect(), Qt.AlignCenter, "Click to load image")
        
        # Draw metadata if enabled
        if self.show_metadata and self.metadata_text:
            painter.setPen(Qt.black)
            painter.setFont(self.font())
            painter.drawText(10, self.height() - 10, self.metadata_text)


class ImageGridView(QWidget):
    """Widget to display a grid of images with metadata, bounding boxes, and borders"""
    
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
        
        # Add bounding box controls
        self.box_controls = QGroupBox("Bounding Boxes")
        box_controls_layout = QVBoxLayout(self.box_controls)
        
        # Show/hide bounding boxes
        self.show_boxes_check = QCheckBox("Show bounding boxes")
        self.show_boxes_check.setChecked(True)
        self.show_boxes_check.stateChanged.connect(self.toggle_boxes)
        box_controls_layout.addWidget(self.show_boxes_check)
        
        # Line style options
        line_style_layout = QHBoxLayout()
        line_style_layout.addWidget(QLabel("Line style:"))
        
        self.solid_line_radio = QRadioButton("Solid")
        self.solid_line_radio.setChecked(True)
        self.solid_line_radio.toggled.connect(lambda: self.set_line_style(Qt.SolidLine))
        line_style_layout.addWidget(self.solid_line_radio)
        
        self.dashed_line_radio = QRadioButton("Dashed")
        self.dashed_line_radio.toggled.connect(lambda: self.set_line_style(Qt.DashLine))
        line_style_layout.addWidget(self.dashed_line_radio)
        
        self.dotted_line_radio = QRadioButton("Dotted")
        self.dotted_line_radio.toggled.connect(lambda: self.set_line_style(Qt.DotLine))
        line_style_layout.addWidget(self.dotted_line_radio)
        
        box_controls_layout.addLayout(line_style_layout)
        
        self.controls_layout.addWidget(self.box_controls)
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
        
        # Set small spacing between images
        self.grid_layout.setSpacing(5)  # 5 pixel spacing between grid items
        
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
    
    def set_images(self, image_paths: list, metadata_texts: list) -> None:
        """Set images and metadata in the grid"""
        for i, widget in enumerate(self.image_widgets):
            if i < len(image_paths):
                widget.set_image(image_paths[i])
                if i < len(metadata_texts):
                    widget.set_metadata_text(metadata_texts[i])
    
    def set_images_from_collection(self, collection):
        """Set images using a collection object"""
        # Sort images by magnification
        sorted_images = sorted(collection.images, 
                             key=lambda x: collection.metadata[x].get("Mag(pol)", 0))
        
        # Limit to the number of grid cells available
        display_images = sorted_images[:len(self.image_widgets)]
        
        # Prepare image paths and metadata texts
        image_paths = display_images
        metadata_texts = [
            f"Mag: {collection.metadata[img].get('Mag(pol)', 0)}x | {os.path.basename(img)}"
            for img in display_images
        ]
        
        # Set images in grid
        self.set_images(image_paths, metadata_texts)
        
        # Clear any existing bounding boxes
        self.clear_all_bounding_boxes()
        
        # Add bounding boxes based on collection containment relationships
        for i, img_path in enumerate(display_images):
            # Check if this image contains others
            if img_path in collection.containment:
                for child_img in collection.containment[img_path]:
                    if child_img in display_images:
                        child_idx = display_images.index(child_img)
                        
                        # Get bounding box
                        bbox = collection.bounding_boxes.get((img_path, child_img))
                        if bbox:
                            # Get color
                            color_rgba = collection.colors.get(child_img)
                            if color_rgba:
                                color = QColor(*color_rgba)
                            else:
                                color = QColor(255, 0, 0, 180)  # Default red
                            
                            # Add box to parent image
                            tooltip = f"{os.path.basename(child_img)}\n{collection.metadata[child_img].get('Mag(pol)', 0)}x"
                            self.add_bounding_box(i, bbox, color, tooltip)
                            
                            # Add colored border to child image
                            self.set_border_color(child_idx, color)
    
    def add_bounding_box(self, widget_index: int, rect: tuple, color: QColor = Qt.red, tooltip: str = None) -> None:
        """Add a bounding box to a specific image widget"""
        if 0 <= widget_index < len(self.image_widgets):
            self.image_widgets[widget_index].add_bounding_box(rect, color, tooltip)
    
    def clear_all_bounding_boxes(self) -> None:
        """Clear all bounding boxes from all widgets"""
        for widget in self.image_widgets:
            widget.clear_bounding_boxes()
    
    def set_border_color(self, widget_index: int, color: QColor) -> None:
        """Set border color for a specific image widget"""
        if 0 <= widget_index < len(self.image_widgets):
            self.image_widgets[widget_index].set_border_color(color)
    
    def toggle_boxes(self, state: int) -> None:
        """Toggle bounding box visibility for all widgets"""
        show = state == Qt.Checked
        for widget in self.image_widgets:
            widget.toggle_boxes(show)
    
    def set_line_style(self, style: int) -> None:
        """Set line style for all bounding boxes"""
        for widget in self.image_widgets:
            widget.set_line_style(style)
    
    def on_box_drawn(self, rect: QRectF, row: int, col: int) -> None:
        """Handle box drawn signal from an image widget"""
        # This will be connected to the controller
        print(f"Box drawn at row {row}, col {col}: {rect.x():.2f}, {rect.y():.2f}, {rect.width():.2f}, {rect.height():.2f}")
    
    def clear_all(self) -> None:
        """Clear all images"""
        for widget in self.image_widgets:
            widget.pixmap = None
            widget.scaled_pixmap = None
            widget.clear_bounding_boxes()
            widget.update()
    
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
