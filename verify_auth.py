import urllib.request
import urllib.parse
import http.cookiejar
import time

# Create a cookie jar to maintain session
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

# Simulate authentication by setting cookies directly
# (normally done via login, but we'll set them manually)
import http.cookies
cookie = http.cookies.SimpleCookie()
cookie['transitops_auth'] = '1'
cookie['transitops_role'] = 'Dispatcher'

# Make request with auth cookie header
try:
    req = urllib.request.Request('http://127.0.0.1:3000/dashboard.html')
    req.add_header('Cookie', 'transitops_auth=1; transitops_role=Dispatcher')
    
    with urllib.request.urlopen(req) as response:
        html = response.read().decode()
        print(f"Content length: {len(html)}")
        print('✓ TRIP DISPATCHER found:', 'TRIP DISPATCHER' in html)
        print('✓ CREATE TRIP found:', 'CREATE TRIP' in html)
        print('✓ LIVE BOARD found:', 'LIVE BOARD' in html)
        print('✓ Validation alert found:', 'validation-alert' in html)
        print('✓ Vehicle capacity validation found:', 'vehicleCapacities' in html)
        
        # Show snippet to confirm
        if 'TRIP DISPATCHER' in html:
            idx = html.find('TRIP DISPATCHER')
            print(f"\nSnippet around TRIP DISPATCHER:\n{html[idx-50:idx+200]}")
            
except Exception as e:
    print(f"Error: {e}")
