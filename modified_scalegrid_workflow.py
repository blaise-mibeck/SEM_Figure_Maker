from workflow_classes import Workflow
from typing import Dict, List, Optional, Tuple, Set
import os
from PyQt5.QtGui import QColor

# Import the new collection manager
from collection_manager import CollectionManager, ImageCollection

class ModifiedScaleGridWorkflow(Workflow):
    """
    Modified ScaleGrid Workflow:
    1. Given a folder of SEM images from the same sample
    2. Process each TIFF image to collect metadata
    3. Determine containment relationships between images using FOV and position
    4. Group related images into collections based on containment
    5. Create collection files (.json) with all information needed to create grid images
    6. Add colored bounding boxes and matching borders
    7. Provide options for showing/hiding boxes and changing line styles
    """
    
    def __init__(self, data_repository):
        super().__init__(
            "Scale Grid", 
            "Create a grid of images with containment relationships and save as collections"
        )
        self.data_repository = data_repository
        self.collection_manager = CollectionManager()
    
    def get_required_inputs(self) -> List[str]:
        return ["folder_path"]
    
    def execute(self, folder_path: str, sample_id: str = None, **kwargs) -> Dict:
        """
        Execute the modified ScaleGrid workflow
        
        Args:
            folder_path: Path to the folder containing SEM images
            sample_id: Optional sample ID (if None, will be extracted from folder name)
            
        Returns:
            Dictionary with the result, containing:
                - status: Success or error status
                - sample_id: Sample ID used
                - collections: List of ImageCollection objects created
                - collection_files: List of JSON files saved
                - first_collection: The first collection for immediate display
        """
        # Extract sample ID from folder name if not provided
        if sample_id is None:
            folder_name = os.path.basename(folder_path)
            
            # Try to extract SEM1-### pattern from folder name
            import re
            folder_match = re.search(r'(SEM\d+-\d+)', folder_name)
            if folder_match:
                sample_id = folder_match.group(1)
            else:
                sample_id = folder_name
        
        # Check if the folder exists
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return {
                "status": "error",
                "message": f"Invalid folder path: {folder_path}"
            }
        
        # Check if we need to prompt for sample information
        sample = self.data_repository.load_sample(sample_id)
        if not sample:
            return {
                "status": "need_sample_info",
                "folder_path": folder_path,
                "suggested_sample_id": sample_id
            }
        
        try:
            # Use extract_metadata_from_tiff function from basic_controller
            # This requires us to pass this function from the controller
            if "extract_metadata_func" not in kwargs:
                return {
                    "status": "error",
                    "message": "Missing extract_metadata_func"
                }
            
            extract_metadata_func = kwargs["extract_metadata_func"]
            
            # Analyze images and create collections
            collections = self.collection_manager.analyze_images(
                folder_path, 
                sample_id,
                extract_metadata_func
            )
            
            if not collections:
                return {
                    "status": "error",
                    "message": f"No valid image collections found in {folder_path}"
                }
            
            # Save collections to JSON files
            collection_files = []
            for collection in collections:
                file_path = self.collection_manager.save_collection(collection)
                collection_files.append(file_path)
            
            # Return the first collection for immediate display
            return {
                "status": "success",
                "sample_id": sample_id,
                "collections": collections,
                "collection_files": collection_files,
                "first_collection": collections[0]
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Error in ScaleGrid workflow: {str(e)}"
            }
