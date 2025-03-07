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
        # Import our controller
        from controller import ScaleGridController
        
        # Create and run the controller
        controller = ScaleGridController()
        controller.run()
        
    except Exception as e:
        QMessageBox.critical(
            None, 
            "Error Starting Application",
            f"An error occurred while starting the application: {str(e)}\n\n"
            "Please check that all required files are present."
        )
        
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
