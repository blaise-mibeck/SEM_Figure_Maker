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

    # Check if PyPhenom is available, but continue either way
    try:
        import PyPhenom as ppi
        print("PyPhenom library is available")
        # Try to find Phenoms on the network
        try:
            for phenom in ppi.FindPhenoms(1):
                print('Phenom ip: ', phenom.ip)
                print('Phenom id: ', phenom.name)
        except Exception as e:
            print(f"Error finding Phenom: {e}")
    except ImportError:
        print("PyPhenom library is not available, using basic functionality")
    
    # Import the basic controller which doesn't depend on PyPhenom
    from basic_controller import BasicController
    
    # Create and run the controller
    controller = BasicController()
    controller.run()
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
