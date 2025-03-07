import os
import csv
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class MetadataManager:
    """Class to manage metadata storage and retrieval for SEM samples"""
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize the metadata manager
        
        Args:
            base_dir: Base directory for storing metadata files
        """
        self.base_dir = base_dir
        self.metadata_dir = os.path.join(base_dir, "metadata")
        os.makedirs(self.metadata_dir, exist_ok=True)
    
    def get_sample_info_path(self, sample_id: str) -> str:
        """Get the path to the sample info JSON file"""
        return os.path.join(self.metadata_dir, f"{sample_id}_info.json")
    
    def get_metadata_csv_path(self, sample_id: str) -> str:
        """Get the path to the metadata CSV file"""
        return os.path.join(self.metadata_dir, f"{sample_id}_metadata.csv")
    
    def save_sample_info(self, sample_info: Dict[str, Any]) -> str:
        """
        Save sample information to a JSON file
        
        Args:
            sample_info: Dictionary containing sample information
            
        Returns:
            Path to the saved file
        """
        if "sample_id" not in sample_info or not sample_info["sample_id"]:
            raise ValueError("Sample ID is required")
        
        # Add timestamp if not present
        if "timestamp" not in sample_info:
            sample_info["timestamp"] = datetime.now().isoformat()
        
        file_path = self.get_sample_info_path(sample_info["sample_id"])
        
        with open(file_path, 'w') as f:
            json.dump(sample_info, f, indent=2)
        
        return file_path
    
    def load_sample_info(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """
        Load sample information from a JSON file
        
        Args:
            sample_id: Sample ID
            
        Returns:
            Dictionary containing sample information if found, None otherwise
        """
        file_path = self.get_sample_info_path(sample_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading sample info for {sample_id}: {e}")
            return None
    
    def save_images_metadata_to_csv(self, sample_id: str, image_metadata: Dict[str, Dict]) -> str:
        """
        Save metadata for all images to a CSV file
        
        Args:
            sample_id: Sample ID
            image_metadata: Dictionary mapping image paths to their metadata
            
        Returns:
            Path to the saved CSV file
        """
        file_path = self.get_metadata_csv_path(sample_id)
        
        # Extract all possible field names from all metadata dictionaries
        fieldnames = set()
        for metadata in image_metadata.values():
            fieldnames.update(metadata.keys())
        
        # Sort fieldnames for consistency, but ensure some important fields come first
        priority_fields = ["image_path", "databarLabel", "Mag(pol)", "field_of_view_width", 
                         "field_of_view_height", "sample_position_x", "sample_position_y",
                         "detector", "high_voltage_kV", "working_distance_mm"]
        
        sorted_fieldnames = [f for f in priority_fields if f in fieldnames]
        sorted_fieldnames.extend([f for f in sorted(fieldnames) if f not in priority_fields])
        
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted_fieldnames)
            writer.writeheader()
            
            for image_path, metadata in image_metadata.items():
                # Add image_path to metadata if not already there
                row_data = metadata.copy()
                if "image_path" not in row_data:
                    row_data["image_path"] = image_path
                writer.writerow(row_data)
        
        return file_path
    
    def load_images_metadata_from_csv(self, sample_id: str) -> Dict[str, Dict]:
        """
        Load metadata for all images from a CSV file
        
        Args:
            sample_id: Sample ID
            
        Returns:
            Dictionary mapping image paths to their metadata
        """
        file_path = self.get_metadata_csv_path(sample_id)
        
        if not os.path.exists(file_path):
            return {}
        
        try:
            image_metadata = {}
            
            with open(file_path, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # Use the image_path as the key
                    if "image_path" in row and row["image_path"]:
                        image_path = row["image_path"]
                        
                        # Convert numeric fields from strings
                        for key, value in row.items():
                            if value == "":
                                continue
                                
                            # Try to convert to appropriate type
                            try:
                                if "." in value:
                                    row[key] = float(value)
                                else:
                                    row[key] = int(value)
                            except ValueError:
                                # Keep as string if conversion fails
                                pass
                        
                        image_metadata[image_path] = row
            
            return image_metadata
            
        except Exception as e:
            print(f"Error loading metadata CSV for {sample_id}: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def check_if_metadata_exists(self, sample_id: str) -> bool:
        """
        Check if metadata CSV exists for a sample
        
        Args:
            sample_id: Sample ID
            
        Returns:
            True if metadata file exists, False otherwise
        """
        file_path = self.get_metadata_csv_path(sample_id)
        return os.path.exists(file_path)
    
    def check_if_sample_info_exists(self, sample_id: str) -> bool:
        """
        Check if sample info JSON exists for a sample
        
        Args:
            sample_id: Sample ID
            
        Returns:
            True if sample info file exists, False otherwise
        """
        file_path = self.get_sample_info_path(sample_id)
        return os.path.exists(file_path)
