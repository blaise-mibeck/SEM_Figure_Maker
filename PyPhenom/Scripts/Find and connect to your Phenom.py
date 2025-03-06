import PyPhenom as ppi

for phenom in ppi.FindPhenoms(1):
    print('Phenom ip: ', phenom.ip)
    print('Phenom id: ', phenom.name)

PhenomID = 'MVE012345678'
username = 'Username provided by Phenom World'
password = 'Password provided by Phenom World'

phenom = ppi.Phenom(PhenomID, username, password)
