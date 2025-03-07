from workflow_classes import Workflow
from typing import Dict, List, Optional, Tuple, Set
import os
from PyQt5.QtGui import QColor

# Import the new collection manager
from collection_manager import CollectionManager, ImageCollection
# Import the metadata manager
from metadata_manager import MetadataManager

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
    
    def __init__(self, data_repository=None):  # data_repository parameter is kept for compatibility but not used
        super().__init__(
            "Scale Grid", 
            "Create a grid of images with containment relationships and save as collections"
        )
        # We don't use data_repository anymore
        self.collection_manager = CollectionManager()
        self.metadata_manager = MetadataManager()
    
    def get_required_inputs(self) -> List[str]:
        return ["folder_path"]
    
    def execute(self, folder_path: str, sample_id: str = None, sample_info: Dict = None, 
              use_existing_metadata: bool = True, **kwargs) -> Dict:
        """
        Execute the modified ScaleGrid workflow
        
        Args:
            folder_path: Path to the folder containing SEM images
            sample_id: Optional sample ID (if None, will be extracted from folder name)
            sample_info: Optional sample information dictionary
            use_existing_metadata: Whether to use existing metadata if available
            
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
        if sample_info is None:
            # Check if we have existing sample information
            existing_info = self.metadata_manager.load_sample_info(sample_id)
            
            if existing_info:
                # We have existing info, but confirm with user if they want to use it
                return {
                    "status": "confirm_sample_info",
                    "folder_path": folder_path,
                    "sample_id": sample_id,
                    "existing_info": existing_info
                }
            else:
                # No existing info, need to prompt user
                return {
                    "status": "need_sample_info",
                    "folder_path": folder_path,
                    "suggested_sample_id": sample_id
                }
        
        try:
            # Save the sample information
            self.metadata_manager.save_sample_info(sample_info)
            
            # Check if we should use existing metadata
            image_metadata = {}
            
            if use_existing_metadata and self.metadata_manager.check_if_metadata_exists(sample_id):
                # Load existing metadata from CSV
                image_metadata = self.metadata_manager.load_images_metadata_from_csv(sample_id)
                
                # Verify that all files still exist
                missing_files = []
                for image_path in list(image_metadata.keys()):
                    if not os.path.exists(image_path):
                        missing_files.append(image_path)
                        del image_metadata[image_path]
                
                if missing_files:
                    print(f"Warning: {len(missing_files)} files referenced in metadata no longer exist")
                
                if not image_metadata:
                    # All files are missing, need to extract metadata again
                    use_existing_metadata = False
            else:
                use_existing_metadata = False
                
            # Extract metadata if needed
            if not use_existing_metadata:
                # Use extract_metadata_from_tiff function
                if "extract_metadata_func" not in kwargs:
                    return {
                        "status": "error",
                        "message": "Missing extract_metadata_func"
                    }
                
                extract_metadata_func = kwargs["extract_metadata_func"]
                
                # Find all TIFF files in the folder
                tiff_files = []
                for filename in os.listdir(folder_path):
                    if filename.lower().endswith(('.tiff', '.tif')):
                        tiff_files.append(os.path.join(folder_path, filename))
                
                # Extract metadata from all files
                for tiff_file in tiff_files:
                    try:
                        metadata = extract_metadata_func(tiff_file)
                        if metadata:
                            image_metadata[tiff_file] = metadata
                    except Exception as e:
                        print(f"Error extracting metadata from {tiff_file}: {e}")
                
                # Save the metadata to CSV
                if image_metadata:
                    self.metadata_manager.save_images_metadata_to_csv(sample_id, image_metadata)
            
            # Check if we have any metadata
            if not image_metadata:
                return {
                    "status": "error",
                    "message": f"No valid image metadata found in {folder_path}"
                }
            
            # Analyze images and create collections
            collections = self.collection_manager.analyze_images_from_metadata(
                sample_id,
                image_metadata
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