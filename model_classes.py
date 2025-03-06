import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
from PIL import Image
import PyPhenom as ppi

class ImageMetadata:
    """Class to store SEM image metadata"""
    
    def __init__(self, 
                 image_path: str, 
                 magnification: float = 0, 
                 pixel_size: float = 0,
                 width_um: float = 0, 
                 height_um: float = 0,
                 working_distance: float = 0,
                 detector_type: str = "",
                 beam_voltage: float = 0,
                 stage_position_x: float = 0,
                 stage_position_y: float = 0,
                 acquisition_timestamp: datetime = None):
        self.image_path = image_path
        self.magnification = magnification
        self.pixel_size = pixel_size
        self.width_um = width_um
        self.height_um = height_um
        self.working_distance = working_distance
        self.detector_type = detector_type
        self.beam_voltage = beam_voltage
        self.stage_position_x = stage_position_x
        self.stage_position_y = stage_position_y
        self.acquisition_timestamp = acquisition_timestamp or datetime.now()
        
        # For containment relationships
        self.contained_in: List['ImageMetadata'] = []
        self.contains: List['ImageMetadata'] = []
        
    def to_dict(self) -> Dict:
        """Convert metadata to dictionary for serialization"""
        return {
            'image_path': self.image_path,
            'magnification': self.magnification,
            'pixel_size': self.pixel_size,
            'width_um': self.width_um,
            'height_um': self.height_um,
            'working_distance': self.working_distance,
            'detector_type': self.detector_type,
            'beam_voltage': self.beam_voltage,
            'stage_position_x': self.stage_position_x,
            'stage_position_y': self.stage_position_y,
            'acquisition_timestamp': self.acquisition_timestamp.isoformat() if self.acquisition_timestamp else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ImageMetadata':
        """Create metadata object from dictionary"""
        metadata = cls(data['image_path'])
        metadata.magnification = data.get('magnification', 0)
        metadata.pixel_size = data.get('pixel_size', 0)
        metadata.width_um = data.get('width_um', 0)
        metadata.height_um = data.get('height_um', 0)
        metadata.working_distance = data.get('working_distance', 0)
        metadata.detector_type = data.get('detector_type', "")
        metadata.beam_voltage = data.get('beam_voltage', 0)
        metadata.stage_position_x = data.get('stage_position_x', 0)
        metadata.stage_position_y = data.get('stage_position_y', 0)
        
        if data.get('acquisition_timestamp'):
            metadata.acquisition_timestamp = datetime.fromisoformat(data['acquisition_timestamp'])
        
        return metadata


class Sample:
    """Class to store sample information"""
    
    def __init__(self, 
                 sample_id: str,
                 preparation_method: str = "",
                 notes: str = "",
                 creation_date: datetime = None):
        self.sample_id = sample_id
        self.preparation_method = preparation_method
        self.notes = notes
        self.creation_date = creation_date or datetime.now()
        self.images: List[ImageMetadata] = []
        
    def add_image(self, image_metadata: ImageMetadata) -> None:
        """Add image metadata to this sample"""
        self.images.append(image_metadata)
        
    def to_dict(self) -> Dict:
        """Convert sample to dictionary for serialization"""
        return {
            'sample_id': self.sample_id,
            'preparation_method': self.preparation_method,
            'notes': self.notes,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'images': [img.to_dict() for img in self.images]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Sample':
        """Create sample object from dictionary"""
        sample = cls(data['sample_id'])
        sample.preparation_method = data.get('preparation_method', "")
        sample.notes = data.get('notes', "")
        
        if data.get('creation_date'):
            sample.creation_date = datetime.fromisoformat(data['creation_date'])
        
        # Load images
        if 'images' in data:
            for img_data in data['images']:
                sample.images.append(ImageMetadata.from_dict(img_data))
                
        return sample


class PhenomAPI:
    """Interface for the Phenom microscope API using PyPhenom"""
    
    def __init__(self, phenom_id: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """Initialize connection to Phenom API
        
        Args:
            phenom_id: Phenom instrument ID (e.g., 'MVE012345678')
            username: Username for Phenom API access
            password: Password for Phenom API access
        """
        self.phenom_id = phenom_id
        self.username = username
        self.password = password
        self.phenom = None
        
    def connect(self):
        """Connect to the Phenom instrument"""
        try:
            if self.phenom_id and self.username and self.password:
                # Connect with explicit credentials
                self.phenom = ppi.Phenom(self.phenom_id, self.username, self.password)
            elif self.phenom_id:
                # Connect with just the instrument ID (using installed license)
                self.phenom = ppi.Phenom(self.phenom_id)
            else:
                # Connect to default Phenom (using installed license)
                self.phenom = ppi.Phenom()
            
            # Check connection by getting instrument mode
            mode = self.phenom.GetInstrumentMode()
            print(f"Connected to Phenom: Instrument mode is {mode}")
            return True
            
        except Exception as e:
            print(f"Error connecting to Phenom: {e}")
            # If connection fails, use a simulator for testing
            self.phenom = ppi.Phenom('Simulator', '', '')
            print("Connected to Phenom simulator")
            return False
            
    def extract_metadata_from_file(self, image_path: str) -> ImageMetadata:
        """
        Extract metadata from a SEM image file using the Phenom API
        
        Args:
            image_path: Path to the SEM image file
            
        Returns:
            ImageMetadata object with the extracted metadata
        """
        try:
            # Load the image and metadata
            acquisition = ppi.Load(image_path)
            return self.acquisition_to_metadata(acquisition, image_path)
            
        except Exception as e:
            print(f"Error extracting metadata from {image_path}: {e}")
            # Fall back to placeholder implementation
            return self.create_placeholder_metadata(image_path)
    
    def acquisition_to_metadata(self, acquisition, image_path: str) -> ImageMetadata:
        """Convert Phenom acquisition object to ImageMetadata"""
        metadata = ImageMetadata(image_path)
        
        # Extract metadata from the acquisition object
        metadata.magnification = acquisition.magnification
        metadata.pixel_size = acquisition.metadata.pixelSize.width * 1e6  # Convert to nm/pixel
        metadata.width_um = acquisition.image.width * acquisition.metadata.pixelSize.width * 1e6
        metadata.height_um = acquisition.image.height * acquisition.metadata.pixelSize.height * 1e6
        metadata.working_distance = acquisition.metadata.workingDistance * 1000  # Convert to mm
        
        # Get detector type
        if hasattr(acquisition.metadata, 'segments'):
            if acquisition.metadata.segments == ppi.DetectorMode.All:
                metadata.detector_type = "BSD"
            elif acquisition.metadata.segments == ppi.DetectorMode.Sed:
                metadata.detector_type = "SED"
            else:
                metadata.detector_type = f"BSD-{acquisition.metadata.segments}"
        else:
            metadata.detector_type = "Unknown"
        
        # Get beam voltage
        metadata.beam_voltage = abs(acquisition.metadata.highVoltage) / 1000  # Convert to kV
        
        # Get stage position
        if hasattr(acquisition.metadata, 'position'):
            metadata.stage_position_x = acquisition.metadata.position.x * 1000  # Convert to mm
            metadata.stage_position_y = acquisition.metadata.position.y * 1000  # Convert to mm
        
        # Get timestamp
        if hasattr(acquisition.metadata, 'time'):
            metadata.acquisition_timestamp = datetime.fromtimestamp(acquisition.metadata.time)
        
        return metadata
    
    def create_placeholder_metadata(self, image_path: str) -> ImageMetadata:
        """Create placeholder metadata when API extraction fails"""
        metadata = ImageMetadata(image_path)
        
        # Get basic image properties
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Extract magnification from filename if possible
                filename = os.path.basename(image_path)
                import re
                mag_match = re.search(r'(\d+)x', filename)
                if mag_match:
                    metadata.magnification = float(mag_match.group(1))
                else:
                    # Default random magnification for testing
                    metadata.magnification = np.random.choice([500, 1000, 2500, 5000, 10000])
                
                # Estimate other metadata
                metadata.pixel_size = 1000 / metadata.magnification  # nm/pixel
                metadata.width_um = width * metadata.pixel_size / 1000
                metadata.height_um = height * metadata.pixel_size / 1000
                metadata.working_distance = np.random.uniform(5, 15)  # mm
                metadata.detector_type = np.random.choice(["BSD", "SED"])
                metadata.beam_voltage = np.random.choice([5, 10, 15, 20])  # kV
                metadata.stage_position_x = np.random.uniform(-10, 10)  # mm
                metadata.stage_position_y = np.random.uniform(-10, 10)  # mm
                
                # Use file creation/modification time for timestamp
                timestamp = os.path.getmtime(image_path)
                metadata.acquisition_timestamp = datetime.fromtimestamp(timestamp)
        
        except Exception as e:
            print(f"Error creating placeholder metadata for {image_path}: {e}")
            
        return metadata
            
    def acquire_live_image(self, size=(1920, 1200), frames=16, detector=None, hdr=False) -> ImageMetadata:
        """
        Acquire a live image from the connected Phenom
        
        Args:
            size: Image size (width, height) in pixels
            frames: Number of frames to average
            detector: Detector mode (None for default)
            hdr: Whether to use high dynamic range mode
            
        Returns:
            ImageMetadata object with the acquired image metadata
        """
        if not self.phenom:
            raise ValueError("Not connected to Phenom")
            
        if detector is None:
            detector = ppi.DetectorMode.All
            
        # Acquire image
        acquisition = self.phenom.SemAcquireImage(size[0], size[1], frames, detector, hdr)
        
        # Create a temporary file path
        temp_path = os.path.join(os.getcwd(), "temp_acquisition.tiff")
        
        # Save the acquisition to a file
        ppi.Save(acquisition, temp_path)
        
        # Convert to metadata
        metadata = self.acquisition_to_metadata(acquisition, temp_path)
        
        return metadata


class MagnificationAnalyzer:
    """Analyzes magnification relationships between images"""
    
    @staticmethod
    def determine_containment(images: List[ImageMetadata]) -> None:
        """
        Determine which high-magnification images are contained within low-magnification images
        based on stage position, magnification, and field of view.
        
        Updates the contained_in and contains relationships of each image.
        """
        # Sort images by magnification (ascending)
        sorted_images = sorted(images, key=lambda x: x.magnification)
        
        # Clear existing relationships
        for img in sorted_images:
            img.contained_in = []
            img.contains = []
        
        # For each higher magnification image, check if it's contained in lower mag images
        for i, high_mag_img in enumerate(sorted_images):
            for low_mag_img in sorted_images[:i]:  # Only check lower magnification images
                
                # Check if the high mag image is within the field of view of the low mag image
                # Calculate the center position of the high mag image
                high_center_x = high_mag_img.stage_position_x
                high_center_y = high_mag_img.stage_position_y
                
                # Calculate the boundaries of the low mag image
                low_width_half = low_mag_img.width_um / 2
                low_height_half = low_mag_img.height_um / 2
                
                low_min_x = low_mag_img.stage_position_x - low_width_half
                low_max_x = low_mag_img.stage_position_x + low_width_half
                low_min_y = low_mag_img.stage_position_y - low_height_half
                low_max_y = low_mag_img.stage_position_y + low_height_half
                
                # Calculate the boundaries of the high mag image
                high_width_half = high_mag_img.width_um / 2
                high_height_half = high_mag_img.height_um / 2
                
                high_min_x = high_center_x - high_width_half
                high_max_x = high_center_x + high_width_half
                high_min_y = high_center_y - high_height_half
                high_max_y = high_center_y + high_height_half
                
                # Check if the high mag image is completely contained within the low mag image
                if (high_min_x >= low_min_x and high_max_x <= low_max_x and
                    high_min_y >= low_min_y and high_max_y <= low_max_y):
                    
                    # Add containment relationship
                    high_mag_img.contained_in.append(low_mag_img)
                    low_mag_img.contains.append(high_mag_img)
    
    @staticmethod
    def calculate_bounding_box(parent_img: ImageMetadata, child_img: ImageMetadata) -> Tuple[float, float, float, float]:
        """
        Calculate the bounding box of a child image within its parent image.
        Returns normalized coordinates (x1, y1, x2, y2) where
        (0,0) is the top-left corner and (1,1) is the bottom-right corner of the parent image.
        """
        # Parent image dimensions
        parent_width = parent_img.width_um
        parent_height = parent_img.height_um
        
        # Child image dimensions
        child_width = child_img.width_um
        child_height = child_img.height_um
        
        # Calculate relative positions
        parent_center_x = parent_img.stage_position_x
        parent_center_y = parent_img.stage_position_y
        child_center_x = child_img.stage_position_x
        child_center_y = child_img.stage_position_y
        
        # Convert to parent image coordinate system (0,0 at center)
        rel_x = child_center_x - parent_center_x
        rel_y = child_center_y - parent_center_y
        
        # Convert to top-left origin and normalize to 0-1 range
        x1 = (rel_x - child_width/2 + parent_width/2) / parent_width
        y1 = (rel_y - child_height/2 + parent_height/2) / parent_height
        x2 = (rel_x + child_width/2 + parent_width/2) / parent_width
        y2 = (rel_y + child_height/2 + parent_height/2) / parent_height
        
        # Clamp to 0-1 range
        x1 = max(0, min(1, x1))
        y1 = max(0, min(1, y1))
        x2 = max(0, min(1, x2))
        y2 = max(0, min(1, y2))
        
        return (x1, y1, x2, y2)


class DataRepository:
    """Repository for persistent storage of samples and their data"""
    
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def save_sample(self, sample: Sample) -> None:
        """Save sample data to disk"""
        file_path = os.path.join(self.storage_dir, f"{sample.sample_id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(sample.to_dict(), f, indent=2)
    
    def load_sample(self, sample_id: str) -> Optional[Sample]:
        """Load sample data from disk"""
        file_path = os.path.join(self.storage_dir, f"{sample_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return Sample.from_dict(data)
        except Exception as e:
            print(f"Error loading sample {sample_id}: {e}")
            return None
    
    def get_all_sample_ids(self) -> List[str]:
        """Get IDs of all saved samples"""
        sample_ids = []
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                sample_ids.append(filename.replace('.json', ''))
        
        return sample_ids
    
    def delete_sample(self, sample_id: str) -> bool:
        """Delete a sample from storage"""
        file_path = os.path.join(self.storage_dir, f"{sample_id}.json")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        
        return False


class ImageProcessor:
    """Processes SEM images to extract metadata and analyze relationships"""
    
    def __init__(self, phenom_api: PhenomAPI):
        self.phenom_api = phenom_api
        self.mag_analyzer = MagnificationAnalyzer()
    
    def process_folder(self, folder_path: str) -> List[ImageMetadata]:
        """
        Process all SEM images in a folder
        Returns a list of image metadata objects
        
        Args:
            folder_path: Path to the folder containing SEM images
            
        Returns:
            List of ImageMetadata objects for all processed images
        """
        image_metadatas = []
        
        # Check if the folder exists
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            raise ValueError(f"Invalid folder path: {folder_path}")
        
        # Check for folder pattern (SEM1-### or EDX1-###)
        folder_name = os.path.basename(folder_path)
        is_sem_folder = any(pattern in folder_name for pattern in ["SEM", "EDX"])
        
        # Get all image files in the folder
        image_extensions = ('.jpg', '.jpeg', '.tif', '.tiff', '.png', '.bmp')
        image_files = [
            os.path.join(folder_path, filename)
            for filename in os.listdir(folder_path)
            if os.path.splitext(filename.lower())[1] in image_extensions
        ]
        
        # Process each image
        for image_path in image_files:
            try:
                # Extract metadata using Phenom API
                metadata = self.phenom_api.extract_metadata_from_file(image_path)
                image_metadatas.append(metadata)
            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
        
        # Analyze magnification relationships
        if image_metadatas:
            self.mag_analyzer.determine_containment(image_metadatas)
        
        return image_metadatas
    
    def create_sample_from_folder(self, folder_path: str, sample_id: str, 
                                 preparation_method: str = "", notes: str = "") -> Sample:
        """
        Create a Sample object from a folder of SEM images
        
        Args:
            folder_path: Path to the folder containing SEM images
            sample_id: Identifier for the sample
            preparation_method: Description of how the sample was prepared
            notes: Additional notes about the sample
            
        Returns:
            Sample object containing metadata for all images in the folder
        """
        # Create new sample
        sample = Sample(sample_id, preparation_method, notes)
        
        # Process images in the folder
        image_metadatas = self.process_folder(folder_path)
        
        # Add images to sample
        for metadata in image_metadatas:
            sample.add_image(metadata)
        
        return sample
        
    def extract_folder_pattern(self, folder_path: str) -> Dict:
        """
        Extract pattern information from folder name
        
        Args:
            folder_path: Path to the folder
            
        Returns:
            Dictionary with extracted information
        """
        folder_name = os.path.basename(folder_path)
        result = {}
        
        # Check for SEM1-### or EDX1-### pattern
        import re
        pattern_match = re.match(r'(SEM|EDX)(\d+)-(\d+)', folder_name)
        
        if pattern_match:
            result['type'] = pattern_match.group(1)  # SEM or EDX
            result['series'] = pattern_match.group(2)  # Series number
            result['number'] = pattern_match.group(3)  # Sample number
            
        return result
