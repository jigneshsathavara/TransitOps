import urllib.request

req = urllib.request.Request('http://127.0.0.1:3000/dashboard.html')
req.add_header('Cookie', 'transitops_auth=1; transitops_role=Dispatcher')
with urllib.request.urlopen(req) as response:
    html = response.read().decode()
    print('FUEL & EXPENSE MANAGEMENT found:', 'FUEL & EXPENSE MANAGEMENT' in html)
    print('FUEL LOGS found:', 'FUEL LOGS' in html)
    print('OTHER EXPENSES found:', 'OTHER EXPENSES' in html)
    print('Total cost found:', '₹34,070' in html)
    print('Log Fuel button found:', '+ Log Fuel' in html)
    print('Add Expense button found:', '+ Add Expense' in html)
