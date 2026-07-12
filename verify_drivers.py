import urllib.request
html = urllib.request.urlopen('http://127.0.0.1:3000/dashboard.html').read().decode()
print('Drivers tab found:', 'data-tab="drivers"' in html)
print('Drivers & Safety found:', 'DRIVERS & SAFETY PROFILES' in html)
print('Alex driver found:', '>Alex<' in html)
print('License expired text:', 'EXPIRED' in html)
print('Status toggle found:', 'status-toggle' in html)
