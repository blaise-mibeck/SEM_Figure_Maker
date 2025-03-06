import os
import sys
import threading
from typing import Dict, List, Optional, Tuple
from PyQt5.QtWidgets import (QFileDialog, QApplication, QMainWindow, QInputDialog, 
                            QMessageBox, QAction, QMenu, QActionGroup)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QObject

# Import model classes
from model_classes import (
    ImageMetadata, Sample, PhenomAPI, MagnificationAnalyzer, 
    DataRepository, ImageProcessor
)

# Import workflow classes
from workflow_classes import (
    Workflow, ScaleGridWorkflow, CompareGridWorkflow, QualityAssessmentWorkflow,
    WorkflowType, ImageQualityMetrics
)

# Import view classes
from view_classes import ImageGridView
from view_dialogs import SampleInfoDialog, ExportDialog, MainWindow

# Import workflow controller
from workflow_controller import WorkflowController, WorkflowInputDialog

# Create a signal handler for background tasks
class SignalHandler(QObject):
    task_completed = pyqtSignal(bool, str)  # Success status, message
    progress_updated = pyqtSignal(int, str)  # Progress percentage, message
    workflow_result = pyqtSignal(bool, object)  # Success status, result object


class EnhancedApplicationController:
    """Enhanced main controller for the ScaleGrid application with workflow support"""
    
    def __init__(self):
        # Initialize signal handler for background tasks
        self.signal_handler = SignalHandler()
        
        # Initialize model components
        self.phenom_api = PhenomAPI()
        self.data_repo = DataRepository()
        self.image_processor = ImageProcessor(self.phenom_api)
        
        # Initialize workflow controller
        self.workflow_controller = WorkflowController(self)
        
        # Current application state
        self.current_folder = None
        self.current_sample = None
        self.current_images = []
        self.is_phenom_connected = False
        self.current_workflow_type = WorkflowType.SCALE_GRID
        
        # Initialize view
        self.main_window = self._create_main_window()
        
        # Connect signals to handlers
        self.connect_signals()
        
        # Connect to Phenom if available
        self.connect_to_phenom()
    
    def _create_main_window(self):
        """Create and setup the main window with workflow menus"""
        main_window = MainWindow()
        
        # Create workflow menu
        workflow_menu = main_window.menuBar().addMenu("Workflows")
        
        # Create action group for workflows (radio-button style menu)
        workflow_group = QActionGroup(main_window)
        
        # Add each workflow to the menu
        workflow_actions = {}
        
        # Scale Grid workflow
        scale_grid_action = QAction("Scale Grid", main_window, checkable=True)
        scale_grid_action.setChecked(True)  # Default workflow
        scale_grid_action.triggered.connect(lambda: self.select_workflow(WorkflowType.SCALE_GRID))
        workflow_group.addAction(scale_grid_action)
        workflow_menu.addAction(scale_grid_action)
        workflow_actions[WorkflowType.SCALE_GRID] = scale_grid_action
        
        # Compare Grid workflow
        compare_grid_action = QAction("Compare Grid", main_window, checkable=True)
        compare_grid_action.triggered.connect(lambda: self.select_workflow(WorkflowType.COMPARE_GRID))
        workflow_group.addAction(compare_grid_action)
        workflow_menu.addAction(compare_grid_action)
        workflow_actions[WorkflowType.COMPARE_GRID] = compare_grid_action
        
        # Quality Assessment workflow
        quality_action = QAction("Quality Assessment", main_window, checkable=True)
        quality_action.triggered.connect(lambda: self.select_workflow(WorkflowType.QUALITY_ASSESSMENT))
        workflow_group.addAction(quality_action)
        workflow_menu.addAction(quality_action)
        workflow_actions[WorkflowType.QUALITY_ASSESSMENT] = quality_action
        
        # Store workflow actions for later reference
        main_window.workflow_actions = workflow_actions
        
        # Add separator and Run Workflow action
        workflow_menu.addSeparator()
        run_workflow_action = QAction("Run Workflow...", main_window)
        run_workflow_action.triggered.connect(self.run_current_workflow)
        workflow_menu.addAction(run_workflow_action)
        
        # Store RunWorkflow action for reference
        main_window.run_workflow_action = run_workflow_action
        
        return main_window
    
    def connect_signals(self):
        """Connect UI signals to controller methods"""
        # Connect folder selection button
        self.main_window.folder_button.clicked.connect(self.on_folder_button_clicked)
        
        # Connect sample info button
        self.main_window.sample_info_button.clicked.connect(self.on_sample_info_button_clicked)
        
        # Connect export button
        self.main_window.image_grid.export_button.clicked.connect(self.on_export_button_clicked)
        
        # Connect box drawing signal
        for i, widget in enumerate(self.main_window.image_grid.image_widgets):
            widget.boxDrawn.connect(lambda rect, idx=i: self.on_box_drawn(rect, idx))
        
        # Connect background task signals
        self.signal_handler.task_completed.connect(self.on_task_completed)
        self.signal_handler.progress_updated.connect(self.on_progress_updated)
        self.signal_handler.workflow_result.connect(self.on_workflow_result)
    
    def select_workflow(self, workflow_type: WorkflowType):
        """Select a workflow to use"""
        self.current_workflow_type = workflow_type
        
        # Update UI to reflect the selected workflow
        workflow = self.workflow_controller.select_workflow(workflow_type)
        self.main_window.setWindowTitle(f"ScaleGrid - {workflow.name}")
        
        # Show a hint about the workflow
        self.main_window.statusBar().showMessage(f"Selected workflow: {workflow.description}")
    
    def run_current_workflow(self):
        """Run the currently selected workflow"""
        workflow = self.workflow_controller.get_workflow(self.current_workflow_type)
        
        # Show input dialog for the workflow
        input_dialog = WorkflowInputDialog(self.main_window, workflow)
        if input_dialog.exec_():
            # Get inputs from dialog
            inputs = input_dialog.get_inputs()
            
            # Check for required inputs
            if self.current_workflow_type == WorkflowType.SCALE_GRID:
                if not inputs.get('folder_path'):
                    self.main_window.show_error("Missing Input", "Please select a folder.")
                    return
            elif self.current_workflow_type == WorkflowType.COMPARE_GRID:
                if not inputs.get('folder_paths') or len(inputs.get('folder_paths', [])) < 2:
                    self.main_window.show_error("Missing Input", "Please select at least two folders.")
                    return
            elif self.current_workflow_type == WorkflowType.QUALITY_ASSESSMENT:
                if not inputs.get('folder_path'):
                    self.main_window.show_error("Missing Input", "Please select a folder.")
                    return
            
            # Run workflow asynchronously
            self.main_window.statusBar().showMessage(f"Running {workflow.name} workflow...")
            
            def callback(success: bool, result: object):
                # Use signal to update UI from main thread
                self.signal_handler.workflow_result.emit(success, result)
            
            # Execute workflow with provided inputs
            self.workflow_controller.execute_workflow_async(
                self.current_workflow_type, 
                callback, 
                **inputs
            )
    
    def on_workflow_result(self, success: bool, result: object):
        """Handle workflow result"""
        if not success:
            self.main_window.show_error("Workflow Failed", str(result))
            return
        
        # Check if we need to process a folder first
        if isinstance(result, dict) and result.get('status') == 'need_processing':
            self.current_folder = result.get('folder_path')
            self.on_sample_info_button_clicked(os.path.basename(result.get('folder_path')))
            return
        
        # Handle successful result based on workflow type
        if self.current_workflow_type == WorkflowType.SCALE_GRID:
            self._handle_scale_grid_result(result)
        elif self.current_workflow_type == WorkflowType.COMPARE_GRID:
            self._handle_compare_grid_result(result)
        elif self.current_workflow_type == WorkflowType.QUALITY_ASSESSMENT:
            self._handle_quality_assessment_result(result)
    
    def _handle_scale_grid_result(self, result: Dict):
        """Handle result from ScaleGrid workflow"""
        if result.get('status') != 'success':
            self.main_window.show_error("Workflow Failed", result.get('message', 'Unknown error'))
            return
        
        # Update current state
        self.current_sample = result.get('sample')
        self.current_images = result.get('images')
        
        # Update image grid with sorted images
        self.update_image_grid()
        
        # Add bounding boxes based on containment map
        containment_map = result.get('containment_map', {})
        for parent_idx, child_indices in containment_map.items():
            for child_idx in child_indices:
                if parent_idx < len(self.main_window.image_grid.image_widgets) and child_idx < len(self.current_images):
                    # Calculate bounding box
                    parent_img = self.current_images[parent_idx]
                    child_img = self.current_images[child_idx]
                    box = self.image_processor.mag_analyzer.calculate_bounding_box(parent_img, child_img)
                    
                    # Add box to parent image
                    self.main_window.image_grid.add_bounding_box(parent_idx, box, QColor(255, 0, 0, 128))
        
        self.main_window.show_message("Workflow Complete", f"Successfully processed {len(self.current_images)} images")
    
    def _handle_compare_grid_result(self, result: Dict):
        """Handle result from CompareGrid workflow"""
        if result.get('status') != 'success':
            self.main_window.show_error("Workflow Failed", result.get('message', 'Unknown error'))
            return
        
        # Get matched images
        samples = result.get('samples', [])
        matched_images = result.get('matched_images', [])
        magnification = result.get('magnification')
        
        if not matched_images:
            self.main_window.show_error("No Matches", "No matching images found across samples")
            return
        
        # Clear the grid
        self.main_window.image_grid.clear_all()
        
        # Determine grid size based on number of images
        grid_size = 2  # Default to 2x2
        if len(matched_images) <= 4:
            grid_size = 2
        elif len(matched_images) <= 9:
            grid_size = 3
        elif len(matched_images) <= 16:
            grid_size = 4
        
        # Resize grid if needed
        if grid_size != self.main_window.image_grid.rows:
            self.main_window.image_grid.grid_size_combo.setCurrentIndex(grid_size - 1)
            self.main_window.image_grid.on_grid_size_changed(grid_size - 1)
        
        # Prepare image paths and metadata texts
        image_paths = []
        metadata_texts = []
        
        for sample_idx, image in matched_images:
            if sample_idx < len(samples):
                sample = samples[sample_idx]
                image_paths.append(image.image_path)
                metadata_texts.append(f"{sample.sample_id}: {image.magnification}x | {os.path.basename(image.image_path)}")
        
        # Set images in grid
        self.main_window.image_grid.set_images(image_paths, metadata_texts)
        
        self.main_window.show_message("Workflow Complete", f"Displaying {len(matched_images)} matching images at ~{magnification}x magnification")
    
    def _handle_quality_assessment_result(self, result: Dict):
        """Handle result from QualityAssessment workflow"""
        if result.get('status') != 'success':
            self.main_window.show_error("Workflow Failed", result.get('message', 'Unknown error'))
            return
        
        # Get quality scores
        sample = result.get('sample')
        quality_scores = result.get('quality_scores', [])
        
        if not quality_scores:
            self.main_window.show_error("No Images", "No images found to assess")
            return
        
        # Clear the grid
        self.main_window.image_grid.clear_all()
        
        # Determine grid size based on number of images
        grid_size = 2  # Default to 2x2
        if len(quality_scores) <= 4:
            grid_size = 2
        elif len(quality_scores) <= 9:
            grid_size = 3
        elif len(quality_scores) <= 16:
            grid_size = 4
        
        # Resize grid if needed
        if grid_size != self.main_window.image_grid.rows:
            self.main_window.image_grid.grid_size_combo.setCurrentIndex(grid_size - 1)
            self.main_window.image_grid.on_grid_size_changed(grid_size - 1)
        
        # Prepare image paths and metadata texts
        image_paths = []
        metadata_texts = []
        
        for image, score in quality_scores[:self.main_window.image_grid.rows * self.main_window.image_grid.cols]:
            image_paths.append(image.image_path)
            metadata_texts.append(f"Quality: {score:.2f} | {image.magnification}x | {os.path.basename(image.image_path)}")
        
        # Set images in grid
        self.main_window.image_grid.set_images(image_paths, metadata_texts)
        
        self.main_window.show_message("Workflow Complete", f"Displaying {len(image_paths)} images sorted by quality")
    
    def run(self):
        """Start the application"""
        self.main_window.show()
        
    def connect_to_phenom(self):
        """Connect to Phenom microscope if available"""
        try:
            # Check if we can find any Phenoms on the network
            self.main_window.statusBar().showMessage("Searching for Phenom microscopes...")
            
            # Run in a separate thread to not block UI
            def connect_thread():
                try:
                    # Try to connect to the Phenom
                    self.is_phenom_connected = self.phenom_api.connect()
                    self.signal_handler.task_completed.emit(
                        self.is_phenom_connected, 
                        "Connected to Phenom" if self.is_phenom_connected else "Using simulation mode"
                    )
                except Exception as e:
                    self.signal_handler.task_completed.emit(False, f"Error connecting to Phenom: {str(e)}")
            
            # Start the connection thread
            threading.Thread(target=connect_thread, daemon=True).start()
            
        except Exception as e:
            self.main_window.show_error("Connection Error", f"Failed to connect to Phenom: {str(e)}")
    
    def on_task_completed(self, success: bool, message: str):
        """Handle completion of background tasks"""
        if success:
            self.main_window.statusBar().showMessage(message)
        else:
            self.main_window.statusBar().showMessage(f"Error: {message}")
            self.main_window.show_error("Task Failed", message)
    
    def on_progress_updated(self, percentage: int, message: str):
        """Handle progress updates from background tasks"""
        # Update status bar
        self.main_window.statusBar().showMessage(f"{message} ({percentage}%)")
    
    def on_folder_button_clicked(self):
        """Handle folder selection button click"""
        folder_path = QFileDialog.getExistingDirectory(
            self.main_window, "Select SEM Images Folder")
        
        if folder_path:
            self.load_folder(folder_path)
    
    def load_folder(self, folder_path: str):
        """Load images from a folder and process them"""
        try:
            self.current_folder = folder_path
            self.main_window.update_folder_path(folder_path)
            
            # Check if the folder name matches expected pattern
            folder_name = os.path.basename(folder_path)
            is_new_sample = True
            
            # Check if we already have this sample in our repository
            for sample_id in self.data_repo.get_all_sample_ids():
                if folder_name.startswith(sample_id):
                    # Found existing sample
                    self.current_sample = self.data_repo.load_sample(sample_id)
                    is_new_sample = False
                    break
            
            if is_new_sample:
                # Ask for sample information
                self.on_sample_info_button_clicked(folder_name)
            else:
                # Process the folder with existing sample info
                self.process_current_folder()
        except Exception as e:
            self.main_window.show_error("Error", f"Failed to load folder: {str(e)}")
    
    def on_sample_info_button_clicked(self, folder_name: str = ""):
        """Handle sample info button click"""
        dialog = SampleInfoDialog(self.main_window, folder_name or os.path.basename(self.current_folder or ""))
        if dialog.exec_():
            # Get sample info from dialog
            sample_info = dialog.get_sample_info()
            
            # Create a new sample if we don't have one already
            if not self.current_sample:
                self.current_sample = Sample(
                    sample_id=sample_info["sample_id"],
                    preparation_method=sample_info["preparation_method"],
                    notes=sample_info["notes"]
                )
            else:
                # Update existing sample info
                self.current_sample.sample_id = sample_info["sample_id"]
                self.current_sample.preparation_method = sample_info["preparation_method"]
                self.current_sample.notes = sample_info["notes"]
            
            # Process the folder now that we have sample info
            if self.current_folder:
                self.process_current_folder()
    
    def process_current_folder(self):
        """Process the current folder to extract and analyze images"""
        if not self.current_folder or not self.current_sample:
            return
        
        # Run processing in a background thread to prevent UI freezing
        def process_thread():
            try:
                # Update progress
                self.signal_handler.progress_updated.emit(0, "Starting folder processing")
                
                # Clear existing images
                self.current_images = []
                
                # Process folder to extract image metadata
                self.signal_handler.progress_updated.emit(10, "Extracting image metadata")
                image_metadatas = self.image_processor.process_folder(self.current_folder)
                
                # Update progress
                self.signal_handler.progress_updated.emit(50, f"Processing {len(image_metadatas)} images")
                
                # Add images to sample
                for i, metadata in enumerate(image_metadatas):
                    # Check if this image is already in the sample
                    existing = False
                    for img in self.current_sample.images:
                        if os.path.samefile(img.image_path, metadata.image_path):
                            existing = True
                            break
                    
                    if not existing:
                        self.current_sample.add_image(metadata)
                    
                    # Update progress periodically
                    if len(image_metadatas) > 0:
                        progress = 50 + int(40 * (i / len(image_metadatas)))
                        self.signal_handler.progress_updated.emit(
                            progress, 
                            f"Processing image {i+1} of {len(image_metadatas)}"
                        )
                
                # Save the sample to repository
                self.signal_handler.progress_updated.emit(90, "Saving sample data")
                self.data_repo.save_sample(self.current_sample)
                
                # Update current images
                self.current_images = self.current_sample.images
                
                # Signal completion to update the UI from the main thread
                self.signal_handler.task_completed.emit(
                    True, 
                    f"Processed {len(image_metadatas)} images from folder {self.current_folder}"
                )
                
                # Request UI update (needs to be done in main thread)
                # We use a signal to ensure this runs in the main thread
                self.signal_handler.progress_updated.emit(100, "Updating display")
                
                # We need to use invoke_later to update the UI from the main thread
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, self.update_image_grid)
                
            except Exception as e:
                self.signal_handler.task_completed.emit(
                    False, 
                    f"Failed to process folder: {str(e)}"
                )
        
        # Start processing thread
        threading.Thread(target=process_thread, daemon=True).start()
    
    def update_image_grid(self):
        """Update the image grid with current images"""
        if not self.current_images:
            return
        
        # Sort images by magnification
        sorted_images = sorted(self.current_images, key=lambda x: x.magnification)
        
        # Limit to the number of grid cells available
        max_images = len(self.main_window.image_grid.image_widgets)
        display_images = sorted_images[:max_images]
        
        # Prepare image paths and metadata texts
        image_paths = [img.image_path for img in display_images]
        metadata_texts = [
            f"Mag: {img.magnification}x | {os.path.basename(img.image_path)}"
            for img in display_images
        ]
        
        # Set images in grid
        self.main_window.image_grid.set_images(image_paths, metadata_texts)
        
        # Clear any existing bounding boxes
        self.main_window.image_grid.clear_all_bounding_boxes()
        
        # Add bounding boxes to show magnification relationships
        self.update_bounding_boxes(display_images)
    
    def update_bounding_boxes(self, display_images: List[ImageMetadata]):
        """Update bounding boxes showing magnification relationships"""
        # Get magnification analyzer
        mag_analyzer = MagnificationAnalyzer()
        
        # For each pair of images, calculate and display bounding box if applicable
        for i, img in enumerate(display_images):
            # Find images that this image contains
            for contained_img in img.contains:
                # Find the index of contained_img in display_images
                for j, display_img in enumerate(display_images):
                    if display_img.image_path == contained_img.image_path:
                        # Calculate bounding box
                        box = mag_analyzer.calculate_bounding_box(img, contained_img)
                        
                        # Add box to the parent image widget
                        self.main_window.image_grid.add_bounding_box(i, box, QColor(255, 0, 0, 128))
    
    def on_box_drawn(self, rect: QRectF, widget_index: int):
        """Handle box drawn on an image widget"""
        if not self.current_images or widget_index >= len(self.current_images):
            return
        
        # For now, just show a message with the drawn box coordinates
        self.main_window.statusBar().showMessage(
            f"Box drawn on image {widget_index} at {rect.x():.2f}, {rect.y():.2f}, {rect.width():.2f}, {rect.height():.2f}"
        )
    
    def on_export_button_clicked(self):
        """Handle export button click"""
        dialog = ExportDialog(self.main_window)
        if dialog.exec_():
            export_options = dialog.get_export_options()
            
            if not export_options["file_path"]:
                self.main_window.show_error("Error", "No output file specified")
                return
            
            # Export the grid
            success = self.main_window.image_grid.export_grid(export_options["file_path"])
            
            if success:
                self.main_window.show_message(
                    "Export Complete", 
                    f"Grid exported to {export_options['file_path']}"
                )
            else:
                self.main_window.show_error(
                    "Export Failed", 
                    "Failed to export grid"
                )
