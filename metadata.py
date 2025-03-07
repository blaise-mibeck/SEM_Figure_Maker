import os
import csv
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from datetime import datetime
from PIL import Image

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
    
    def get_session_info_path(self, session_id: str) -> str:
        """Get the path to the session info JSON file"""
        return os.path.join(self.metadata_dir, f"{session_id}_info.json")
    
    def get_metadata_csv_path(self, session_id: str) -> str:
        """Get the path to the metadata CSV file"""
        return os.path.join(self.metadata_dir, f"{session_id}_metadata.csv")
    
    def save_session_info(self, session_info: Dict[str, Any]) -> str:
        """
        Save session information to a JSON file
        
        Args:
            session_info: Dictionary containing session information
            
        Returns:
            Path to the saved file
        """
        if "session_id" not in session_info or not session_info["session_id"]:
            raise ValueError("Session ID is required")
        
        # Add timestamp if not present
        if "timestamp" not in session_info:
            session_info["timestamp"] = datetime.now().isoformat()
        
        file_path = self.get_session_info_path(session_info["session_id"])
        
        with open(file_path, 'w') as f:
            json.dump(session_info, f, indent=2)
        
        return file_path
    
    def load_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session information from a JSON file
        
        Args:
            session_id: Session ID (e.g., SEM1-123)
            
        Returns:
            Dictionary containing session information if found, None otherwise
        """
        file_path = self.get_session_info_path(session_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session info for {session_id}: {e}")
            return None
    
    def save_images_metadata_to_csv(self, session_id: str, image_metadata: Dict[str, Dict]) -> str:
        """
        Save metadata for all images to a CSV file
        
        Args:
            session_id: Session ID (e.g., SEM1-123)
            image_metadata: Dictionary mapping image paths to their metadata
            
        Returns:
            Path to the saved CSV file
        """
        file_path = self.get_metadata_csv_path(session_id)
        
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
    
    def load_images_metadata_from_csv(self, session_id: str) -> Dict[str, Dict]:
        """
        Load metadata for all images from a CSV file
        
        Args:
            session_id: Session ID (e.g., SEM1-123)
            
        Returns:
            Dictionary mapping image paths to their metadata
        """
        file_path = self.get_metadata_csv_path(session_id)
        
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
            print(f"Error loading metadata CSV for {session_id}: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def check_if_metadata_exists(self, session_id: str) -> bool:
        """
        Check if metadata CSV exists for a session
        
        Args:
            session_id: Session ID (e.g., SEM1-123)
            
        Returns:
            True if metadata file exists, False otherwise
        """
        file_path = self.get_metadata_csv_path(session_id)
        return os.path.exists(file_path)
    
    def check_if_session_info_exists(self, session_id: str) -> bool:
        """
        Check if session info JSON exists for a session
        
        Args:
            session_id: Session ID (e.g., SEM1-123)
            
        Returns:
            True if session info file exists, False otherwise
        """
        file_path = self.get_session_info_path(session_id)
        return os.path.exists(file_path)
    
    def extract_metadata_from_tiff(self, tiff_path: str) -> Dict:
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
