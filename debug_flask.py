import urllib.request
import urllib.error

try:
    response = urllib.request.urlopen('http://127.0.0.1:3000/dashboard.html')
    content = response.read().decode('utf-8')
    
    # Check file size
    print(f"Content length: {len(content)}")
    
    # Find specific markers
    if 'TRIP DISPATCHER' in content:
        print("✓ TRIP DISPATCHER found")
    else:
        print("✗ TRIP DISPATCHER not found")
        
    if 'CREATE TRIP' in content:
        print("✓ CREATE TRIP found")
    else:
        print("✗ CREATE TRIP not found")
        
    if 'LIVE BOARD' in content:
        print("✓ LIVE BOARD found")
    else:
        print("✗ LIVE BOARD not found")
    
    # Show first 500 chars of trips-tab content
    trips_start = content.find('id="trips-tab"')
    if trips_start > -1:
        print("\nFirst 300 chars of trips-tab:")
        print(content[trips_start:trips_start+300])
        
except urllib.error.URLError as e:
    print(f"Error: {e}")
