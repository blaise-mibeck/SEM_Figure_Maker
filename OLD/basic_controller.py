import os
import sys
from typing import Dict, List, Optional, Tuple
import glob
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import QFileDialog, QApplication, QMainWindow, QMessageBox
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QRectF
from PIL import Image

from view_classes import ImageGridView

class BasicController:
    """Simple controller for the ScaleGrid application"""
    
    def __init__(self):
        # Initialize view
        self.main_window = self._create_main_window()
        
        # Current application state
        self.current_folder = None
        
        # Connect signals
        self.connect_signals()
    
    def _create_main_window(self):
        """Create the main window with menu and controls"""
        from view_dialogs import MainWindow
        main_window = MainWindow()
        return main_window
    
    def connect_signals(self):
        """Connect UI signals to controller methods"""
        # Connect folder selection button
        self.main_window.folder_button.clicked.connect(self.on_folder_button_clicked)
        
        # Connect export button
        self.main_window.image_grid.export_button.clicked.connect(self.on_export_button_clicked)
        
        # Connect individual image widgets for click events
        for i, widget in enumerate(self.main_window.image_grid.image_widgets):
            widget.mousePressEvent = lambda event, idx=i: self.on_image_widget_click(event, idx)
    
    def run(self):
        """Start the application"""
        self.main_window.show()
        
    def on_image_widget_click(self, event, widget_index):
        """Handle click on an image widget"""
        # Only handle left clicks
        if event.button() == Qt.LeftButton:
            # If no folder loaded, prompt to select one
            if not self.current_folder:
                self.on_folder_button_clicked()
                return
                
            # Let the original mousePressEvent handle drawing boxes if enabled
            if self.main_window.image_grid.image_widgets[widget_index].drawing_enabled:
                # Call the original implementation
                ImageWidget = type(self.main_window.image_grid.image_widgets[widget_index])
                ImageWidget.mousePressEvent(self.main_window.image_grid.image_widgets[widget_index], event)
                return
                
            # Otherwise, let the user select an image from the folder
            self.select_image_for_widget(widget_index)
    
    def on_folder_button_clicked(self):
        """Handle folder selection button click"""
        folder_path = QFileDialog.getExistingDirectory(
            self.main_window, "Select SEM Images Folder")
        
        if folder_path:
            self.load_folder(folder_path)
    
    def load_folder(self, folder_path):
        """Load images from a folder"""
        try:
            self.current_folder = folder_path
            self.main_window.update_folder_path(folder_path)
            
            # Get a list of TIFF files in the folder
            image_files = glob.glob(os.path.join(folder_path, "*.tiff")) + glob.glob(os.path.join(folder_path, "*.tif"))
            
            if not image_files:
                self.main_window.show_message("No Images", f"No TIFF images found in {folder_path}")
                return
                
            # Extract metadata for all images
            self.image_metadata = {}
            for image_file in image_files:
                metadata = self.extract_basic_metadata(image_file)
                if metadata:
                    self.image_metadata[image_file] = metadata
            
            # Sort images by magnification
            sorted_images = sorted(image_files, key=lambda x: self.image_metadata.get(x, {}).get("Mag(pol)", 0))
            
            # Display the images in the grid
            self.display_images(sorted_images[:4])  # Display up to 4 images for now
            
            # Add bounding boxes to show magnification relationships
            self.add_magnification_boxes()
            
            self.main_window.show_message(
                "Folder Loaded", 
                f"Loaded {len(image_files)} images from {folder_path}"
            )
        except Exception as e:
            self.main_window.show_error("Error", f"Failed to load folder: {str(e)}")
    
    def add_magnification_boxes(self):
        """Add bounding boxes to show where high-mag images are located in low-mag images"""
        try:
            # Get displayed images and their widgets
            displayed_images = []
            for widget in self.main_window.image_grid.image_widgets:
                if hasattr(widget, 'image_path') and widget.image_path:
                    displayed_images.append(widget.image_path)
            
            print(f"\nDisplayed images: {len(displayed_images)}")
            for img in displayed_images:
                mag = self.image_metadata.get(img, {}).get("Mag(pol)", "Unknown")
                print(f"  - {os.path.basename(img)}: {mag}x")
            
            if len(displayed_images) < 2:
                print("Not enough images displayed to show relationships")
                return  # Need at least 2 images to show relationships
            
            # Sort all images by magnification (lowest to highest)
            all_sorted_images = sorted(self.image_metadata.keys(), 
                                      key=lambda x: self.image_metadata.get(x, {}).get("Mag(pol)", 0))
            
            # Sort displayed images by magnification
            sorted_displayed = sorted(displayed_images, 
                                     key=lambda x: self.image_metadata.get(x, {}).get("Mag(pol)", 0))
            
            # Track how many boxes we calculate and display
            boxes_calculated = 0
            boxes_displayed = 0
            
            # Create a mapping of high-mag images to their colors
            high_mag_colors = {}
            
            # For each pair of adjacent magnification levels
            for i in range(len(sorted_displayed) - 1):
                low_mag_img = sorted_displayed[i]
                high_mag_img = sorted_displayed[i+1]
                low_mag_idx = displayed_images.index(low_mag_img)
                high_mag_idx = displayed_images.index(high_mag_img)
                
                low_mag_meta = self.image_metadata.get(low_mag_img, {})
                high_mag_meta = self.image_metadata.get(high_mag_img, {})
                
                low_mag_name = os.path.basename(low_mag_img)
                high_mag_name = os.path.basename(high_mag_img)
                
                print(f"\nChecking if {high_mag_name} ({high_mag_meta.get('Mag(pol)', 0)}x) is inside {low_mag_name} ({low_mag_meta.get('Mag(pol)', 0)}x)")
                
                # Calculate bounding box
                box = self.calculate_bounding_box(low_mag_meta, high_mag_meta)
                if box:
                    boxes_calculated += 1
                    print(f"  -> FOUND CONTAINMENT! Box: {box}")
                    
                    # Determine color based on magnification ratio
                    mag_ratio = high_mag_meta.get("Mag(pol)", 0) / max(1, low_mag_meta.get("Mag(pol)", 1))
                    
                    if mag_ratio < 5:
                        color = QColor(0, 255, 0, 128)  # Green for small mag change
                    elif mag_ratio < 20:
                        color = QColor(255, 255, 0, 128)  # Yellow for medium mag change
                    else:
                        color = QColor(255, 0, 0, 128)  # Red for large mag change
                    
                    # Store the color for the high-mag image
                    high_mag_colors[high_mag_img] = color
                    
                    # Get the filename to display in the tooltip
                    high_mag_filename = os.path.basename(high_mag_img)
                    
                    print(f"  -> Adding box to widget at index {low_mag_idx}")
                    
                    # Add box to low-mag image
                    self.main_window.image_grid.add_bounding_box(
                        low_mag_idx, box, color, 
                        tooltip=f"{high_mag_filename}\n{high_mag_meta.get('Mag(pol)', 0)}x")
                    
                    # Add colored border to high-mag image
                    self.main_window.image_grid.set_border_color(high_mag_idx, color)
                    
                    boxes_displayed += 1
                else:
                    print(f"  -> NO CONTAINMENT")
            
            print(f"\nSummary: Calculated {boxes_calculated} boxes, displayed {boxes_displayed} boxes")
            
        except Exception as e:
            print(f"Error adding magnification boxes: {e}")
            import traceback
            traceback.print_exc()

    
    def calculate_bounding_box(self, low_mag_meta, high_mag_meta):
        """
        Calculate the normalized bounding box coordinates of a high-mag image within a low-mag image
        Returns tuple (x1, y1, x2, y2) with values from 0 to 1
        """
        try:
            # Get stage positions (in micrometers)
            if "sample_position_x" not in low_mag_meta or "sample_position_x" not in high_mag_meta:
                print("  -> Missing position data")
                return None
                
            low_x = low_mag_meta["sample_position_x"]
            low_y = low_mag_meta["sample_position_y"]
            high_x = high_mag_meta["sample_position_x"]
            high_y = high_mag_meta["sample_position_y"]
            
            # Get field widths (in micrometers)
            if "field_of_view_width" not in low_mag_meta or "field_of_view_width" not in high_mag_meta:
                print("  -> Missing field of view data")
                return None
                
            low_fov_w = low_mag_meta["field_of_view_width"]
            low_fov_h = low_mag_meta["field_of_view_height"]
            high_fov_w = high_mag_meta["field_of_view_width"]
            high_fov_h = high_mag_meta["field_of_view_height"]
            
            print(f"  Low mag: pos=({low_x}, {low_y}), FOV=({low_fov_w}, {low_fov_h})")
            print(f"  High mag: pos=({high_x}, {high_y}), FOV=({high_fov_w}, {high_fov_h})")
            
            # Check if high-mag FOV is fully contained within low-mag FOV
            # For X axis
            low_mag_x_min = low_x - low_fov_w/2
            low_mag_x_max = low_x + low_fov_w/2
            high_mag_x_min = high_x - high_fov_w/2
            high_mag_x_max = high_x + high_fov_w/2
            
            # For Y axis
            low_mag_y_min = low_y - low_fov_h/2
            low_mag_y_max = low_y + low_fov_h/2
            high_mag_y_min = high_y - high_fov_h/2
            high_mag_y_max = high_y + high_fov_h/2
            
            print(f"  X containment check: {low_mag_x_min} < {high_mag_x_min} and {low_mag_x_max} > {high_mag_x_max}")
            print(f"  Y containment check: {low_mag_y_min} < {high_mag_y_min} and {low_mag_y_max} > {high_mag_y_max}")
            
            # Allow a small margin for containment (5% of the low mag FOV)
            margin_x = low_fov_w * 0.05
            margin_y = low_fov_h * 0.05
            
            # Check if high mag FOV is inside low mag FOV (with margin)
            x_contained = ((low_mag_x_min - margin_x) < high_mag_x_min and 
                           (low_mag_x_max + margin_x) > high_mag_x_max)
            y_contained = ((low_mag_y_min - margin_y) < high_mag_y_min and 
                           (low_mag_y_max + margin_y) > high_mag_y_max)
            
            print(f"  X contained: {x_contained}, Y contained: {y_contained}")
            
            if x_contained and y_contained:
                # Calculate normalized coordinates (0-1) where (0,0) is top-left of the image
                # First, find the position of the high-mag FOV corners relative to the low-mag center
                rel_left = (high_mag_x_min - low_x) / low_fov_w
                rel_right = (high_mag_x_max - low_x) / low_fov_w
                # For y-coordinates, we invert because image coordinates have (0,0) at top-left
                rel_top = -(high_mag_y_max - low_y) / low_fov_h
                rel_bottom = -(high_mag_y_min - low_y) / low_fov_h
                
                # Convert to normalized coordinates (0-1) centered at (0.5, 0.5)
                x1 = 0.5 + rel_left
                x2 = 0.5 + rel_right
                y1 = 0.5 + rel_top
                y2 = 0.5 + rel_bottom
                
                print(f"  Relative positions: left={rel_left}, right={rel_right}, top={rel_top}, bottom={rel_bottom}")
                print(f"  Normalized coords: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
                
                # Ensure coordinates are within bounds
                x1 = max(0, min(1, x1))
                y1 = max(0, min(1, y1))
                x2 = max(0, min(1, x2))
                y2 = max(0, min(1, y2))
                
                print(f"  Final box: {x1:.2f}, {y1:.2f}, {x2:.2f}, {y2:.2f}")
                
                return (x1, y1, x2, y2)
            
            return None
            
        except Exception as e:
            print(f"Error calculating bounding box: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def display_images(self, image_files):
        """Display images in the grid"""
        # Clear the grid first
        self.main_window.image_grid.clear_all_bounding_boxes()
        
        # Create lists for image paths and metadata texts
        image_paths = []
        metadata_texts = []
        
        for i, image_file in enumerate(image_files):
            image_paths.append(image_file)
            
            # Extract basic metadata, but we won't display it since it's already in the databar
            try:
                metadata = self.extract_basic_metadata(image_file)
                metadata_text = ""  # Empty since databar already has metadata
            except Exception as e:
                metadata_text = ""
            
            metadata_texts.append(metadata_text)
        
        # Set images in grid
        self.main_window.image_grid.set_images(image_paths, metadata_texts)
        
    def select_image_for_widget(self, widget_index):
        """Allow user to select an image for a specific grid position"""
        if not self.current_folder:
            return
            
        # Open file dialog to choose image from the current folder
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Select Image for Grid Position",
            self.current_folder,
            "Image Files (*.tiff *.tif *.png *.jpg)"
        )
        
        if file_path:
            # Update the image widget
            widget = self.main_window.image_grid.image_widgets[widget_index]
            widget.set_image(file_path)
            widget.set_metadata_text("")  # No metadata text, using databar instead
    
    def extract_basic_metadata(self, image_path):
        """Extract basic metadata from image file"""
        try:
            # Try to extract embedded XML metadata using the improved method
            metadata = self.extract_metadata_from_tiff(image_path)
            if metadata:
                return metadata
            
            # Fallback to basic file properties
            return {"filename": os.path.basename(image_path)}
        except Exception as e:
            print(f"Error extracting metadata from {image_path}: {e}")
            return {}
    
    def extract_metadata_from_tiff(self, tiff_path):
        """
        Extracts and parses the XML metadata embedded in a TIFF image.
        
        Args:
            tiff_path (str): Path to the TIFF file.

        Returns:
            dict: Extracted metadata as a dictionary.
        """
        try:
            # Open the TIFF file using Pillow
            with Image.open(tiff_path) as img:
                # TIFF images may store metadata in their "info" dictionary
                xml_data = img.tag_v2.get(34683)  # 34683 is the TIFF tag for Phenom XML metadata
                
                if not xml_data:
                    print(f"No XML metadata found in {tiff_path}")
                    return {}
                
                # Convert bytes to string if necessary
                if isinstance(xml_data, bytes):
                    xml_data = xml_data.decode("utf-8")

                # Parse the XML
                root = ET.fromstring(xml_data)

                width_pix = int(root.find("cropHint/right").text) # in pixels
                height_pix = int(root.find("cropHint/bottom").text) #in pixels
                pixel_dim_nm = float(root.find("pixelWidth").text)  # in nm
                field_of_view_width = pixel_dim_nm*width_pix/1000 # in um
                field_of_view_height = pixel_dim_nm*height_pix/1000 # in um
                mag_pol = int(127000/field_of_view_width)

                multi_stage = root.find("multiStage")
                
                multi_stage_x = None
                multi_stage_y = None
                beam_shift_x = None
                beam_shift_y = None

                if multi_stage:
                    for axis in multi_stage.findall("axis"):
                        if axis.get("id") == "X":
                            multi_stage_x = float(axis.text)
                        elif axis.get("id") == "Y":
                            multi_stage_y = float(axis.text)

                beam_shift = root.find("acquisition/scan/beamShift")
                if beam_shift is not None:
                    beam_shift_x = float(beam_shift.find("x").text)
                    beam_shift_y = float(beam_shift.find("y").text)
                else:
                    beam_shift_x = None
                    beam_shift_y = None

                # Extract required metadata
                data = {
                    "databarLabel": root.findtext("databarLabel"),
                    "time": root.findtext("time"),
                    "pixels_width": width_pix,
                    "pixels_height": height_pix,
                    "pixel_dimension_nm": pixel_dim_nm,  # assuming square pixels
                    "field_of_view_width": field_of_view_width,
                    "field_of_view_height": field_of_view_height, 
                    "Mag(pol)": mag_pol,  # Keep this key for compatibility
                    "mag_pol": mag_pol, 
                    "sample_position_x": float(root.find("samplePosition/x").text), # in um
                    "sample_position_y": float(root.find("samplePosition/y").text), # in um
                    "multistage_X": multi_stage_x,
                    "multistage_Y": multi_stage_y,
                    "beam_shift_x": beam_shift_x,
                    "beam_shift_y": beam_shift_y,
                    "spot_size": float(root.find("acquisition/scan/spotSize").text),
                    "detector": root.find("acquisition/scan/detector").text,
                    "dwell_time_ns": int(root.find("acquisition/scan/dwellTime").text),
                    "contrast": float(root.find("appliedContrast").text),
                    "gamma": float(root.find("appliedGamma").text),
                    "brightness": float(root.find("appliedBrightness").text),
                    "pressure_Pa": float(root.find("samplePressureEstimate").text),
                    "high_voltage_kV": float(root.find("acquisition/scan/highVoltage").text) / 1000,  # Convert to kV
                    "emission_current_uA": float(root.find("acquisition/scan/emissionCurrent").text),
                    "working_distance_mm": float(root.find("workingDistance").text)
                }
                
                # Add stage_x and stage_y for compatibility with existing code
                data["stage_x"] = data["sample_position_x"]
                data["stage_y"] = data["sample_position_y"]
                
                # Add hfw and hfh for compatibility with existing code
                data["hfw"] = data["field_of_view_width"]
                data["hfh"] = data["field_of_view_height"]
                
                return data
        except Exception as e:
            print(f"Error in extract_metadata_from_tiff for {tiff_path}: {e}")
            return {}
    

    def on_export_button_clicked(self):
        """Handle export button click"""
        if not self.current_folder:
            self.main_window.show_error("Error", "No folder loaded")
            return
            
        # Get sample name from metadata or folder
        sample_id = "Unknown"
        folder_name = os.path.basename(self.current_folder)
        
        # Try to extract SEM1-### pattern from folder name
        import re
        folder_match = re.search(r'(SEM\d+-\d+)', folder_name)
        prefix = folder_match.group(1) if folder_match else folder_name
        
        # Try to get sample ID
        if hasattr(self, 'current_sample') and self.current_sample:
            sample_id = self.current_sample.sample_id
        else:
            # Ask for sample information if not available
            self.on_sample_info_button_clicked(folder_name)
            if hasattr(self, 'current_sample') and self.current_sample:
                sample_id = self.current_sample.sample_id
        
        # Find the next available grid number
        grid_number = 1
        while True:
            filename = f"{prefix}_{sample_id}_ScaleGrid-{grid_number}.png"
            full_path = os.path.join(self.current_folder, filename)
            if not os.path.exists(full_path):
                break
            grid_number += 1
        
        # Suggest default path with standardized naming
        default_path = os.path.join(self.current_folder, filename)
        
        # Show save dialog with default path
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window, 
            "Save Grid As", 
            default_path,
            "PNG Files (*.png)"
        )
        
        if file_path:
            success = self.main_window.image_grid.export_grid(file_path)
            
            if success:
                # Ask what to do next
                response = QMessageBox.question(
                    self.main_window,
                    "Export Complete",
                    f"Grid exported to {file_path}\n\nWhat would you like to do next?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes
                )
                
                if response == QMessageBox.Yes:  # "Reset"
                    # Clear current grid for new images from same folder
                    self.main_window.image_grid.clear_all()
                    self.display_next_set_of_images()
                elif response == QMessageBox.No:  # "New Folder"
                    # Prompt for a new folder
                    self.on_folder_button_clicked()
                elif response == QMessageBox.Cancel:  # "Close"
                    # Close the application
                    self.main_window.close()
            else:
                self.main_window.show_error(
                    "Export Failed", 
                    "Failed to export grid"
                )
                
    def display_next_set_of_images(self):
        """Display the next set of images from the current folder"""
        if not self.current_folder:
            return
            
        # Get a list of all TIFF files in the folder
        image_files = glob.glob(os.path.join(self.current_folder, "*.tiff")) + glob.glob(os.path.join(self.current_folder, "*.tif"))
        
        # If we've already displayed some images, find the last one
        displayed_images = []
        for widget in self.main_window.image_grid.image_widgets:
            if widget.pixmap is not None and hasattr(widget, 'image_path'):
                displayed_images.append(widget.image_path)
        
        # Find where to start the next set
        start_index = 0
        if displayed_images:
            last_image = displayed_images[-1]
            if last_image in image_files:
                start_index = image_files.index(last_image) + 1
        
        # Get the next set of images
        num_images = len(self.main_window.image_grid.image_widgets)
        next_images = image_files[start_index:start_index + num_images]
        
        if not next_images:
            QMessageBox.information(
                self.main_window,
                "End of Images",
                "No more images available in this folder.",
                QMessageBox.Ok
            )
            return
            
        # Display the next set of images
        self.display_images(next_images)
