import os
import json
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum, auto
import numpy as np
from PIL import Image

from model_classes import ImageMetadata, Sample, MagnificationAnalyzer, DataRepository

class WorkflowType(Enum):
    """Types of workflows supported by the application"""
    SCALE_GRID = auto()
    COMPARE_GRID = auto()
    QUALITY_ASSESSMENT = auto()


class Workflow:
    """Base class for all workflows"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def execute(self, *args, **kwargs):
        """Execute the workflow"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_required_inputs(self) -> List[str]:
        """Get the list of required inputs for this workflow"""
        raise NotImplementedError("Subclasses must implement this method")


class ScaleGridWorkflow(Workflow):
    """
    ScaleGrid Workflow:
    1. Given a folder of SEM images from the same sample
    2. Process each image to collect metadata
    3. Determine magnification relationships (which high-mag images are contained in low-mag images)
    4. Display a grid of images with increasing magnification
    5. Allow for drawing boxes on low-mag images to show high-mag locations
    """
    
    def __init__(self, data_repository: DataRepository):
        super().__init__(
            "Scale Grid", 
            "Create a grid of images from the same sample with increasing magnification"
        )
        self.data_repository = data_repository
    
    def get_required_inputs(self) -> List[str]:
        return ["folder_path"]
    
    def execute(self, folder_path: str, sample_id: str = None, **kwargs) -> Dict:
        """
        Execute the ScaleGrid workflow
        
        Args:
            folder_path: Path to the folder containing SEM images
            sample_id: Optional sample ID (if None, will be extracted from folder name)
            
        Returns:
            Dictionary with the result, containing:
                - sample: The Sample object
                - images: List of ImageMetadata objects sorted by magnification
                - containment_map: Dictionary mapping image indices to contained image indices
        """
        # Extract sample ID from folder name if not provided
        if sample_id is None:
            sample_id = os.path.basename(folder_path)
        
        # Check if we have this sample cached
        sample = self.data_repository.load_sample(sample_id)
        
        # If not found or empty, create a new sample
        if sample is None or not sample.images:
            # This would be handled by the controller, which has the ImageProcessor
            return {
                "status": "need_processing",
                "folder_path": folder_path,
                "sample_id": sample_id
            }
        
        # Sort images by magnification
        sorted_images = sorted(sample.images, key=lambda x: x.magnification)
        
        # Create containment map for UI to show relationships
        containment_map = {}
        for i, img in enumerate(sorted_images):
            contained_indices = []
            for j, other_img in enumerate(sorted_images):
                if other_img in img.contains:
                    contained_indices.append(j)
            if contained_indices:
                containment_map[i] = contained_indices
        
        return {
            "status": "success",
            "sample": sample,
            "images": sorted_images,
            "containment_map": containment_map
        }


class CompareGridWorkflow(Workflow):
    """
    CompareGrid Workflow:
    1. Given several folders, each with one sample imaged
    2. Use the metadata to find images taken with similar image mode and magnification
    3. Put these images together in a grid with sample labels
    """
    
    def __init__(self, data_repository: DataRepository):
        super().__init__(
            "Compare Grid", 
            "Compare images from different samples at similar magnification"
        )
        self.data_repository = data_repository
    
    def get_required_inputs(self) -> List[str]:
        return ["folder_paths", "magnification_target", "tolerance_percent"]
    
    def execute(self, folder_paths: List[str], magnification_target: float = None, 
                tolerance_percent: float = 20, detector_type: str = None, **kwargs) -> Dict:
        """
        Execute the CompareGrid workflow
        
        Args:
            folder_paths: List of paths to folders containing SEM images
            magnification_target: Target magnification to match (if None, will be determined from available images)
            tolerance_percent: Percentage tolerance for magnification matching (default 20%)
            detector_type: If provided, only match images with this detector type
            
        Returns:
            Dictionary with the result, containing:
                - samples: List of Sample objects
                - matched_images: List of tuples (sample_index, image) for the matched images
                - magnification: Actual magnification target used
        """
        # Load samples from each folder
        samples = []
        for folder_path in folder_paths:
            sample_id = os.path.basename(folder_path)
            sample = self.data_repository.load_sample(sample_id)
            
            # If not found, need to process
            if sample is None:
                return {
                    "status": "need_processing",
                    "folder_path": folder_path,
                    "sample_id": sample_id
                }
            
            samples.append(sample)
        
        # If no magnification_target provided, analyze available magnifications and pick a common one
        if magnification_target is None:
            magnification_target = self._find_common_magnification(samples, detector_type)
            
        # If we still don't have a target, return an error
        if magnification_target is None:
            return {
                "status": "error",
                "message": "Could not find a common magnification across samples"
            }
        
        # Find matching images from each sample
        matched_images = []
        magnification_min = magnification_target * (1 - tolerance_percent/100)
        magnification_max = magnification_target * (1 + tolerance_percent/100)
        
        for i, sample in enumerate(samples):
            best_match = None
            best_match_diff = float('inf')
            
            for img in sample.images:
                # Skip if detector type doesn't match
                if detector_type and img.detector_type != detector_type:
                    continue
                
                # Check if magnification is within tolerance
                if magnification_min <= img.magnification <= magnification_max:
                    # Pick the closest match
                    diff = abs(img.magnification - magnification_target)
                    if diff < best_match_diff:
                        best_match = img
                        best_match_diff = diff
            
            if best_match:
                matched_images.append((i, best_match))
        
        # Return result
        return {
            "status": "success",
            "samples": samples,
            "matched_images": matched_images,
            "magnification": magnification_target
        }
    
    def _find_common_magnification(self, samples: List[Sample], detector_type: str = None) -> Optional[float]:
        """Find a magnification value that is common across samples"""
        # Collect all magnification values
        all_magnifications = []
        for sample in samples:
            for img in sample.images:
                if detector_type and img.detector_type != detector_type:
                    continue
                all_magnifications.append(img.magnification)
        
        if not all_magnifications:
            return None
        
        # Group magnifications into ranges (with 10% tolerance)
        ranges = {}
        for mag in all_magnifications:
            found = False
            for range_center in ranges.keys():
                if 0.9 * range_center <= mag <= 1.1 * range_center:
                    ranges[range_center].append(mag)
                    found = True
                    break
            
            if not found:
                ranges[mag] = [mag]
        
        # Find the range that appears in most samples
        best_range = None
        best_count = 0
        
        for range_center, values in ranges.items():
            # Count unique samples that have this magnification
            sample_indices = set()
            for sample_idx, sample in enumerate(samples):
                for img in sample.images:
                    if detector_type and img.detector_type != detector_type:
                        continue
                    if 0.9 * range_center <= img.magnification <= 1.1 * range_center:
                        sample_indices.add(sample_idx)
                        break
            
            if len(sample_indices) > best_count:
                best_count = len(sample_indices)
                best_range = range_center
        
        return best_range


class ImageQualityMetrics:
    """Class for assessing image quality"""
    
    @staticmethod
    def calculate_blur_metric(image_path: str) -> float:
        """
        Calculate a blur metric for the image (higher value = less blur)
        Uses the variance of the Laplacian method
        """
        try:
            # Open the image
            img = Image.open(image_path).convert('L')  # Convert to grayscale
            img_array = np.array(img)
            
            # Calculate the Laplacian
            laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
            conv = np.abs(ImageQualityMetrics._convolve2d(img_array, laplacian))
            
            # Return the variance
            return np.var(conv)
        except Exception as e:
            print(f"Error calculating blur metric: {e}")
            return 0.0
    
    @staticmethod
    def calculate_contrast_metric(image_path: str) -> float:
        """
        Calculate a contrast metric for the image (higher value = more contrast)
        Uses the standard deviation of pixel values
        """
        try:
            # Open the image
            img = Image.open(image_path).convert('L')  # Convert to grayscale
            img_array = np.array(img)
            
            # Return the standard deviation
            return np.std(img_array)
        except Exception as e:
            print(f"Error calculating contrast metric: {e}")
            return 0.0
    
    @staticmethod
    def calculate_noise_metric(image_path: str) -> float:
        """
        Calculate a noise metric for the image (higher value = more noise)
        Uses a simple estimation based on local variance
        """
        try:
            # Open the image
            img = Image.open(image_path).convert('L')  # Convert to grayscale
            img_array = np.array(img)
            
            # Compute local variance
            local_var = ImageQualityMetrics._local_variance(img_array, window_size=5)
            
            # Return the median of local variances (robust to outliers)
            return np.median(local_var)
        except Exception as e:
            print(f"Error calculating noise metric: {e}")
            return 0.0
    
    @staticmethod
    def _convolve2d(image, kernel):
        """Simple 2D convolution implementation"""
        k_height, k_width = kernel.shape
        pad_height, pad_width = k_height // 2, k_width // 2
        
        # Pad the image
        padded = np.pad(image, ((pad_height, pad_height), (pad_width, pad_width)), mode='reflect')
        
        # Create output array
        output = np.zeros_like(image)
        
        # Perform convolution
        for i in range(image.shape[0]):
            for j in range(image.shape[1]):
                region = padded[i:i+k_height, j:j+k_width]
                output[i, j] = np.sum(region * kernel)
                
        return output
    
    @staticmethod
    def _local_variance(image, window_size=3):
        """Calculate local variance in a window around each pixel"""
        pad = window_size // 2
        padded = np.pad(image, ((pad, pad), (pad, pad)), mode='reflect')
        
        # Create output array
        output = np.zeros_like(image, dtype=float)
        
        # Calculate local variance
        for i in range(image.shape[0]):
            for j in range(image.shape[1]):
                region = padded[i:i+window_size, j:j+window_size]
                output[i, j] = np.var(region)
                
        return output


class QualityAssessmentWorkflow(Workflow):
    """
    Quality Assessment Workflow:
    1. Given a folder of SEM images
    2. Assess the quality of each image using various metrics
    3. Return a sorted list of images by quality
    """
    
    def __init__(self, data_repository: DataRepository):
        super().__init__(
            "Quality Assessment", 
            "Assess and rank the quality of SEM images"
        )
        self.data_repository = data_repository
    
    def get_required_inputs(self) -> List[str]:
        return ["folder_path", "metric_weights"]
    
    def execute(self, folder_path: str, metric_weights: Dict[str, float] = None, **kwargs) -> Dict:
        """
        Execute the Quality Assessment workflow
        
        Args:
            folder_path: Path to the folder containing SEM images
            metric_weights: Dictionary of metric weights
                            Keys: 'blur', 'contrast', 'noise'
                            Values: Weight for each metric (0.0 to 1.0)
                            
        Returns:
            Dictionary with the result, containing:
                - sample: The Sample object
                - quality_scores: List of tuples (image, score) sorted by quality
        """
        # Use default weights if not provided
        if metric_weights is None:
            metric_weights = {
                'blur': 0.4,  # Higher blur metric = better (less blur)
                'contrast': 0.4,  # Higher contrast = better
                'noise': 0.2,  # Lower noise = better
            }
        
        # Extract sample ID from folder name
        sample_id = os.path.basename(folder_path)
        
        # Check if we have this sample cached
        sample = self.data_repository.load_sample(sample_id)
        
        # If not found, need to process
        if sample is None:
            return {
                "status": "need_processing",
                "folder_path": folder_path,
                "sample_id": sample_id
            }
        
        # Calculate quality metrics for each image
        quality_scores = []
        
        for img in sample.images:
            # Calculate metrics
            blur_metric = ImageQualityMetrics.calculate_blur_metric(img.image_path)
            contrast_metric = ImageQualityMetrics.calculate_contrast_metric(img.image_path)
            noise_metric = ImageQualityMetrics.calculate_noise_metric(img.image_path)
            
            # Normalize metrics
            max_blur = 1000.0  # Typical maximum value for blur metric
            max_contrast = 80.0  # Typical maximum value for contrast metric
            max_noise = 500.0  # Typical maximum value for noise metric
            
            norm_blur = min(blur_metric / max_blur, 1.0)
            norm_contrast = min(contrast_metric / max_contrast, 1.0)
            norm_noise = 1.0 - min(noise_metric / max_noise, 1.0)  # Invert so higher=better
            
            # Calculate weighted score
            score = (
                metric_weights['blur'] * norm_blur + 
                metric_weights['contrast'] * norm_contrast + 
                metric_weights['noise'] * norm_noise
            )
            
            quality_scores.append((img, score))
        
        # Sort by score (highest first)
        quality_scores.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "status": "success",
            "sample": sample,
            "quality_scores": quality_scores
        }
