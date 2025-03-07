import os
import sys
import threading
from typing import Dict, List, Optional, Any
from PyQt5.QtWidgets import (QFileDialog, QApplication, QMainWindow, QInputDialog, 
                            QMessageBox, QDialog, QVBoxLayout, QListWidget, 
                            QPushButton, QLabel, QComboBox, QHBoxLayout, QWidget)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QObject

from workflow_classes import (
    Workflow, ScaleGridWorkflow, CompareGridWorkflow, QualityAssessmentWorkflow,
    WorkflowType, ImageQualityMetrics
)
from model_classes import (
    ImageMetadata, Sample, PhenomAPI, MagnificationAnalyzer, 
    DataRepository, ImageProcessor
)

class WorkflowController:
    """Controller for managing different workflows"""
    
    def __init__(self, application_controller):
        """Initialize workflow controller with reference to main controller"""
        self.app_controller = application_controller
        
        # Initialize available workflows
        self.workflows = {
            WorkflowType.SCALE_GRID: ScaleGridWorkflow(self.app_controller.data_repo),
            WorkflowType.COMPARE_GRID: CompareGridWorkflow(self.app_controller.data_repo),
            WorkflowType.QUALITY_ASSESSMENT: QualityAssessmentWorkflow(self.app_controller.data_repo)
        }
        
        # Current workflow state
        self.current_workflow = None
        self.workflow_result = None
    
    def select_workflow(self, workflow_type: WorkflowType):
        """Select a workflow to execute"""
        self.current_workflow = self.workflows[workflow_type]
        return self.current_workflow
    
    def get_workflow(self, workflow_type: WorkflowType) -> Workflow:
        """Get a workflow by type"""
        return self.workflows[workflow_type]
    
    def get_available_workflows(self) -> List[Workflow]:
        """Get list of all available workflows"""
        return list(self.workflows.values())
    
    def execute_workflow(self, workflow_type: WorkflowType, **kwargs) -> Dict:
        """Execute a specific workflow with provided parameters"""
        workflow = self.workflows[workflow_type]
        
        # Check if all required inputs are provided
        required_inputs = workflow.get_required_inputs()
        for input_name in required_inputs:
            if input_name not in kwargs:
                raise ValueError(f"Missing required input: {input_name}")
        
        # Execute workflow
        self.workflow_result = workflow.execute(**kwargs)
        return self.workflow_result
    
    def execute_workflow_async(self, workflow_type: WorkflowType, callback, **kwargs):
        """Execute a workflow asynchronously in a background thread"""
        workflow = self.workflows[workflow_type]
        
        # Check if all required inputs are provided
        required_inputs = workflow.get_required_inputs()
        for input_name in required_inputs:
            if input_name not in kwargs:
                raise ValueError(f"Missing required input: {input_name}")
        
        # Create thread function
        def thread_func():
            try:
                # Execute workflow
                result = workflow.execute(**kwargs)
                # Call callback with result
                callback(True, result)
            except Exception as e:
                # Call callback with error
                callback(False, str(e))
        
        # Start thread
        threading.Thread(target=thread_func, daemon=True).start()


class WorkflowInputDialog(QDialog):
    """Dialog for collecting workflow input parameters"""
    
    def __init__(self, parent, workflow: Workflow):
        super().__init__(parent)
        self.workflow = workflow
        self.inputs = {}
        self.input_widgets = {}
        
        self.setWindowTitle(f"{workflow.name} - Input Parameters")
        self.resize(500, 300)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add description
        description_label = QLabel(workflow.description)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        
        # Add required inputs based on workflow type
        if isinstance(workflow, ScaleGridWorkflow):
            self._setup_scale_grid_inputs(layout)
        elif isinstance(workflow, CompareGridWorkflow):
            self._setup_compare_grid_inputs(layout)
        elif isinstance(workflow, QualityAssessmentWorkflow):
            self._setup_quality_assessment_inputs(layout)
        
        # Add buttons
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        run_button = QPushButton("Run Workflow")
        run_button.clicked.connect(self.accept)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(run_button)
        
        layout.addLayout(button_layout)
    
    def _setup_scale_grid_inputs(self, layout):
        """Setup inputs for ScaleGrid workflow"""
        # Folder selection
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Folder:"))
        self.input_widgets['folder_path'] = QLabel("No folder selected")
        folder_layout.addWidget(self.input_widgets['folder_path'])
        folder_button = QPushButton("Browse...")
        folder_button.clicked.connect(self._browse_folder)
        folder_layout.addWidget(folder_button)
        layout.addLayout(folder_layout)
    
    def _setup_compare_grid_inputs(self, layout):
        """Setup inputs for CompareGrid workflow"""
        # Folders selection
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Folders:"))
        self.folders_list = QListWidget()
        self.input_widgets['folder_paths'] = self.folders_list
        folder_layout.addWidget(self.folders_list)
        
        folder_buttons = QVBoxLayout()
        add_folder_button = QPushButton("Add Folder...")
        add_folder_button.clicked.connect(self._add_folder)
        remove_folder_button = QPushButton("Remove Selected")
        remove_folder_button.clicked.connect(self._remove_folder)
        folder_buttons.addWidget(add_folder_button)
        folder_buttons.addWidget(remove_folder_button)
        folder_layout.addLayout(folder_buttons)
        
        layout.addLayout(folder_layout)
        
        # Magnification target
        mag_layout = QHBoxLayout()
        mag_layout.addWidget(QLabel("Target Magnification:"))
        self.input_widgets['magnification_target'] = QComboBox()
        self.input_widgets['magnification_target'].addItem("Auto-detect", None)
        for mag in [500, 1000, 2500, 5000, 10000, 20000]:
            self.input_widgets['magnification_target'].addItem(f"{mag}x", mag)
        mag_layout.addWidget(self.input_widgets['magnification_target'])
        layout.addLayout(mag_layout)
        
        # Tolerance
        tolerance_layout = QHBoxLayout()
        tolerance_layout.addWidget(QLabel("Tolerance (%):"))
        self.input_widgets['tolerance_percent'] = QComboBox()
        for tol in [5, 10, 20, 30, 50]:
            self.input_widgets['tolerance_percent'].addItem(f"{tol}%", tol)
        self.input_widgets['tolerance_percent'].setCurrentIndex(2)  # Default to 20%
        tolerance_layout.addWidget(self.input_widgets['tolerance_percent'])
        layout.addLayout(tolerance_layout)
        
        # Detector type
        detector_layout = QHBoxLayout()
        detector_layout.addWidget(QLabel("Detector Type:"))
        self.input_widgets['detector_type'] = QComboBox()
        self.input_widgets['detector_type'].addItem("Any", None)
        self.input_widgets['detector_type'].addItem("BSD", "BSD")
        self.input_widgets['detector_type'].addItem("SED", "SED")
        detector_layout.addWidget(self.input_widgets['detector_type'])
        layout.addLayout(detector_layout)
    
    def _setup_quality_assessment_inputs(self, layout):
        """Setup inputs for QualityAssessment workflow"""
        # Folder selection
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Folder:"))
        self.input_widgets['folder_path'] = QLabel("No folder selected")
        folder_layout.addWidget(self.input_widgets['folder_path'])
        folder_button = QPushButton("Browse...")
        folder_button.clicked.connect(self._browse_folder)
        folder_layout.addWidget(folder_button)
        layout.addLayout(folder_layout)
        
        # Metric weights
        weights_label = QLabel("Metric Weights:")
        layout.addWidget(weights_label)
        
        # Blur weight
        blur_layout = QHBoxLayout()
        blur_layout.addWidget(QLabel("Blur:"))
        self.input_widgets['blur_weight'] = QComboBox()
        for weight in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            self.input_widgets['blur_weight'].addItem(f"{weight:.1f}", weight)
        self.input_widgets['blur_weight'].setCurrentIndex(2)  # Default to 0.4
        blur_layout.addWidget(self.input_widgets['blur_weight'])
        layout.addLayout(blur_layout)
        
        # Contrast weight
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("Contrast:"))
        self.input_widgets['contrast_weight'] = QComboBox()
        for weight in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            self.input_widgets['contrast_weight'].addItem(f"{weight:.1f}", weight)
        self.input_widgets['contrast_weight'].setCurrentIndex(2)  # Default to 0.4
        contrast_layout.addWidget(self.input_widgets['contrast_weight'])
        layout.addLayout(contrast_layout)
        
        # Noise weight
        noise_layout = QHBoxLayout()
        noise_layout.addWidget(QLabel("Noise:"))
        self.input_widgets['noise_weight'] = QComboBox()
        for weight in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            self.input_widgets['noise_weight'].addItem(f"{weight:.1f}", weight)
        self.input_widgets['noise_weight'].setCurrentIndex(1)  # Default to 0.2
        noise_layout.addWidget(self.input_widgets['noise_weight'])
        layout.addLayout(noise_layout)
    
    def _browse_folder(self):
        """Browse for a folder and update the folder_path input"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.input_widgets['folder_path'].setText(folder_path)
            self.inputs['folder_path'] = folder_path
    
    def _add_folder(self):
        """Add a folder to the folders list"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.folders_list.addItem(folder_path)
    
    def _remove_folder(self):
        """Remove selected folder from the folders list"""
        selected_items = self.folders_list.selectedItems()
        for item in selected_items:
            self.folders_list.takeItem(self.folders_list.row(item))
    
    def get_inputs(self) -> Dict:
        """Get the input values provided by the user"""
        # Get values from widgets
        if isinstance(self.workflow, ScaleGridWorkflow):
            return {
                'folder_path': self.input_widgets['folder_path'].text()
            }
        elif isinstance(self.workflow, CompareGridWorkflow):
            # Get folder paths from list widget
            folder_paths = []
            for i in range(self.folders_list.count()):
                folder_paths.append(self.folders_list.item(i).text())
            
            # Get other inputs
            return {
                'folder_paths': folder_paths,
                'magnification_target': self.input_widgets['magnification_target'].currentData(),
                'tolerance_percent': self.input_widgets['tolerance_percent'].currentData(),
                'detector_type': self.input_widgets['detector_type'].currentData()
            }
        elif isinstance(self.workflow, QualityAssessmentWorkflow):
            # Get metric weights
            return {
                'folder_path': self.input_widgets['folder_path'].text(),
                'metric_weights': {
                    'blur': self.input_widgets['blur_weight'].currentData(),
                    'contrast': self.input_widgets['contrast_weight'].currentData(),
                    'noise': self.input_widgets['noise_weight'].currentData()
                }
            }
        
        return {}
