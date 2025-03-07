import os
import sys
from typing import Dict, List, Optional, Tuple
import glob
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import (QFileDialog, QApplication, QMainWindow, QMessageBox,
                            QMenu, QAction, QActionGroup)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QRectF

from PIL import Image

# Import custom enhanced ImageGridView
from enhanced_image_grid import EnhancedImageGridView

# Import the collection manager
from collection_manager import CollectionManager, ImageCollection

# Import the modified workflow
from modified_scalegrid_workflow import ModifiedScaleGridWorkflow

class EnhancedController:
    """Enhanced controller for the ScaleGrid application with collection support"""
    
    def __init__(self):
        # Initialize collection manager
        self.collection_manager = CollectionManager()
        
        # Initialize view
        self.main_window = self._create_main_window()
        
        # Current application state
        self.current_folder = None
        self.current_collections = []
        self.current_collection = None
        
        # Connect signals
        self.connect_signals()
        
        # Initialize modified workflow
        self.scale_grid_workflow = ModifiedScaleGridWorkflow(None)  # No data repository needed
    
    def _create_main_window(self):
        """Create the main window with menu and controls"""
        from view_dialogs import MainWindow
        main_window = MainWindow()
        
        # Create menu for collections
        self.collections_menu = main_window.menuBar().addMenu("Collections")
        
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
            
            # Get sample ID from folder name
            sample_id = os.path.basename(folder_path)
            import re
            folder_match = re.search(r'(SEM\d+-\d+)', sample_id)
            if folder_match:
                sample_id = folder_match.group(1)
            
            # Check if we have existing collections for this sample
            collection_files = self.collection_manager.get_collections_for_sample(sample_id)
            
            if collection_files:
                # Load existing collections
                self.current_collections = [
                    self.collection_manager.load_collection(file_path)
                    for file_path in collection_files
                ]
                
                # Update collections menu
                self.update_collections_menu()
                
                # Display the first collection
                if self.current_collections:
                    self.current_collection = self.current_collections[0]
                    self.display_collection(self.current_collection)
            else:
                # No existing collections, analyze the folder to create them
                self.analyze_folder_and_create_collections(folder_path, sample_id)
        except Exception as e:
            self.main_window.show_error("Error", f"Failed to load folder: {str(e)}")
    
    def analyze_folder_and_create_collections(self, folder_path, sample_id):
        """Analyze folder contents and create collections"""
        try:
            # First check if there are TIFF files in the folder
            tiff_files = glob.glob(os.path.join(folder_path, "*.tiff")) + \
                         glob.glob(os.path.join(folder_path, "*.tif"))
            
            if not tiff_files:
                self.main_window.show_message("No Images", f"No TIFF images found in {folder_path}")
                return
            
            # Execute the workflow
            result = self.scale_grid_workflow.execute(
                folder_path=folder_path,
                sample_id=sample_id,
                extract_metadata_func=self.extract_metadata_from_tiff
            )
            
            if result["status"] == "success":
                # Store the collections
                self.current_collections = result["collections"]
                
                # Update collections menu
                self.update_collections_menu()
                
                # Display the first collection
                if self.current_collections:
                    self.current_collection = self.current_collections[0]
                    self.display_collection(self.current_collection)
                    
                self.main_window.show_message(
                    "Collections Created", 
                    f"Created {len(result['collections'])} collections from {folder_path}"
                )
            elif result["status"] == "need_sample_info":
                # We need to get sample information before processing
                self.on_sample_info_button_clicked(result["suggested_sample_id"])
            else:
                # Error occurred
                self.main_window.show_error("Error", result["message"])
                
        except Exception as e:
            self.main_window.show_error("Error", f"Failed to analyze folder: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_collections_menu(self):
        """Update the collections menu with current collections"""
        # Clear existing menu items
        self.collections_menu.clear()
        
        # Create action group for collections (radio button style)
        collection_group = QActionGroup(self.main_window)
        
        # Add each collection to the menu
        for i, collection in enumerate(self.current_collections):
            action = QAction(f"{collection.name} ({len(collection.images)} images)", self.main_window)
            action.setCheckable(True)
            
            # Check the first item by default
            if i == 0:
                action.setChecked(True)
                
            # Connect to handler
            action.triggered.connect(lambda checked, idx=i: self.on_collection_selected(idx))
            
            collection_group.addAction(action)
            self.collections_menu.addAction(action)
    
    def on_collection_selected(self, collection_index):
        """Handle collection selection from menu"""
        if 0 <= collection_index < len(self.current_collections):
            self.current_collection = self.current_collections[collection_index]
            self.display_collection(self.current_collection)
    
    def display_collection(self, collection):
        """Display a collection in the image grid"""
        if not collection:
            return
            
        # Use our enhanced image grid to display the collection
        if isinstance(self.main_window.image_grid, EnhancedImageGridView):
            self.main_window.image_grid.set_images_from_collection(collection)
        else:
            # Fallback for regular image grid
            self.display_collection_in_regular_grid(collection)
            
        self.main_window.setWindowTitle(f"ScaleGrid - {collection.name} - {collection.sample_id}")
    
    def display_collection_in_regular_grid(self, collection):
        """Display a collection in the regular image grid (fallback method)"""
        # Sort images by magnification
        sorted_images = sorted(collection.images, 
                             key=lambda x: collection.metadata[x].get("Mag(pol)", 0))
        
        # Limit to the number of grid cells available
        display_images = sorted_images[:len(self.main_window.image_grid.image_widgets)]
        
        # Prepare image paths and metadata texts
        image_paths = display_images
        metadata_texts = [
            f"Mag: {collection.metadata[img].get('Mag(pol)', 0)}x | {os.path.basename(img)}"
            for img in display_images
        ]
        
        # Set images in grid
        self.main_window.image_grid.set_images(image_paths, metadata_texts)
        
        # Clear any existing bounding boxes
        self.main_window.image_grid.clear_all_bounding_boxes()
        
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
                            self.main_window.image_grid.add_bounding_box(i, bbox, color, tooltip)
                            
                            # Add colored border to child image
                            self.main_window.image_grid.set_border_color(child_idx, color)
    
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
            import traceback
            traceback.print_exc()
            return {}
    
    def on_sample_info_button_clicked(self, suggested_sample_id=""):
        """Handle sample info button click"""
        from view_dialogs import SampleInfoDialog
        dialog = SampleInfoDialog(self.main_window, suggested_sample_id)
        if dialog.exec_():
            # Get sample info from dialog
            sample_info = dialog.get_sample_info()
            
            # Process the folder now that we have sample info
            if self.current_folder:
                self.analyze_folder_and_create_collections(
                    self.current_folder, 
                    sample_info["sample_id"]
                )
    
    def on_export_button_clicked(self):
        """Handle export button click"""
        if not self.current_folder or not self.current_collection:
            self.main_window.show_error("Error", "No collection loaded")
            return
            
        # Get sample name from metadata or folder
        sample_id = self.current_collection.sample_id
        collection_name = self.current_collection.name
        folder_name = os.path.basename(self.current_folder)
        
        # Find the next available grid number
        grid_number = 1
        while True:
            filename = f"{sample_id}_{collection_name}_Grid-{grid_number}.png"
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
                    self.display_next_collection()
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
    
    def display_next_collection(self):
        """Display the next collection in the list"""
        if not self.current_collections or not self.current_collection:
            return
            
        # Find the current collection index
        current_idx = self.current_collections.index(self.current_collection)
        next_idx = (current_idx + 1) % len(self.current_collections)
        
        # Display the next collection
        self.current_collection = self.current_collections[next_idx]
        self.display_collection(self.current_collection)
        
        # Update the checked state in the collections menu
        actions = self.collections_menu.actions()
        if 0 <= next_idx < len(actions):
            actions[next_idx].setChecked(True)