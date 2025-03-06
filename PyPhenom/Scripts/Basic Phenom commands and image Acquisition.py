import PyPhenom as ppi
import time

PhenomID = 'MVE012345678'
username = 'Username provided by Phenom World'
password = 'Password provided by Phenom World'

phenom = ppi.Phenom(PhenomID, username, password)

phenom.Load()

phenom.MoveToNavCam()

acqCamParams = ppi.CamParams()
acqCamParams.size = ppi.Size(912, 912)
acqCamParams.nFrames = 1

acqNavCam = phenom.NavCamAcquireImage(acqCamParams)
ppi.Save(acqNavCam, 'NavCam.tiff')

phenom.MoveToSem()
time.sleep(7)

phenom.MoveTo(0, 0)

phenom.SetSemHighTension(-5000)

phenom.SetSemSpotSize(3.3)

phenom.SemAutoFocus()

phenom.SetHFW(ppi.MagnificationToFieldWidth(5000))

phenom.SemAutoContrastBrightness()

viewingMode = phenom.GetSemViewingMode()
viewingMode.scanParams.detector = ppi.DetectorMode.All
phenom.SetSemViewingMode(viewingMode)

acqScanParams = ppi.ScanParams()
acqScanParams.size = ppi.Size(1024, 1024)
acqScanParams.detector = ppi.DetectorMode.All
acqScanParams.nFrames = 16
acqScanParams.hdr= False
acqScanParams.scale = 1.0
acq = phenom.SemAcquireImage(acqScanParams)
acqWithDatabar = ppi.AddDatabar(acq, 'Label')

ppi.Save(acq, 'example.tiff')
ppi.Save(acqWithDatabar, 'exampleWithDatabar.tiff')

phenom.Unload()
