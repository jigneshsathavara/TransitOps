import urllib.request
html = urllib.request.urlopen('http://127.0.0.1:3000/dashboard.html').read().decode()
print('Fleet tab found:', 'data-tab="fleet"' in html)
print('Vehicle Registry found:', 'VEHICLE REGISTRY' in html)
print('GJ014B452 found:', 'GJ014B452' in html)
print('Unique rule found:', 'must be unique' in html)
