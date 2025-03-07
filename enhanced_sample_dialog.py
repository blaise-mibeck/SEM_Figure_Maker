from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QTextEdit, QPushButton, QDialogButtonBox, QFileDialog,
                            QFormLayout, QGroupBox, QComboBox, QCheckBox, QMainWindow)
from PyQt5.QtCore import Qt
from typing import Dict, Optional, Tuple

class EnhancedSampleInfoDialog(QDialog):
    """Enhanced dialog to collect detailed sample information from the user"""
    
    def __init__(self, parent=None, folder_name: str = "", existing_info: Dict = None):
        super().__init__(parent)
        self.setWindowTitle("Sample Information")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Form layout for input fields
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Sample ID (pre-filled with folder name or existing info)
        self.sample_id_edit = QLineEdit()
        if existing_info and "sample_id" in existing_info:
            self.sample_id_edit.setText(existing_info["sample_id"])
        elif folder_name:
            # Try to extract prefix from folder name (e.g., SEM1-123)
            import re
            folder_match = re.search(r'(SEM\d+-\d+)', folder_name)
            if folder_match:
                prefix = folder_match.group(1)
                self.sample_id_edit.setText(prefix)
            else:
                self.sample_id_edit.setText(folder_name)
        form_layout.addRow("Sample ID:", self.sample_id_edit)
        
        # Sample preparation method dropdown
        self.prep_method_combo = QComboBox()
        prep_methods = ["", "Dust", "Flick", "Dish", "Chunk"]
        self.prep_method_combo.addItems(prep_methods)
        if existing_info and "preparation_method" in existing_info:
            index = self.prep_method_combo.findText(existing_info["preparation_method"])
            if index >= 0:
                self.prep_method_combo.setCurrentIndex(index)
        form_layout.addRow("Preparation method:", self.prep_method_combo)
        
        # Gold coating checkbox
        self.gold_coated_check = QCheckBox("Gold coated")
        if existing_info and "gold_coated" in existing_info:
            self.gold_coated_check.setChecked(existing_info["gold_coated"])
        form_layout.addRow("Coating:", self.gold_coated_check)
        
        # SEM operator
        self.operator_edit = QLineEdit()
        if existing_info and "operator" in existing_info:
            self.operator_edit.setText(existing_info["operator"])
        form_layout.addRow("SEM operator:", self.operator_edit)
        
        # Notes/comments
        form_layout.addRow(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(100)
        if existing_info and "notes" in existing_info:
            self.notes_edit.setPlainText(existing_info["notes"])
        layout.addWidget(self.notes_edit)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_sample_info(self) -> Dict[str, str]:
        """Get the sample information entered by the user"""
        return {
            "sample_id": self.sample_id_edit.text(),
            "preparation_method": self.prep_method_combo.currentText(),
            "gold_coated": self.gold_coated_check.isChecked(),
            "operator": self.operator_edit.text(),
            "notes": self.notes_edit.toPlainText()
        }
