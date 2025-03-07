# ScaleGrid - SEM Image Grid Maker

A tool for creating grids of SEM images with proper scale relationships.

## Overview

ScaleGrid helps you organize and visualize Scanning Electron Microscope (SEM) images at different magnifications. It automatically:

1. Detects when one image is taken at a higher magnification within the field of view of another image
2. Creates collections of related images
3. Displays the images with color-coded bounding boxes showing where higher magnification images were taken
4. Exports publication-ready image grids

## Installation

1. Make sure you have Python 3.6+ installed
2. Install the required packages:
   ```
   pip install PyQt5 Pillow
   ```
3. Run the application:
   ```
   python main.py
   ```

## Usage

### Basic Workflow

1. Click "Open Folder" to select a folder containing SEM images (TIFF format)
2. Enter sample information when prompted:
   - Session ID (SEM1-### or EDX1-###) - automatically filled from folder name
   - Sample ID (TCL##### or ####-##-##) - the actual sample identifier
   - Preparation method (Dust, Flick, Dish, or Chunk)
   - Gold coating status
   - SEM operator name
   - Notes
3. The application will analyze the images and create collections
4. The first collection will be displayed with bounding boxes showing the relationships
5. Use the "Collections" menu to switch between different collections
6. Click "Export Grid" to save the current grid view as a PNG image

### Controls

- **Grid size**: Select from 1x1, 2x2, 3x3, or 4x4 grid layouts
- **Bounding boxes**:
  - Show/hide bounding boxes
  - Change line style (solid, dashed, or dotted)
- **Collections**: Switch between different groups of related images
- **Sample Info**: Edit sample information
- **Export Grid**: Save the current grid view to a PNG file

## File Organization

- **Main files**:
  - `main.py` - Entry point
  - `controller.py` - Main controller logic
  - `image_grid.py` - Image grid display
  - `metadata.py` - Metadata handling and CSV storage
  - `collections.py` - Collection management
  - `sample_dialog.py` - Sample information dialog
  - `main_window.py` - Main application window

- **Data files** (automatically created):
  - `metadata/[session_id]_info.json` - Sample/session information
  - `metadata/[session_id]_metadata.csv` - Image metadata in CSV format
  - `collections/[session_id]_[sample_id]_[collection_name].json` - Collection data

## Features

- **Session vs Sample ID**: Distinguishes between SEM sessions (SEM1-###) and actual sample IDs (TCL#####)
- **Reuse Information**: Remembers previously entered information and metadata for faster processing
- **CSV Metadata Storage**: All image metadata is saved in CSV format for easy access with external tools
- **Color-Coded Relationships**: Different colors for different magnification scales
- **Tooltip Information**: Hover over bounding boxes to see details of the higher-magnification image
- **Multiple Collections**: When a folder has multiple unrelated images, they're organized into separate collections
- **Customizable Display**: Options for visibility and style of bounding boxes
