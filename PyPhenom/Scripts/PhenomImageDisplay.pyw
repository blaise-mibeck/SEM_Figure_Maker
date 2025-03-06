#!python3
# -*- coding: utf-8 -*-

import sys
import math
import ctypes
import PySide2
from PySide2 import QtCore
from PySide2.QtCore import Qt
from PySide2 import QtGui
from PySide2 import QtWidgets
import PyPhenom as ppi
import threading


class ConnectDialog(QtWidgets.QDialog):

	def __init__(self, parent = None):
		super(ConnectDialog, self).__init__(parent)

		self.phenom = None

		self.settings = QtCore.QSettings('Phenom-World', 'PPI')
		address = self.settings.value('address', ppi.FindPhenom(1).ip)
		username = self.settings.value('username', '')
		password = self.settings.value('password', '')

		self.address = QtWidgets.QLineEdit()
		self.address.setInputMask('000.000.000.000')
		self.address.setText(address)

		self.username = QtWidgets.QLineEdit()
		self.username.setText(username)

		self.password = QtWidgets.QLineEdit()
		self.password.setEchoMode(QtWidgets.QLineEdit.Password)
		self.password.setText(password)

		formLayout = QtWidgets.QFormLayout()
		formLayout.addRow("Address:", self.address)
		formLayout.addRow("User:", self.username)
		formLayout.addRow("Password:", self.password)
		
		layout = QtWidgets.QGridLayout()
		layout.addLayout(formLayout, 0, 0, 1, 3)

		buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, Qt.Horizontal, self)
		buttons.accepted.connect(self.connect)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)
		self.setLayout(layout)

		self.setWindowTitle(self.tr("Connect Phenom"))

	def connect(self):
		address = self.address.text()
		username = self.username.text()
		password = self.password.text()

		try:
			self.phenom = ppi.Phenom(address, username, password)
		except Exception as ex:
			QtWidgets.QMessageBox.critical(self, "Connect", str(ex))

		self.phenom.address = address
		self.settings.setValue('address', address)
		self.settings.setValue('username', username)
		self.settings.setValue('password', password)
		self.accept()

	def getPhenom(self):
		return self.phenom


def getPhenom():
	if len(sys.argv) == 2 and sys.argv[1] == '--sim':
		return ppi.Phenom('Simulator', '', '')
	dialog = ConnectDialog()
	if dialog.exec_() != QtWidgets.QDialog.Accepted:
		return None
	return dialog.getPhenom()


class toQImage(QtGui.QImage):

	def __init__(self, image):
		self._initialized = False
		rgbImg = ppi.Processing.Render(image)
		pixelTypes = {
			ppi.PixelType.Unsigned8 : QtGui.QImage.Format_Indexed8,
			ppi.PixelType.BGR : QtGui.QImage.Format_RGB888,
			ppi.PixelType.BGRA : QtGui.QImage.Format_ARGB32
		}

		# Workaround PYSIDE-140: QImage constructor never frees his memory
		self._data = memoryview(rgbImg).tobytes()
		super().__init__(self._data, rgbImg.width, rgbImg.height, rgbImg.strideY, pixelTypes[rgbImg.encoding])
		self._initialized = True

	def __del__(self):
		if self._initialized:
			if PySide2.__version__ < '5.11':
				ctypes.c_long.from_address(id(self._data)).value -= 1
			self._initialized = False
		#super(QImage2, self).__del__()


class ImageView(QtWidgets.QWidget):

	def __init__(self, image = None):
		super().__init__()
		self.setMinimumSize(128, 128)
		self._image = image
		self._zoom = 1
		self._viewMatrix = QtGui.QMatrix()
		self.setMouseTracking(True)
		self.setBackgroundRole(QtGui.QPalette.Base)

	def mousePressEvent(self, e):
		if e.buttons() & Qt.LeftButton:
			self._dragStart = e.pos()
			self._dragMatrix = QtGui.QMatrix(self.viewMatrix())

	def mouseMoveEvent(self, e):
		if (e.buttons() & Qt.LeftButton) == 0:
			return
		tv = self.imageMatrix().inverted()[0]
		p1 = tv.map(QtCore.QPointF(self._dragStart))
		p2 = tv.map(QtCore.QPointF(e.pos()))
		t = self._dragMatrix
		self.setViewMatrix(QtGui.QMatrix(t.m11(), t.m12(), t.m21(), t.m22(), t.dx() + p2.x() - p1.x(), t.dy() + p2.y() - p1.y()))
		self.repaint()

	def wheelEvent(self, e):
		pv = self.imageMatrix().inverted()[0].map(e.pos())
		pi = self.viewMatrix().inverted()[0].map(pv)
		self._zoom = max(self._zoom * math.pow(1.1, e.delta() / 120.0), 1.0)
		self.setViewMatrix(QtGui.QMatrix(self._zoom, 0, 0, self._zoom, pv.x() - self._zoom*pi.x(), pv.y() - self._zoom*pi.y()))
		self.repaint()

	def viewMatrix(self):
		return self._viewMatrix

	def setViewMatrix(self, t):
		if not self._image:
			return

		imgRect = QtCore.QRectF(0, 0, self._image.width(), self._image.height())
		viewRect = (t * self.imageMatrix()).mapRect(imgRect)
		if viewRect.width() >= self.width():
			dx = min(-viewRect.left(), 0) + max(self.width() - viewRect.right(), 0)
		else:
			dx = (self.width() - viewRect.width()) / 2 - viewRect.left()
		if viewRect.height() >= self.height():
			dy = min(-viewRect.top(), 0) + max(self.height() - viewRect.bottom(), 0)
		else:
			dy = (self.height() - viewRect.height()) / 2 - viewRect.top()
		self._viewMatrix = QtGui.QMatrix(viewRect.width()/imgRect.width(), 0, 0, viewRect.height()/imgRect.height(), viewRect.left() + dx, viewRect.top() + dy) * self.imageMatrix().inverted()[0]

	def resizeEvent(self, e):
		self.setViewMatrix(self.viewMatrix())

	def paintEvent(self, e):
		qp = QtGui.QPainter()
		qp.begin(self)
		qp.setRenderHint(QtGui.QPainter.Antialiasing)
		qp.setClipRect(self.rect())
		self.drawWidget(qp)
		qp.end()

	def imageMatrix(self):
		t = QtGui.QMatrix()
		if self._image:
			scale = min(self.width() / self._image.width(), self.height() / self._image.height())
			t.translate(0.5*(self.width() - scale*self._image.width()), 0.5*(self.height() - scale*self._image.height()))
			t.scale(scale, scale)
		return t

	def drawWidget(self, qp):
		if self._image:
			qp.setWorldMatrix(self.viewMatrix() * self.imageMatrix())
			qp.drawImage(QtCore.QPoint(0, 0), self._image)

	def setImage(self, image):
		self._image = image
		self.repaint()


class Window(QtWidgets.QWidget):

	acquisitionFinished = QtCore.Signal()
	acqSourceUpdate = QtCore.Signal(ppi.Acquisition)

	def __init__(self, phenom, parent = None):
		QtWidgets.QWidget.__init__(self, parent)

		self.phenom = phenom
		self.acqSource = ppi.AcquisitionSource(phenom.address)
		self.thread = threading.Thread(target=self.acqSource.Run)
		self.thread.start()
		self.acquisitionFinished.connect(lambda: self.onAcquisitionFinished())
		self.acqSourceUpdate.connect(lambda acq: self.handleLiveAcquisition(acq))
		self.acqSource.AcquisitionFinished.connect(lambda: self.acquisitionFinished.emit())
		self.acqSource.AcquisitionUpdate.connect(lambda acq: self.acqSourceUpdate.emit(acq))
		self.acq = None
		self.movieWriter = None

		self.imageView = ImageView()
		self.imageView.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

		self.detectorCombo = QtWidgets.QComboBox()
		self.detectorCombo.addItem('BSD', ppi.DetectorMode.All)
		self.detectorCombo.addItem('Topo A', ppi.DetectorMode.NorthSouth)
		self.detectorCombo.addItem('Topo B', ppi.DetectorMode.EastWest)
		self.detectorCombo.addItem('BSD A', ppi.DetectorMode.A)
		self.detectorCombo.addItem('BSD B', ppi.DetectorMode.B)
		self.detectorCombo.addItem('BSD C', ppi.DetectorMode.C)
		self.detectorCombo.addItem('BSD D', ppi.DetectorMode.D)
		self.detectorCombo.addItem('SED', ppi.DetectorMode.Sed)
		self.detectorCombo.addItem('Mix', ppi.DetectorMode.Mix)
		self.detectorCombo.currentIndexChanged.connect(self.setDetectorMode)

		self.sizeCombo = QtWidgets.QComboBox()
		self.sizeCombo.addItem(' 512 x  512', 512)
		self.sizeCombo.addItem('1024 x 1024', 1024)
		self.sizeCombo.addItem('2048 x 2048', 2048)
		self.sizeCombo.addItem('4096 x 4096', 4096)

		self.bitCombo = QtWidgets.QComboBox()
		self.bitCombo.addItem(' 8 bits', 8)
		self.bitCombo.addItem('16 bits', 16)

		self.integrateCombo = QtWidgets.QComboBox()
		self.integrateCombo.addItem('live', 1)
		self.integrateCombo.addItem('medium', 16)
		self.integrateCombo.addItem('high', 32)
		self.integrateCombo.addItem('best', 64)

		self.extClockModeCombo = QtWidgets.QComboBox()
		self.extClockModeCombo.addItem('Off', ppi.ScanExtClockMode.Off)
		self.extClockModeCombo.addItem('Cmd', ppi.ScanExtClockMode.Cmd)
		self.extClockModeCombo.addItem('Frame', ppi.ScanExtClockMode.Frame)
		self.extClockModeCombo.addItem('Line', ppi.ScanExtClockMode.Line)
		self.extClockModeCombo.addItem('Pixel', ppi.ScanExtClockMode.Pixel)

		self.driftCorrectionCombo = QtWidgets.QComboBox()
		self.driftCorrectionCombo.addItem('Default', ppi.DriftCorrection.Default)
		self.driftCorrectionCombo.addItem('Off', ppi.DriftCorrection.Off)
		self.driftCorrectionCombo.addItem('On', ppi.DriftCorrection.On)

		self.angleSlider = QtWidgets.QSlider()
		self.angleSlider.setOrientation(Qt.Horizontal)
		self.angleSlider.setRange(0, 360)
		self.angleSlider.setValue(0)
		self.angleSlider.setTickInterval(30)
		self.angleSlider.valueChanged.connect(self.setMix)

		self.radiusSlider = QtWidgets.QSlider()
		self.radiusSlider.setOrientation(Qt.Horizontal)
		self.radiusSlider.setRange(0, 100)
		self.radiusSlider.setValue(50)
		self.radiusSlider.setTickInterval(10)
		self.radiusSlider.valueChanged.connect(self.setMix)

		acquireButton = QtWidgets.QPushButton("Acquire")
		self.continuousButton = QtWidgets.QCheckBox("Continuous")
		loadButton = QtWidgets.QPushButton("Load...")
		saveButton = QtWidgets.QPushButton("Save...")
		self.recordButton = QtWidgets.QPushButton("Start Rec...")

		acquireButton.clicked.connect(self.acquire)
		loadButton.clicked.connect(self.loadImage)
		saveButton.clicked.connect(self.saveImage)
		self.recordButton.clicked.connect(self.toggleRecording)

		settingsLayout = QtWidgets.QHBoxLayout()
		settingsLayout.addWidget(self.detectorCombo)
		settingsLayout.addWidget(QtWidgets.QLabel('Size:'))
		settingsLayout.addWidget(self.sizeCombo)
		settingsLayout.addWidget(QtWidgets.QLabel('Integrate:'))
		settingsLayout.addWidget(self.integrateCombo)
		settingsLayout.addWidget(self.bitCombo)
		settingsLayout.addWidget(QtWidgets.QLabel('ExtClockMode:'))
		settingsLayout.addWidget(self.extClockModeCombo)
		settingsLayout.addWidget(QtWidgets.QLabel('DriftCorr:'))
		settingsLayout.addWidget(self.driftCorrectionCombo)
		settingsLayout.addStretch()
		settingsLayout.addWidget(QtWidgets.QLabel('Angle:'))
		settingsLayout.addWidget(self.angleSlider)
		settingsLayout.addWidget(QtWidgets.QLabel('Radius:'))
		settingsLayout.addWidget(self.radiusSlider)

		buttonLayout = QtWidgets.QHBoxLayout()
		buttonLayout.addWidget(acquireButton)
		buttonLayout.addWidget(self.continuousButton)
		buttonLayout.addWidget(loadButton)
		buttonLayout.addWidget(saveButton)
		buttonLayout.addWidget(self.recordButton)
		buttonLayout.addStretch()

		layout = QtWidgets.QVBoxLayout()
		layout.addWidget(self.imageView)
		layout.addLayout(settingsLayout)
		layout.addLayout(buttonLayout)
		self.setLayout(layout)

		self.setWindowTitle("Phenom [" + phenom.address + "]")

	def closeEvent(self, event):
		self.acqSource.Close()
		self.thread.join()
		event.accept()

	def onAcquisitionFinished(self):
		acq = self.acqSource.EndSemAcquireImage()
		self.showAcquisition(acq)
		if self.continuousButton.isChecked():
			QtCore.QTimer.singleShot(500, self.acquire)

	def showAcquisition(self, acq):
		self.acq = acq
		self.imageView.setImage(toQImage(self.acq.image))

	def handleLiveAcquisition(self, acq):
		self.showAcquisition(acq)
		self.addFrameToRecording(acq.image)

	def acquire(self):
		try:
			size = self.sizeCombo.itemData(self.sizeCombo.currentIndex())
			detectorMode = ppi.DetectorMode(self.detectorCombo.itemData(self.detectorCombo.currentIndex()))
			integrate = self.integrateCombo.itemData(self.integrateCombo.currentIndex())
			hdr = self.bitCombo.itemData(self.bitCombo.currentIndex()) == 16
			scale = 1.0
			center = ppi.Position(0, 0)
			extClockMode = ppi.ScanExtClockMode(self.extClockModeCombo.itemData(self.extClockModeCombo.currentIndex()))
			dc = ppi.DriftCorrection(self.driftCorrectionCombo.itemData(self.driftCorrectionCombo.currentIndex()))
			self.acqSource.BeginSemAcquireImage(size, size, integrate, detectorMode, hdr, scale, center, extClockMode, dc)
		except Exception as ex:
			QtWidgets.QMessageBox.critical(self, "Connect", str(ex))

	def loadImage(self):
		path = QtWidgets.QFileDialog.getOpenFileName(self, "Load Image", "Image.tif", "TIFF File (*.tif);;JPEG File (*.jpg);;BMP File (*.bmp)")[0]
		
		if path:
			try:
				self.acq = ppi.Load(path)
				self.imageView.setImage(toQImage(ppi.Processing.Normalize(self.acq.image)))
			except Exception as ex:
				QtWidgets.QMessageBox.critical(self, "Load Image", str(ex))

	def saveImage(self):
		if not self.acq:
			return
		path = QtWidgets.QFileDialog.getSaveFileName(self, "Save Image", "Image.tif", "TIFF File (*.tif);;JPEG File (*.jpg);;BMP File (*.bmp)")[0]
		
		if path:
			try:
				ppi.Save(self.acq, path)
			except Exception as ex:
				QtWidgets.QMessageBox.critical(self, "Save Image", str(ex))

	def startRecording(self):
		if not self.acq:
			return
		path = QtWidgets.QFileDialog.getSaveFileName(self, "Save Recording", "recording.mp4", "MP4 File (*.mp4)")[0]
		if not path:
			return
		fps = int(round(1/self.phenom.SemGetAcquisitionTimeEstimate(self.phenom.GetSemViewingMode().scanParams, True)))
		self.movieWriter = ppi.MovieWriter(self.acq.image.size, path, fps, 0.1)
		self.recordButton.setText("Stop Rec")

	def stopRecording(self):
		if not self.movieWriter:
			return
		self.movieWriter.Close()
		self.movieWriter = None
		self.recordButton.setText("Start Rec...")

	def toggleRecording(self):
		if self.movieWriter:
			self.stopRecording()
		else:
			self.startRecording()

	def addFrameToRecording(self, image):
		if self.movieWriter:
			self.movieWriter.AddFrame(image)

	def setDetectorMode(self, index):
		vm = self.phenom.GetSemViewingMode()
		vm.scanParams.detector = self.detectorCombo.itemData(index)
		self.phenom.SetSemViewingMode(vm)

	def setMix(self):
		degrees = self.angleSlider.value()
		radius = self.radiusSlider.value() * 0.01
		f = math.sin(radius * math.pi / 2)

		rot = degrees / 360
		a = 0.5 * (f * (abs(2 - 4 * rot) - 1) + 0.1*(1 - f))
		b = 0.5 * (f * (abs(2 - 4 * abs(rot - 0.25)) - 1) + 0.1*(1 - f))
		c = 0.5 * (f * (abs(2 - 4 * abs(rot - 0.75)) - 1) + 0.1*(1 - f))
		d = 0.5 * (f * (abs(2 - 4 * abs(rot - 0.50)) - 1) + 0.1*(1 - f))
		#print(f'angle={degrees}, radius={radius}: a={a:0.3f}, b={b:0.3f}, c={c:0.3f}, d={d:0.3f}')
		mix = ppi.DetectorMixFactors()
		mix.bsdA = a
		mix.bsdB = b
		mix.bsdC = c
		mix.bsdD = d
		self.phenom.SemSetDetectorMixFactors(mix)

def main():
	app = QtWidgets.QApplication(sys.argv)

	app.setOrganizationName("Phenom-World")
	app.setOrganizationDomain("phenom-world.com")
	app.setApplicationName("ImageDisplay")

	window = Window(getPhenom())
	window.show()
	sys.exit(app.exec_())

if __name__ == "__main__":
	main()
