import urllib.request
import time

time.sleep(1)

try:
    req = urllib.request.Request('http://127.0.0.1:3000/dashboard.html')
    req.add_header('Cookie', 'transitops_auth=1; transitops_role=Dispatcher')
    
    with urllib.request.urlopen(req) as response:
        html = response.read().decode()
        print('✓ MAINTENANCE MANAGEMENT found:', 'MAINTENANCE MANAGEMENT' in html)
        print('✓ SERVICE RECORD LOG found:', 'SERVICE RECORD LOG' in html)
        print('✓ MAINTENANCE RECORDS found:', 'MAINTENANCE RECORDS' in html)
        print('✓ Service type dropdown found:', 'Oil Change' in html and 'Engine Repair' in html)
        print('✓ Sample data found:', 'VAN-05' in html and 'TRUCK-11' in html and 'MINI-03' in html)
        print('✓ In Shop note found:', 'In Shop vehicles are removed' in html)
        print('✓ Save button found:', 'btn-save' in html)
        
except Exception as e:
    print(f"Error: {e}")
