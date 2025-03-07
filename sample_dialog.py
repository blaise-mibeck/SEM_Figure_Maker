from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QTextEdit, QPushButton, QDialogButtonBox, QFileDialog,
                            QFormLayout, QGroupBox, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt
from typing import Dict, Optional

class SampleInfoDialog(QDialog):
    """Enhanced dialog to collect detailed sample information from the user"""
    
    def __init__(self, parent=None, session_id: str = "", existing_info: Dict = None):
        super().__init__(parent)
        self.setWindowTitle("Sample Information")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Form layout for input fields
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Session ID (pre-filled with folder pattern, e.g., SEM1-123)
        self.session_id_edit = QLineEdit()
        if existing_info and "session_id" in existing_info:
            self.session_id_edit.setText(existing_info["session_id"])
        elif session_id:
            self.session_id_edit.setText(session_id)
        form_layout.addRow("Session ID (SEM1-###):", self.session_id_edit)
        
        # Sample ID (separate from session ID, e.g., TCL##### or ####-##-##)
        self.sample_id_edit = QLineEdit()
        if existing_info and "sample_id" in existing_info:
            self.sample_id_edit.setText(existing_info["sample_id"])
        form_layout.addRow("Sample ID (TCL##### or ####-##-##):", self.sample_id_edit)
        
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
            "session_id": self.session_id_edit.text(),
            "sample_id": self.sample_id_edit.text(),
            "preparation_method": self.prep_method_combo.currentText(),
            "gold_coated": self.gold_coated_check.isChecked(),
            "operator": self.operator_edit.text(),
            "notes": self.notes_edit.toPlainText()
        }
