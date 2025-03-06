import PyPhenom as ppi

for phenom in ppi.FindPhenoms(1):
    print('Phenom ip: ', phenom.ip)
    print('Phenom id: ', phenom.name)

