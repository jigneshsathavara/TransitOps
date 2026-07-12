import urllib.request
import urllib.parse

url = 'http://127.0.0.1:3000/dashboard.html?' + urllib.parse.urlencode({'t': 'nocache'})
html = urllib.request.urlopen(url).read().decode()
print('Trip Dispatcher found:', 'TRIP DISPATCHER' in html)
print('Create Trip found:', 'CREATE TRIP' in html)
print('Live Board found:', 'LIVE BOARD' in html)
print('Validation alert found:', 'validation-alert' in html)
print('Vehicle capacity check found:', 'vehicleCapacities' in html)
