import PyPhenom as ppi
from matplotlib import pyplot as plt

PhenomID = 'MVE012345678'
username = 'Username provided by Phenom World'
password = 'Password provided by Phenom World'

phenom = ppi.Phenom(PhenomID, username, password)

acq = phenom.SemAcquireImage(1024 ,1024, 16, ppi.DetectorMode.All, False, 1.0)

fig = plt.figure()

width = acq.metadata.pixelSize.width * acq.image.width
height = acq.metadata.pixelSize.height * acq.image.height

plot = plt.imshow(acq.image, cmap='gray', extent=[0,width,0,height])

plt.title('Phenom Acquisition image')
plt.xlabel('x')
plt.ylabel('y')

fig.colorbar(plot)

plt.show()
