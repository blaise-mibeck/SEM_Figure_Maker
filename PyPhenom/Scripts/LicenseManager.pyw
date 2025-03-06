#!python3
#
# Copyright (c) 2017 by Phenom-World B.V.
# All rights reserved. This file includes confidential and proprietary information of Phenom-World B.V.

import sys
import ctypes
MessageBox = ctypes.windll.user32.MessageBoxW

try:
    from PySide import QtCore
    from PySide.QtCore import Qt
    from PySide import QtGui
    import PyPhenom as ppi
except Exception as e:
    MessageBox(None, str(e), 'LicenseManager error', 0)


class LicenseDialog(QtGui.QDialog):

    def __init__(self, parent = None):
        super(LicenseDialog, self).__init__(parent)

        self.setWindowTitle('Add License')

        self.instrument = QtGui.QLineEdit()
        self.username = QtGui.QLineEdit()
        self.password = QtGui.QLineEdit()

        formLayout = QtGui.QFormLayout()
        formLayout.addRow("Instrument:", self.instrument)
        formLayout.addRow("Username:", self.username)
        formLayout.addRow("Password:", self.password)

        layout = QtGui.QGridLayout()
        layout.addLayout(formLayout, 0, 0, 4, 3)

        buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def GetLicense(self):
        return ppi.LicenseInfo(self.instrument.text(), self.username.text(), self.password.text())


class Window(QtGui.QWidget):

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.setWindowTitle('PPI License Manager')

        self.reportTree = QtGui.QTreeWidget()
        self.reportTree.setHeaderLabels(['Instrument', 'Username', 'Password'])

        items = []
        for lic in ppi.GetLicenses():
            items.append(QtGui.QTreeWidgetItem(None, [lic.instrumentId, lic.username, lic.password]))
        self.reportTree.insertTopLevelItems(0, items)
        if len(items):
            self.reportTree.setCurrentItem(items[0])

        self.reportTree.currentItemChanged.connect(self.onItemChanged)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.reportTree)

        self.deleteButton = QtGui.QPushButton('Delete')
        self.deleteButton.clicked.connect(self.onDelete)

        self.addButton = QtGui.QPushButton('Add...')
        self.addButton.clicked.connect(self.onAdd)

        btnLayout = QtGui.QHBoxLayout()
        btnLayout.addWidget(self.deleteButton)
        btnLayout.addWidget(self.addButton)
        btnLayout.addStretch()
        layout.addLayout(btnLayout)
        
        self.setLayout(layout)
        self.setMinimumSize(360, 120)
        self.updateUi()

    def updateUi(self):
        self.deleteButton.setEnabled(len(self.reportTree.selectedItems()) == 1)

    def onItemChanged(self, current, previous):
        self.updateUi()

    def onDelete(self):
        item = self.reportTree.currentItem()
        ppi.UninstallLicense(item.text(0))
        self.reportTree.takeTopLevelItem(self.reportTree.currentIndex().row())

    def onAdd(self):
        dialog = LicenseDialog()
        if dialog.exec_() == QtGui.QDialog.Accepted:
            lic = dialog.GetLicense()
            ppi.InstallLicense(lic.instrumentId, lic.username, lic.password)
            QtGui.QTreeWidgetItem(self.reportTree, [lic.instrumentId, lic.username, lic.password])


def main():
    app = QtGui.QApplication(sys.argv)

    window = Window()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
