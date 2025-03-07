import os
import json
from typing import Dict, List, Optional, Tuple
from PyQt5.QtGui import QColor

class ImageCollection:
    """Class to represent a collection of related SEM images with containment relationships"""
    
    def __init__(self, name: str, session_id: str, sample_id: str):
        self.name = name
        self.session_id = session_id
        self.sample_id = sample_id
        self.images = []  # List of image paths
        self.metadata = {}  # Dictionary mapping image paths to their metadata
        self.containment = {}  # Dictionary mapping low-mag image paths to high-mag images they contain
        self.bounding_boxes = {}  # Dictionary mapping image pairs to bounding box coordinates
        self.colors = {}  # Dictionary mapping high-mag images to their assigned colors
    
    def add_image(self, image_path: str, metadata: dict) -> None:
        """Add an image to the collection"""
        if image_path not in self.images:
            self.images.append(image_path)
            self.metadata[image_path] = metadata
    
    def add_containment(self, parent_image: str, child_image: str, bbox: tuple) -> None:
        """
        Add a containment relationship between parent (low-mag) and child (high-mag) images
        bbox is normalized coordinates (x1, y1, x2, y2) where child is located in parent
        """
        if parent_image not in self.containment:
            self.containment[parent_image] = []
        
        if child_image not in self.containment[parent_image]:
            self.containment[parent_image].append(child_image)
            self.bounding_boxes[(parent_image, child_image)] = bbox
    
    def assign_colors(self) -> None:
        """Assign distinct colors to all high-magnification images in the collection"""
        # Collect all high-mag images
        high_mag_images = set()
        for contained_images in self.containment.values():
            high_mag_images.update(contained_images)
        
        # Create a set of distinct colors
        colors = [
            QColor(255, 0, 0, 180),    # Red
            QColor(0, 255, 0, 180),    # Green
            QColor(0, 0, 255, 180),    # Blue
            QColor(255, 255, 0, 180),  # Yellow
            QColor(255, 0, 255, 180),  # Magenta
            QColor(0, 255, 255, 180),  # Cyan
            QColor(255, 128, 0, 180),  # Orange
            QColor(128, 0, 255, 180),  # Purple
            QColor(0, 128, 0, 180),    # Dark Green
            QColor(128, 128, 255, 180) # Light Blue
        ]
        
        # Assign colors to high-mag images
        for i, image in enumerate(high_mag_images):
            color_index = i % len(colors)
            # Store color as RGBA tuple for serialization
            self.colors[image] = (
                colors[color_index].red(),
                colors[color_index].green(),
                colors[color_index].blue(),
                colors[color_index].alpha()
            )
    
    def to_dict(self) -> dict:
        """Convert collection to dictionary for serialization"""
        return {
            "name": self.name,
            "session_id": self.session_id,
            "sample_id": self.sample_id,
            "images": self.images,
            "metadata": self.metadata,
            "containment": self.containment,
            "bounding_boxes": {f"{parent}|{child}": bbox 
                              for (parent, child), bbox in self.bounding_boxes.items()},
            "colors": self.colors
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ImageCollection':
        """Create collection object from dictionary"""
        collection = cls(data["name"], data["session_id"], data["sample_id"])
        collection.images = data["images"]
        collection.metadata = data["metadata"]
        collection.containment = data["containment"]
        
        # Convert string keys back to tuples for bounding_boxes
        collection.bounding_boxes = {}
        for key, bbox in data["bounding_boxes"].items():
            parent, child = key.split("|")
            collection.bounding_boxes[(parent, child)] = bbox
        
        collection.colors = data["colors"]
        return collection


class CollectionManager:
    """Class to manage SEM image collections"""
    
    def __init__(self, storage_dir: str = "collections"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def create_collection(self, name: str, session_id: str, sample_id: str) -> ImageCollection:
        """Create a new image collection"""
        return ImageCollection(name, session_id, sample_id)
    
    def save_collection(self, collection: ImageCollection) -> str:
        """Save collection to a JSON file and return the file path"""
        # Generate a filename based on collection name, session_id and sample_id
        filename = f"{collection.session_id}_{collection.sample_id}_{collection.name.replace(' ', '_')}.json"
        file_path = os.path.join(self.storage_dir, filename)
        
        # Convert to dictionary and save as JSON
        with open(file_path, 'w') as f:
            json.dump(collection.to_dict(), f, indent=2)
        
        return file_path
    
    def load_collection(self, file_path: str) -> Optional[ImageCollection]:
        """Load collection from a JSON file"""
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return ImageCollection.from_dict(data)
        except Exception as e:
            print(f"Error loading collection from {file_path}: {e}")
            return None
    
    def get_collections_for_session(self, session_id: str) -> List[str]:
        """Get list of collection file paths for a specific session"""
        collection_files = []
        
        for filename in os.listdir(self.storage_dir):
            if filename.startswith(f"{session_id}_") and filename.endswith(".json"):
                collection_files.append(os.path.join(self.storage_dir, filename))
        
        return collection_files
    
    def analyze_images(self, folder_path: str, session_id: str, sample_id: str, image_metadata: Dict[str, Dict]) -> List[ImageCollection]:
        """
        Analyze images based on their metadata and create collections based on containment relationships
        
        Args:
            folder_path: Path to folder containing TIFF images
            session_id: Session ID for these images (e.g., SEM1-123)
            sample_id: Sample ID for these images (e.g., TCL12345)
            image_metadata: Dictionary mapping image paths to their metadata
            
        Returns:
            List of ImageCollection objects
        """
        if not image_metadata:
            print(f"No image metadata provided for session {session_id}, sample {sample_id}")
            return []
        
        # Sort images by magnification (low to high)
        sorted_images = sorted(image_metadata.keys(), 
                              key=lambda x: image_metadata[x].get("Mag(pol)", 0))
        
        # Analyze containment relationships
        containment_map = self._analyze_containment(image_metadata)
        
        # Group images into collections based on containment
        collections = []
        used_images = set()
        
        # Start with highest magnification images as seeds for collections
        for i, image_path in enumerate(reversed(sorted_images)):
            if image_path in used_images:
                continue
            
            # Find all images that contain this one
            containing_images = []
            for parent_img, children in containment_map.items():
                if image_path in children:
                    containing_images.append(parent_img)
            
            if containing_images:
                # This image is contained in others, so it's part of a collection
                collection = self.create_collection(
                    f"Collection_{len(collections) + 1}", 
                    session_id,
                    sample_id
                )
                
                # Add all related images to the collection
                all_images = set([image_path] + containing_images)
                
                # Also add any images contained in our containing images
                for parent in containing_images:
                    if parent in containment_map:
                        all_images.update(containment_map[parent])
                
                for img in all_images:
                    collection.add_image(img, image_metadata[img])
                    used_images.add(img)
                
                # Add containment relationships and calculate bounding boxes
                for parent in containing_images:
                    if parent in containment_map:
                        for child in containment_map[parent]:
                            if child in all_images:
                                # Calculate bounding box
                                bbox = self._calculate_bounding_box(
                                    image_metadata[parent],
                                    image_metadata[child]
                                )
                                if bbox:
                                    collection.add_containment(parent, child, bbox)
                
                # Assign colors to high-mag images
                collection.assign_colors()
                
                collections.append(collection)
        
        # Add any remaining images as single-image collections
        for image_path in sorted_images:
            if image_path not in used_images:
                collection = self.create_collection(
                    f"Single_{os.path.basename(image_path)}", 
                    session_id,
                    sample_id
                )
                collection.add_image(image_path, image_metadata[image_path])
                collections.append(collection)
        
        return collections
    
    def _analyze_containment(self, image_metadata: Dict[str, Dict]) -> Dict[str, List[str]]:
        """
        Analyze which images fully contain other images based on FOV and position
        
        Args:
            image_metadata: Dictionary mapping image paths to their metadata
            
        Returns:
            Dictionary mapping parent images to lists of contained child images
        """
        containment_map = {}
        
        # Sort images by magnification (low to high to ensure we check lower mag first)
        sorted_images = sorted(image_metadata.keys(), 
                              key=lambda x: image_metadata[x].get("Mag(pol)", 0))
        
        # For each low-mag image, check which high-mag images it contains
        for i, low_mag_img in enumerate(sorted_images):
            low_mag_meta = image_metadata[low_mag_img]
            
            # Skip if missing required fields
            if not all(k in low_mag_meta for k in ["field_of_view_width", "field_of_view_height", 
                                                  "sample_position_x", "sample_position_y"]):
                continue
            
            # Get field of view and position for low-mag image
            low_fov_w = low_mag_meta["field_of_view_width"]
            low_fov_h = low_mag_meta["field_of_view_height"]
            low_x = low_mag_meta["sample_position_x"]
            low_y = low_mag_meta["sample_position_y"]
            
            # Check all higher magnification images
            contained_images = []
            for high_mag_img in sorted_images[i+1:]:
                high_mag_meta = image_metadata[high_mag_img]
                
                # Skip if missing required fields
                if not all(k in high_mag_meta for k in ["field_of_view_width", "field_of_view_height", 
                                                       "sample_position_x", "sample_position_y"]):
                    continue
                
                # Get field of view and position for high-mag image
                high_fov_w = high_mag_meta["field_of_view_width"]
                high_fov_h = high_mag_meta["field_of_view_height"]
                high_x = high_mag_meta["sample_position_x"]
                high_y = high_mag_meta["sample_position_y"]
                
                # Check if high-mag image is fully contained in low-mag image
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
                
                # Allow a small margin (5% of the low mag FOV)
                margin_x = low_fov_w * 0.05
                margin_y = low_fov_h * 0.05
                
                # Check if high mag FOV is inside low mag FOV (with margin)
                x_contained = ((low_mag_x_min - margin_x) < high_mag_x_min and 
                              (low_mag_x_max + margin_x) > high_mag_x_max)
                y_contained = ((low_mag_y_min - margin_y) < high_mag_y_min and 
                              (low_mag_y_max + margin_y) > high_mag_y_max)
                
                if x_contained and y_contained:
                    contained_images.append(high_mag_img)
            
            if contained_images:
                containment_map[low_mag_img] = contained_images
        
        return containment_map
    
    def _calculate_bounding_box(self, parent_metadata: Dict, child_metadata: Dict) -> Optional[Tuple[float, float, float, float]]:
        """
        Calculate the normalized bounding box coordinates of a child image within a parent image
        Returns tuple (x1, y1, x2, y2) with values from 0 to 1
        """
        try:
            # Get stage positions (in micrometers)
            if "sample_position_x" not in parent_metadata or "sample_position_x" not in child_metadata:
                return None
                
            parent_x = parent_metadata["sample_position_x"]
            parent_y = parent_metadata["sample_position_y"]
            child_x = child_metadata["sample_position_x"]
            child_y = child_metadata["sample_position_y"]
            
            # Get field widths (in micrometers)
            if "field_of_view_width" not in parent_metadata or "field_of_view_width" not in child_metadata:
                return None
                
            parent_fov_w = parent_metadata["field_of_view_width"]
            parent_fov_h = parent_metadata["field_of_view_height"]
            child_fov_w = child_metadata["field_of_view_width"]
            child_fov_h = child_metadata["field_of_view_height"]
            
            # Calculate normalized coordinates (0-1) where (0,0) is top-left of the parent image
            # First, find the position of the child FOV corners relative to the parent center
            rel_left = (child_x - child_fov_w/2 - parent_x) / parent_fov_w
            rel_right = (child_x + child_fov_w/2 - parent_x) / parent_fov_w
            # For y-coordinates, we invert because image coordinates have (0,0) at top-left
            rel_top = -(child_y + child_fov_h/2 - parent_y) / parent_fov_h
            rel_bottom = -(child_y - child_fov_h/2 - parent_y) / parent_fov_h
            
            # Convert to normalized coordinates (0-1) centered at (0.5, 0.5)
            x1 = 0.5 + rel_left
            x2 = 0.5 + rel_right
            y1 = 0.5 + rel_top
            y2 = 0.5 + rel_bottom
            
            # Ensure coordinates are within bounds
            x1 = max(0, min(1, x1))
            y1 = max(0, min(1, y1))
            x2 = max(0, min(1, x2))
            y2 = max(0, min(1, y2))
            
            return (x1, y1, x2, y2)
            
        except Exception as e:
            print(f"Error calculating bounding box: {e}")
            import traceback
            traceback.print_exc()
            return None