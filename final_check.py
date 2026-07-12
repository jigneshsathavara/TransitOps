import urllib.request
import time

# Give server time to settle
time.sleep(2)

try:
    html = urllib.request.urlopen('http://127.0.0.1:3000/dashboard.html').read().decode()
    print(f"Content length: {len(html)}")
    print('✓ TRIP DISPATCHER found:', 'TRIP DISPATCHER' in html)
    print('✓ CREATE TRIP found:', 'CREATE TRIP' in html)
    print('✓ LIVE BOARD found:', 'LIVE BOARD' in html)
    print('✓ Validation alert found:', 'validation-alert' in html)
    print('✓ Vehicle capacity validation found:', 'vehicleCapacities' in html)
except Exception as e:
    print(f"Error: {e}")
