import sys
import os

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    print("Successfully imported PyQt5")
except ImportError as e:
    print(f"Error importing PyQt5: {e}")
    print(f"Python path: {sys.path}")
    print(f"Python executable: {sys.executable}")
    sys.exit(1)

# Add the current directory to sys.path to ensure all modules can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

def main():
    # Create the application
    app = QApplication(sys.argv)
    app.setApplicationName("ScaleGrid")
    app.setStyle("Fusion")  # Use Fusion style for consistent cross-platform look

    try:
        # First check that all modules can be imported without errors
        required_modules = [
            "main_window",
            "image_grid",
            "metadata",
            "image_collections", 
            "sample_dialog",
            "controller"
        ]
        
        for module_name in required_modules:
            try:
                __import__(module_name)
                print(f"Successfully imported {module_name}")
            except ImportError as e:
                print(f"Error importing {module_name}: {e}")
                raise
        
        # Import our controller
        from controller import ScaleGridController
        
        # Create and run the controller
        controller = ScaleGridController()
        controller.run()
        
    except Exception as e:
        error_msg = f"An error occurred while starting the application: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        # Show error dialog
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error Starting Application")
            msg_box.setText(error_msg)
            msg_box.setDetailedText(traceback.format_exc())
            msg_box.exec_()
        except:
            # If even the QMessageBox fails, print to console only
            print("Could not display error dialog")
        
        sys.exit(1)
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
