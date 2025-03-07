# ScaleGrid Enhanced Version

This is an enhanced version of ScaleGrid that adds support for:
- Analyzing collections of SEM images 
- Detecting containment relationships based on FOV and sample position
- Creating collection files to save all information
- Adding colored bounding boxes and borders to show relationships
- Providing options for customizing bounding box display
- Enhanced sample information collection and storage
- Metadata storage in CSV format for easy access
- Reuse of existing sample information and metadata

## Installation

1. Make sure you have Python 3.6+ installed
2. Install PyQt5: `pip install PyQt5`
3. Install Pillow: `pip install Pillow`
4. Place all the files in the same directory

## Files Structure

```
.
├── collection_manager.py        # Class for managing collections
├── enhanced_controller.py       # Updated controller with collection support
├── enhanced_image_grid.py       # Enhanced image grid with line style options
├── enhanced_main.py             # Main entry point for the application
├── enhanced_sample_dialog.py    # Enhanced sample information dialog
├── metadata_manager.py          # Class for managing metadata and sample info
├── modified_scalegrid_workflow.py  # Modified ScaleGrid workflow
├── view_classes.py              # Original view classes (unmodified)
├── view_dialogs.py              # Original dialog classes (unmodified)
└── README.md                    # This file
```

## Usage

1. Run the application:
   ```
   python enhanced_main.py
   ```

2. Click the "Open Folder" button to select a folder containing SEM images.

3. If this is the first time using this folder, you'll be prompted to enter detailed sample information:
   - Sample ID (pre-filled with folder name pattern)
   - Preparation method (Dust, Flick, Dish, or Chunk)
   - Gold coating status
   - SEM operator name
   - Additional notes/comments

4. If sample information already exists, you'll be asked if you want to use it or create new information.

5. Similarly, if metadata has been previously extracted, you'll be asked if you want to reuse it.

6. The application will analyze the TIFF files in the folder to extract metadata and determine containment relationships.

7. All image metadata will be stored in a CSV file for easy external access.

8. Image collections will be automatically created and saved as JSON files in a "collections" folder.

9. The first collection will be displayed in the grid.

10. You can switch between collections using the "Collections" menu.

11. Use the "Show bounding boxes" checkbox to toggle bounding box visibility.

12. Use the line style radio buttons to choose between solid, dashed, and dotted lines.

13. Click the "Export Grid" button to save the current grid as a PNG image.

## Collection Files

Collection files are stored in JSON format and contain:
- List of all images in the collection
- Metadata for each image
- Containment relationships between images
- Bounding box coordinates for contained images
- Color assignments for high-magnification images

These files allow you to reload collections without re-analyzing the original images.

## Features

- **Automatic Analysis**: Automatically analyzes SEM images to extract metadata and determine containment relationships.
- **Collection Management**: Groups related images into collections based on containment.
- **Colored Visualization**: Assigns distinct colors to high-magnification images and their bounding boxes.
- **Customizable Display**: Options to show/hide bounding boxes and change line styles.
- **Tooltip Information**: Hover over bounding boxes to see information about the contained image.
- **Grid Export**: Export the current grid view as a PNG image.
- **Enhanced Sample Information**: Collect and store detailed sample preparation information.
- **Metadata Storage**: Store all image metadata in CSV format for easy access with external tools.
- **Data Reuse**: Option to reuse existing sample information and metadata to speed up processing.

## Data Storage

The application creates the following data files:

- **metadata/[sample_id]_info.json**: Contains sample information including preparation method, gold coating status, operator, and notes.
- **metadata/[sample_id]_metadata.csv**: Contains extracted metadata for all images in CSV format.
- **collections/[sample_id]_*.json**: Contains collection information including image lists, containment relationships, and bounding box coordinates.

These files are automatically created when processing a folder and can be reused in future sessions to speed up the workflow.
