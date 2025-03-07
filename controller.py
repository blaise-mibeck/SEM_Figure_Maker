import os
import sys
import glob
import re
from typing import Dict, List, Optional
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QAction, QActionGroup
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from main_window import MainWindow
from sample_dialog import SampleInfoDialog
from metadata import MetadataManager
from image_collections import CollectionManager, ImageCollection

class ScaleGridController:
    """Main controller for the ScaleGrid application"""
    
    def __init__(self):
        # Initialize managers
        self.metadata_manager = MetadataManager()
        self.collection_manager = CollectionManager()
        
        # Initialize main window
        self.main_window = MainWindow()
        
        # Current application state
        self.current_folder = None
        self.current_session_id = None
        self.current_sample_id = None
        self.current_collections = []
        self.current_collection = None
        self.image_metadata = {}
        
        # Connect signals
        self.connect_signals()
