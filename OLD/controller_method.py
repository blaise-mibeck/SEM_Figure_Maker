def analyze_folder_and_create_collections(self, folder_path, sample_id):
    """Analyze folder contents and create collections"""
    try:
        # First check if there are TIFF files in the folder
        tiff_files = glob.glob(os.path.join(folder_path, "*.tiff")) + \
                     glob.glob(os.path.join(folder_path, "*.tif"))
        
        if not tiff_files:
            self.main_window.show_message("No Images", f"No TIFF images found in {folder_path}")
            return
        
        # Check if we have existing sample info
        existing_info = self.metadata_manager.load_sample_info(sample_id)
        
        if existing_info:
            # Ask if user wants to use existing info
            response = QMessageBox.question(
                self.main_window,
                "Use Existing Sample Information",
                f"Found existing information for sample {sample_id}.\nDo you want to use it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if response == QMessageBox.Yes:
                # Use existing info and proceed with analysis
                self.analyze_folder_with_sample_info(folder_path, sample_id, existing_info)
            else:
                # Get new sample info
                self.show_sample_info_dialog(sample_id, existing_info)
        else:
            # No existing info, need to collect it
            self.show_sample_info_dialog(sample_id)
            
    except Exception as e:
        self.main_window.show_error("Error", f"Failed to analyze folder: {str(e)}")
        import traceback
        traceback.print_exc()