import PyPhenom as ppi
import numpy as np
import cv2

PhenomID = 'MVE012345678'
username = 'Username provided by Phenom World'
password = 'Password provided by Phenom World'

phenom = ppi.Phenom(PhenomID, username, password)

acq = phenom.SemAcquireImage(1024, 1024, 16, ppi.DetectorMode.All, False, 1.0)
acq.image = cv2.Canny(np.array(acq.image), 32, 176)
ppi.Save(acq, 'cannyEdge.tiff')
