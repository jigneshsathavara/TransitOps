import urllib.request
html = urllib.request.urlopen('http://127.0.0.1:3000/dashboard.html').read().decode()
print('Trip Dispatcher found:', 'TRIP DISPATCHER' in html)
print('Trip Lifecycle found:', 'TRIP LIFECYCLE' in html)
print('Create Trip form found:', 'CREATE TRIP' in html)
print('Live Board found:', 'LIVE BOARD' in html)
print('Cargo validation found:', 'capacity exceeded' in html)
print('Vehicle capacity validation:', 'vehicleCapacities' in html)
