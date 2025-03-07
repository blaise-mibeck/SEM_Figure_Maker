from PIL import Image
import xml.etree.ElementTree as ET
import io
import os
import pandas as pd

def extract_metadata_from_tiff(tiff_path):
    """
    Extracts and parses the XML metadata embedded in a TIFF image.
    
    Args:
        tiff_path (str): Path to the TIFF file.

    Returns:
        dict: Extracted metadata as a dictionary.
    """
    # Open the TIFF file using Pillow
    with Image.open(tiff_path) as img:
        # TIFF images may store metadata in their "info" dictionary
        xml_data = img.tag_v2.get(34683)  # 270 is the TIFF tag for ImageDescription
        
        if not xml_data:
            raise ValueError("No XML metadata found in the TIFF file.")
        
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
        mag_pol = int(127000/field_of_view_width, 0)

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
            "high_voltage_kV": float(root.find("acquisition/scan/highVoltage").text),
            "emission_current_uA": float(root.find("acquisition/scan/emissionCurrent").text),
            "working_distance_mm": float(root.find("workingDistance").text)
        }
        
        return data

# Example usage:
tiff_folder = "data\SEM1-426\Stitch_SE_115x\Project 11\Area 1\Acquisitions"  # Replace with your actual TIFF file path
tiff_list = os.listdir(tiff_folder)

metadata_df = pd.DataFrame()

for tif in tiff_list:
    if ".tiff" in tif:
        tiff_path = os.path.join(tiff_folder, tif)
        metadata = extract_metadata_from_tiff(tiff_path)
        metadata_df = metadata_df._append(metadata, ignore_index=True)   
        print(metadata)
metadata_df.to_csv("data\SEM1-426\Stitch_SE_115x\Project 11\Area 1\Acquisitions\metadata.csv", index=False)
