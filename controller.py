import os
import sys
import glob
import re
from typing import Dict, List, Optional
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QAction, QActionGroup
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from main_window import MainWindow
from sample_dialog import SampleInfoDialog
from metadata import MetadataManager
from collections import CollectionManager, ImageCollection

class ScaleGridController:
    """Main controller for the ScaleGrid application"""
    
    def __init__(self):
        # Initialize managers
        self.metadata_manager = MetadataManager()
        self.collection_manager = CollectionManager()
        
        # Initialize main window
        self.main_window = MainWindow()
        
        # Current application state
        self.current_folder = None
        self.current_session_id = None
        self.current_sample_id = None
        self.current_collections = []
        self.current_collection = None
        self.image_metadata = {}
        
        # Connect signals
        self.connect_signals()
    
    def connect_signals(self):
        """Connect UI signals to controller methods"""
        # Connect main window signals
        self.main_window.folder_button.clicked.connect(self.on_folder_button_clicked)
        self.main_window.sample_info_button.clicked.connect(self.on_sample_info_button_clicked)
        self.main_window.image_grid.export_button.clicked.connect(self.on_export_button_clicked)
        
        # Connect menu actions
        for action in self.main_window.menuBar().findChildren(QAction):
            if action.text() == "Open Folder...":
                action.triggered.connect(self.on_folder_button_clicked)
            elif action.text() == "Export Grid...":
                action.triggered.connect(self.on_export_button_clicked)
        
        # Connect grid size actions
        view_menu = self.main_window.menuBar().findChild(QAction, "View").menu()
        if view_menu:
            grid_size_menu = view_menu.findChild(QAction, "Grid Size").menu()
            if grid_size_menu:
                for action in grid_size_menu.actions():
                    size_text = action.text()
                    action.triggered.connect(lambda _, s=size_text: self.set_grid_size(s))
    
    def run(self):
        """Start the application"""
        self.main_window.show()
    
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
            
            # Extract session ID from folder name (SEM1-###)
            folder_name = os.path.basename(folder_path)
            session_match = re.search(r'(SEM\d+-\d+|EDX\d+-\d+)', folder_name)
            
            if session_match:
                session_id = session_match.group(1)
            else:
                # If no match, use the folder name as session ID
                session_id = folder_name
            
            self.current_session_id = session_id
            
            # Check if we have existing session info
            existing_info = self.metadata_manager.load_session_info(session_id)
            
            if existing_info:
                # Ask user if they want to use existing info
                use_existing = self.main_window.show_question(
                    "Use Existing Information",
                    f"Found existing information for session {session_id}.\n"
                    f"Sample ID: {existing_info.get('sample_id', 'Unknown')}\n"
                    f"Do you want to use this information?"
                )
                
                if use_existing:
                    # Use existing info and proceed with analysis
                    self.current_sample_id = existing_info.get("sample_id")
                    self.process_folder_with_info(session_id, existing_info)
                else:
                    # Edit existing info
                    self.show_sample_info_dialog(session_id, existing_info)
            else:
                # No existing info, show dialog to collect it
                self.show_sample_info_dialog(session_id)
            
        except Exception as e:
            self.main_window.show_error("Error", f"Failed to load folder: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def show_sample_info_dialog(self, session_id, existing_info=None):
        """Show dialog to collect sample information"""
        dialog = SampleInfoDialog(self.main_window, session_id, existing_info)
        if dialog.exec_():
            # Get sample info from dialog
            sample_info = dialog.get_sample_info()
            
            # Store the current sample ID
            self.current_sample_id = sample_info["sample_id"]
            
            # Process the folder with the sample info
            self.process_folder_with_info(session_id, sample_info)
    
    def process_folder_with_info(self, session_id, sample_info):
        """Process a folder with provided sample information"""
        try:
            # Save the sample information
            self.metadata_manager.save_session_info(sample_info)
            
            # Check if we have existing metadata for these images
            use_existing_metadata = False
            if self.metadata_manager.check_if_metadata_exists(session_id):
                use_existing_metadata = self.main_window.show_question(
                    "Use Existing Metadata",
                    f"Found existing metadata for session {session_id}.\n"
                    f"Do you want to use it instead of re-analyzing the images?"
                )
                
                if use_existing_metadata:
                    # Load existing metadata from CSV
                    self.image_metadata = self.metadata_manager.load_images_metadata_from_csv(session_id)
                    
                    # Verify that all files still exist
                    missing_files = []
                    for image_path in list(self.image_metadata.keys()):
                        if not os.path.exists(image_path):
                            missing_files.append(image_path)
                            del self.image_metadata[image_path]
                    
                    if missing_files:
                        self.main_window.show_message(
                            "Missing Files",
                            f"{len(missing_files)} files referenced in metadata no longer exist."
                        )
                    
                    if not self.image_metadata:
                        # All files are missing, need to extract metadata again
                        use_existing_metadata = False
            
            if not use_existing_metadata:
                # Find all TIFF files in the folder
                self.main_window.set_status("Finding TIFF files...")
                tiff_files = glob.glob(os.path.join(self.current_folder, "*.tiff")) + \
                             glob.glob(os.path.join(self.current_folder, "*.tif"))
                
                if not tiff_files:
                    self.main_window.show_error("No Images", f"No TIFF images found in {self.current_folder}")
                    return
                
                # Extract metadata from all files
                self.main_window.set_status(f"Extracting metadata from {len(tiff_files)} files...")
                self.image_metadata = {}
                
                for i, tiff_file in enumerate(tiff_files):
                    try:
                        # Update status periodically
                        if i % 5 == 0:
                            self.main_window.set_status(f"Processing image {i+1} of {len(tiff_files)}...")
                        
                        metadata = self.metadata_manager.extract_metadata_from_tiff(tiff_file)
                        if metadata:
                            self.image_metadata[tiff_file] = metadata
                    except Exception as e:
                        print(f"Error extracting metadata from {tiff_file}: {e}")
                
                # Save the metadata to CSV
                if self.image_metadata:
                    self.metadata_manager.save_images_metadata_to_csv(session_id, self.image_metadata)
            
            # Check if we have any valid metadata
            if not self.image_metadata:
                self.main_window.show_error("Error", "No valid image metadata found")
                return
            
            # Analyze images and create collections
            self.main_window.set_status("Analyzing image relationships...")
            self.current_collections = self.collection_manager.analyze_images(
                self.current_folder,
                session_id,
                sample_info["sample_id"],
                self.image_metadata
            )
            
            if not self.current_collections:
                self.main_window.show_error("Error", "No valid image collections created")
                return
            
            # Save collections
            self.main_window.set_status("Saving image collections...")
            for collection in self.current_collections:
                self.collection_manager.save_collection(collection)
            
            # Update collections menu
            self.update_collections_menu()
            
            # Display the first collection
            if self.current_collections:
                self.main_window.set_status(f"Created {len(self.current_collections)} collections")
                self.current_collection = self.current_collections[0]
                self.display_collection(self.current_collection)
        
        except Exception as e:
            self.main_window.show_error("Error", f"Failed to process folder: {str(e)}")
            import traceback
            traceback.print_exc()
            self.main_window.clear_status()
    
    def update_collections_menu(self):
        """Update the collections menu with current collections"""
        # Clear existing menu items
        self.main_window.collections_menu.clear()
        
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
            self.main_window.collections_menu.addAction(action)
    
    def on_collection_selected(self, collection_index):
        """Handle collection selection from menu"""
        if 0 <= collection_index < len(self.current_collections):
            self.current_collection = self.current_collections[collection_index]
            self.display_collection(self.current_collection)
    
    def display_collection(self, collection):
        """Display a collection in the image grid"""
        if not collection:
            return
            
        # Use our image grid to display the collection
        self.main_window.image_grid.set_images_from_collection(collection)
        
        # Update window title
        self.main_window.setWindowTitle(
            f"ScaleGrid - {collection.name} - Session: {collection.session_id} - Sample: {collection.sample_id}"
        )
    
    def on_sample_info_button_clicked(self):
        """Handle sample info button click"""
        if not self.current_session_id:
            self.main_window.show_error("Error", "No folder loaded")
            return
        
        # Check if we have existing sample info
        existing_info = self.metadata_manager.load_session_info(self.current_session_id)
        
        # Show the sample info dialog
        self.show_sample_info_dialog(self.current_session_id, existing_info)
    
    def on_export_button_clicked(self):
        """Handle export button click"""
        if not self.current_folder or not self.current_collection:
            self.main_window.show_error("Error", "No collection loaded")
            return
            
        # Get sample name and collection name
        session_id = self.current_collection.session_id
        sample_id = self.current_collection.sample_id
        collection_name = self.current_collection.name
        
        # Find the next available grid number
        grid_number = 1
        while True:
            filename = f"{session_id}_{sample_id}_{collection_name}_Grid-{grid_number}.png"
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
            self.main_window.set_status("Exporting grid image...")
            success = self.main_window.image_grid.export_grid(file_path)
            
            if success:
                self.main_window.set_status(f"Grid exported to {file_path}")
                # Ask what to do next
                response = QMessageBox.question(
                    self.main_window,
                    "Export Complete",
                    f"Grid exported to {file_path}\n\nWhat would you like to do next?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes
                )
                
                if response == QMessageBox.Yes:  # "Next Collection"
                    # Display the next collection
                    self.display_next_collection()
                elif response == QMessageBox.No:  # "New Folder"
                    # Prompt for a new folder
                    self.on_folder_button_clicked()
                # QMessageBox.Cancel just returns to the current view
            else:
                self.main_window.show_error(
                    "Export Failed", 
                    "Failed to export grid"
                )
                self.main_window.clear_status()
    
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
        actions = self.main_window.collections_menu.actions()
        if 0 <= next_idx < len(actions):
            actions[next_idx].setChecked(True)
    
    def set_grid_size(self, size_text):
        """Set the grid size based on the selected menu option"""
        sizes = {"1x1": 0, "2x2": 1, "3x3": 2, "4x4": 3}
        if size_text in sizes:
            self.main_window.image_grid.grid_size_combo.setCurrentIndex(sizes[size_text])
