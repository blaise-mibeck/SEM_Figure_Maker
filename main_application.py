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
    app.setStyle("Fusion")  # Use Fusion style for consistent cross-platform lookpip 
    
    # Check if PyPhenom is available
    try:
        # Import PyPhenom to check if it's installed
        import PyPhenom as ppi

        for phenom in ppi.FindPhenoms(1):
            print('Phenom ip: ', phenom.ip)
            print('Phenom id: ', phenom.name)
        # If we got here, the import succeeded
        from enhanced_controller import EnhancedApplicationController
        
        # Create and run the controller
        controller = EnhancedApplicationController()
        controller.run()
        
    except ImportError:
        # PyPhenom is not installed, show an error message
        QMessageBox.critical(
            None, 
            "Missing Dependency",
            "PyPhenom is not installed or could not be imported. "
            "ScaleGrid requires PyPhenom to operate fully.\n\n"
            "You can still use ScaleGrid for viewing existing SEM images, "
            "but you won't be able to connect to a Phenom microscope or extract metadata "
            "from SEM image files.\n\n"
            "Please install PyPhenom according to the documentation."
        )
        
        # Import a simulated version of the controller
        from enhanced_controller import EnhancedApplicationController
        
        # Create and run the controller in simulation mode
        controller = EnhancedApplicationController()
        controller.run()
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
